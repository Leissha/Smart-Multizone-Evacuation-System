from __future__ import annotations

import json
import logging
import re
from typing import Any

from devices.node2.edge.actuator_service import MAX_THRESHOLD_CM, MIN_THRESHOLD_CM

logger = logging.getLogger(__name__)

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/"
RPC_RESPONSE_PREFIX = "v1/devices/me/rpc/response/"
ATTRIBUTES_TOPIC = "v1/devices/me/attributes"
ATTRIBUTES_REQUEST_PREFIX = "v1/devices/me/attributes/request/"
ATTRIBUTES_RESPONSE_PREFIX = "v1/devices/me/attributes/response/"
THRESHOLD_ATTRIBUTE = "threshold_cm"

# Boolean RPCs: (command when true, command when false, response state key).
BOOLEAN_RPC_COMMANDS = {
    "setEvacuation": ("EVAC_ON", "EVAC_OFF", "evacuation_mode"),
    "setExitClosed": ("EXIT_CLOSE", "EXIT_OPEN", "exit_closed"),
    "setBuzzer": ("BUZZER_ON", "BUZZER_OFF", "buzzer_state"),
}
SUPPORTED_RPC_METHODS = (*BOOLEAN_RPC_COMMANDS, "setThreshold", "getState")


def token_fingerprint(token: str) -> str:
    """Return a useful identifier without exposing the credential."""
    if len(token) < 8:
        return "<missing-or-too-short>"
    return f"{token[:4]}...{token[-4:]}"


def rpc_request_id(topic: str) -> str:
    prefix = RPC_REQUEST_PREFIX
    if not topic.startswith(prefix):
        raise ValueError(f"unexpected RPC topic: {topic}")
    request_id = topic[len(prefix):]
    if not request_id or "/" in request_id:
        raise ValueError(f"invalid RPC request id in topic: {topic}")
    return request_id


def rpc_response_topic(request_id: str) -> str:
    if not request_id or not re.fullmatch(r"[A-Za-z0-9_-]+", request_id):
        raise ValueError("invalid RPC request id")
    return f"{RPC_RESPONSE_PREFIX}{request_id}"


def connection_failed(reason_code: Any) -> bool:
    """Support Paho v2 ReasonCode objects as well as integer test doubles."""
    is_failure = getattr(reason_code, "is_failure", None)
    if is_failure is not None:
        return bool(is_failure)
    return reason_code != 0


def _unwrap(params: Any) -> Any:
    return params.get("value") if isinstance(params, dict) and "value" in params else params


def boolean_param(params: Any) -> bool:
    value = _unwrap(params)
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValueError("params must be a boolean")


def threshold_param(params: Any) -> int:
    value = _unwrap(params)
    if isinstance(value, bool):
        raise ValueError("threshold must be a number of centimetres")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("threshold must be a number of centimetres") from None
    if not number.is_integer() or not MIN_THRESHOLD_CM <= number <= MAX_THRESHOLD_CM:
        raise ValueError(f"threshold must be a whole number from {MIN_THRESHOLD_CM} to {MAX_THRESHOLD_CM} cm")
    return int(number)


class ThingsBoardClient:
    def __init__(self, config: object, actuator_service: object) -> None:
        self.config = config
        self.actuator_service = actuator_service
        self.client: Any = None
        self.connected = False
        self.last_telemetry: dict[str, Any] = {}

    def start(self) -> None:
        if not self.config.thingsboard_enabled:
            logger.info("ThingsBoard disabled; serial ingestion remains active")
            return
        if not self.config.thingsboard_access_token:
            logger.warning("ThingsBoard token missing; serial ingestion remains active")
            return
        try:
            import paho.mqtt.client as mqtt
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"a3-{self.config.device_id}-edge",
            )
            self.client.username_pw_set(self.config.thingsboard_access_token, "")
            if self.config.thingsboard_tls:
                self.client.tls_set()
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe
            logger.info(
                "Connecting to ThingsBoard MQTT host=%s port=%s tls=%s device_id=%s token=%s",
                self.config.thingsboard_host,
                self.config.thingsboard_port,
                self.config.thingsboard_tls,
                self.config.device_id,
                token_fingerprint(self.config.thingsboard_access_token),
            )
            self.client.connect_async(self.config.thingsboard_host, self.config.thingsboard_port, 60)
            self.client.loop_start()
        except Exception as error:
            logger.warning("MQTT startup failed; serial ingestion remains active: %s", error)

    def stop(self) -> None:
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()

    def publish_telemetry(self, telemetry: dict[str, Any]) -> bool:
        payload = {key: value for key, value in telemetry.items() if value is not None}
        self.last_telemetry.update(payload)
        if not payload or not self.connected or self.client is None:
            return False
        try:
            encoded = json.dumps(payload, separators=(",", ":"))
            result = self.client.publish(TELEMETRY_TOPIC, encoded, qos=1)
            logger.info("MQTT telemetry publish payload=%s result=%s mid=%s", encoded, result.rc, result.mid)
            return result.rc == 0
        except Exception as error:
            logger.warning("Telemetry publish failed; serial ingestion continues: %s", error)
            return False

    # ---------- RPC: ThingsBoard -> edge -> Arduino ----------

    def handle_rpc_payload(self, request_id: str, payload: dict[str, Any]) -> None:
        method = payload.get("method", "")
        params = payload.get("params")

        if method == "getState":
            self.respond(request_id, {"success": True, "method": method, **self.last_telemetry})
            return

        try:
            if method in BOOLEAN_RPC_COMMANDS:
                enabled = boolean_param(params)
                on_command, off_command, state_key = BOOLEAN_RPC_COMMANDS[method]
                command, state_value = (on_command if enabled else off_command), enabled
            elif method == "setThreshold":
                state_value = threshold_param(params)
                command, state_key = f"THRESHOLD={state_value}", "threshold_cm"
            else:
                self.respond(request_id, {"success": False, "method": method, "error": "unsupported method"})
                return
        except ValueError as error:
            self.respond(request_id, {"success": False, "method": method, "error": str(error)})
            return

        def completed(success: bool, detail: str) -> None:
            response: dict[str, Any] = {"success": success, "method": method}
            if success:
                response[state_key] = state_value
            else:
                response["error"] = detail
            self.respond(request_id, response)

        self.actuator_service.request(command, completed)

    def respond(self, request_id: str, response: dict[str, Any]) -> None:
        if self.client is None:
            return
        topic = rpc_response_topic(request_id)
        encoded = json.dumps(response, separators=(",", ":"))
        result = self.client.publish(topic, encoded, qos=1)
        logger.info("MQTT RPC response topic=%s payload=%s result=%s", topic, encoded, result.rc)

    # ---------- Shared attributes: remote configuration ----------

    def handle_attributes(self, attributes: dict[str, Any]) -> None:
        """Apply a shared-attribute update such as {"threshold_cm": 40}."""
        if THRESHOLD_ATTRIBUTE not in attributes:
            return
        try:
            threshold = threshold_param(attributes[THRESHOLD_ATTRIBUTE])
        except ValueError as error:
            logger.warning("Ignoring shared attribute %s: %s", THRESHOLD_ATTRIBUTE, error)
            return
        if self.last_telemetry.get("threshold_cm") == threshold:
            logger.info("Shared threshold_cm=%s already active on the Arduino", threshold)
            return

        def completed(success: bool, detail: str) -> None:
            if success:
                logger.info("Shared attribute applied: threshold_cm=%s", threshold)
            else:
                logger.warning("Shared attribute threshold_cm=%s failed: %s", threshold, detail)

        self.actuator_service.request(f"THRESHOLD={threshold}", completed)

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if connection_failed(reason_code):
            self.connected = False
            logger.error("ThingsBoard MQTT connection rejected: %s", reason_code)
            return

        try:
            for topic in (f"{RPC_REQUEST_PREFIX}+", ATTRIBUTES_TOPIC, f"{ATTRIBUTES_RESPONSE_PREFIX}+"):
                result, message_id = client.subscribe(topic, qos=1)
                logger.info("MQTT subscribe requested topic=%s result=%s mid=%s", topic, result, message_id)
                if result != 0:
                    self.connected = False
                    logger.error("ThingsBoard subscription to %s failed with code %s", topic, result)
                    return
            # Ask for the current shared threshold so a value changed while the
            # edge was offline is still applied after a reconnect.
            client.publish(
                f"{ATTRIBUTES_REQUEST_PREFIX}1",
                json.dumps({"sharedKeys": THRESHOLD_ATTRIBUTE}),
                qos=1,
            )
        except Exception as error:
            self.connected = False
            logger.exception("ThingsBoard subscription failed: %s", error)
            return

        self.connected = True
        logger.info("Connected to ThingsBoard MQTT; RPC and attribute subscriptions requested")

    def _on_subscribe(self, client: Any, userdata: Any, message_id: int, reason_codes: list[Any], properties: Any) -> None:
        logger.info("MQTT subscription acknowledged mid=%s reason_codes=%s", message_id, [str(code) for code in reason_codes])

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        self.connected = False
        logger.warning("ThingsBoard MQTT disconnected (%s); reconnect is automatic", reason_code)

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        payload_text = message.payload.decode("utf-8", errors="replace")
        logger.info("MQTT message received topic=%s payload=%s", message.topic, payload_text)
        try:
            payload = json.loads(payload_text)
            if message.topic == ATTRIBUTES_TOPIC:
                self.handle_attributes(payload)
            elif message.topic.startswith(ATTRIBUTES_RESPONSE_PREFIX):
                self.handle_attributes(payload.get("shared", {}))
            else:
                request_id = rpc_request_id(message.topic)
                self.handle_rpc_payload(request_id, payload)
        except Exception as error:
            logger.exception("Invalid MQTT message: %s", error)

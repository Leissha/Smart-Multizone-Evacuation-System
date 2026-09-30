from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/"
RPC_RESPONSE_PREFIX = "v1/devices/me/rpc/response/"

RPC_COMMANDS = {
    # third tuple element is the response key set to the RPC's own boolean
    # params on success - display_state is a *string* in the telemetry
    # registry ("SAFE"/"LOCKDOWN"), so setLockdown reports a boolean
    # "lockdown_active" confirmation instead of misusing that string field.
    "setLockdown": ("LOCKDOWN_ON", "LOCKDOWN_OFF", "lockdown_active"),
    "setBuzzer": ("BUZZER_ON", "BUZZER_OFF", "master_buzzer"),
}


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


def boolean_param(params: Any) -> bool:
    value = params.get("value") if isinstance(params, dict) and "value" in params else params
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValueError("params must be a boolean")


class ThingsBoardClient:
    def __init__(self, config: object, actuator_service: object) -> None:
        self.config = config
        self.actuator_service = actuator_service
        self.client: Any = None
        self.connected = False

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
            self.client.on_publish = self._on_publish
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
        if not payload or not self.connected or self.client is None:
            return False
        try:
            encoded = json.dumps(payload, separators=(",", ":"))
            result = self.client.publish(TELEMETRY_TOPIC, encoded, qos=1)
            logger.info(
                "MQTT telemetry publish topic=%s payload=%s result=%s mid=%s",
                TELEMETRY_TOPIC,
                encoded,
                result.rc,
                result.mid,
            )
            return result.rc == 0
        except Exception as error:
            logger.warning("Telemetry publish failed; serial ingestion continues: %s", error)
            return False

    def handle_rpc_payload(self, request_id: str, payload: dict[str, Any]) -> None:
        method = payload.get("method", "")
        if method not in RPC_COMMANDS:
            self.respond(request_id, {"success": False, "method": method, "error": "unsupported method"})
            return
        try:
            enabled = boolean_param(payload.get("params"))
        except ValueError as error:
            self.respond(request_id, {"success": False, "method": method, "error": str(error)})
            return

        on_command, off_command, state_key = RPC_COMMANDS[method]
        command = on_command if enabled else off_command

        def completed(success: bool, detail: str) -> None:
            response = {"success": success, "method": method}
            if success:
                response[state_key] = enabled
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
        logger.info(
            "MQTT RPC response topic=%s payload=%s result=%s mid=%s",
            topic,
            encoded,
            result.rc,
            result.mid,
        )

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if connection_failed(reason_code):
            self.connected = False
            logger.error("ThingsBoard MQTT connection rejected: %s", reason_code)
            return

        try:
            topic = f"{RPC_REQUEST_PREFIX}+"
            result, message_id = client.subscribe(topic, qos=1)
            logger.info(
                "MQTT RPC subscribe requested topic=%s result=%s mid=%s",
                topic,
                result,
                message_id,
            )
            if result != 0:
                self.connected = False
                logger.error("ThingsBoard RPC subscription failed with code %s", result)
                return
        except Exception as error:
            self.connected = False
            logger.exception("ThingsBoard RPC subscription failed: %s", error)
            return

        self.connected = True
        logger.info("Connected to ThingsBoard MQTT; RPC subscription requested")

    def _on_subscribe(
        self,
        client: Any,
        userdata: Any,
        message_id: int,
        reason_codes: list[Any],
        properties: Any,
    ) -> None:
        logger.info(
            "MQTT RPC subscription acknowledged mid=%s reason_codes=%s",
            message_id,
            [str(code) for code in reason_codes],
        )

    def _on_publish(
        self,
        client: Any,
        userdata: Any,
        message_id: int,
        reason_code: Any,
        properties: Any,
    ) -> None:
        logger.info("MQTT publish acknowledged mid=%s reason=%s", message_id, reason_code)

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        self.connected = False
        logger.warning(
            "ThingsBoard MQTT disconnected (%s); reconnect is automatic",
            reason_code,
        )

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        payload_text = message.payload.decode("utf-8", errors="replace")
        logger.info("MQTT message received topic=%s payload=%s", message.topic, payload_text)
        try:
            request_id = rpc_request_id(message.topic)
            payload = json.loads(payload_text)
            logger.info(
                "RPC parsed request_id=%s method=%s params=%s",
                request_id,
                payload.get("method"),
                payload.get("params"),
            )
            self.handle_rpc_payload(request_id, payload)
        except Exception as error:
            logger.exception("Invalid MQTT RPC message: %s", error)

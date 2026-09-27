from __future__ import annotations

import argparse
import json
import time
from typing import Any

import paho.mqtt.client as mqtt

from devices.node3.edge.config import get_config
from devices.node3.edge.thingsboard_client import (
    RPC_REQUEST_PREFIX,
    TELEMETRY_TOPIC,
    rpc_request_id,
    rpc_response_topic,
    token_fingerprint,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolate ThingsBoard MQTT from Arduino and FastAPI")
    parser.add_argument("--wait-seconds", type=int, default=60)
    parser.add_argument("--respond", action="store_true", help="Reply to received RPC requests")
    args = parser.parse_args()
    config = get_config()

    if not config.thingsboard_access_token:
        print("ERROR: THINGSBOARD_ACCESS_TOKEN is missing")
        return 2

    print(
        "MQTT diagnostic configuration:",
        f"device_id={config.device_id}",
        f"host={config.thingsboard_host}",
        f"port={config.thingsboard_port}",
        f"tls={config.thingsboard_tls}",
        f"token={token_fingerprint(config.thingsboard_access_token)}",
    )

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="a3-node3-mqtt-diagnostic")
    client.username_pw_set(config.thingsboard_access_token, "")
    if config.thingsboard_tls:
        client.tls_set()

    def on_connect(client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        print(f"CONNECTED reason={reason_code}")
        if getattr(reason_code, "is_failure", reason_code != 0):
            return
        result, message_id = client.subscribe(f"{RPC_REQUEST_PREFIX}+", qos=1)
        print(f"SUBSCRIBE topic={RPC_REQUEST_PREFIX}+ result={result} mid={message_id}")
        payload = json.dumps({"diagnostic_test": int(time.time() * 1000)})
        published = client.publish(TELEMETRY_TOPIC, payload, qos=1)
        print(f"PUBLISH topic={TELEMETRY_TOPIC} payload={payload} result={published.rc} mid={published.mid}")

    def on_subscribe(client: Any, userdata: Any, message_id: int, reason_codes: list[Any], properties: Any) -> None:
        print(f"SUBSCRIBED mid={message_id} reason_codes={[str(code) for code in reason_codes]}")

    def on_message(client: Any, userdata: Any, message: Any) -> None:
        text = message.payload.decode("utf-8", errors="replace")
        print(f"RPC_RECEIVED topic={message.topic} payload={text}")
        if args.respond:
            request_id = rpc_request_id(message.topic)
            topic = rpc_response_topic(request_id)
            response = json.dumps({"success": True, "diagnostic": True})
            published = client.publish(topic, response, qos=1)
            print(f"RPC_RESPONSE topic={topic} payload={response} result={published.rc} mid={published.mid}")

    def on_disconnect(client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        print(f"DISCONNECTED reason={reason_code}")

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.connect(config.thingsboard_host, config.thingsboard_port, 60)
    client.loop_start()
    try:
        time.sleep(max(1, args.wait_seconds))
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

HOST = os.getenv("THINGSBOARD_HOST", "mqtt.thingsboard.cloud")
PORT = int(os.getenv("THINGSBOARD_PORT", "8883"))
USE_TLS = os.getenv("THINGSBOARD_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
TELEMETRY_TOPIC = "v1/devices/me/telemetry"

NODES = {
    "node1": {
        "token_env": "NODE_1_ACCESS_TOKEN",
        "alarm": {
            "fire_detected": True,
            "smoke_level": "HIGH",
            "temperature": 30.0,
        },
        "clear": {
            "fire_detected": False,
            "smoke_level": "LOW",
            "temperature": 24.0,
        },
    },
    "node2": {
        "token_env": "NODE_2_ACCESS_TOKEN",
        "alarm": {
            "distance_cm": 10.0,
            "exit_blocked": True,
        },
        "clear": {
            "distance_cm": 120.0,
            "exit_blocked": False,
        },
    },
    "node3": {
        "token_env": "NODE_3_ACCESS_TOKEN",
        "alarm": {
            "sound_level": 26,
            "vibration_detected": True,
        },
        "clear": {
            "sound_level": 0,
            "vibration_detected": False,
        },
    },
    "node4": {
        "token_env": "NODE_4_ACCESS_TOKEN",
        "alarm": {
            "manual_emergency": True,
        },
        "clear": {
            "manual_emergency": False,
        },
    },
}


def publish(name: str, state: str) -> None:
    config = NODES[name]
    token_env = config["token_env"]
    token = os.getenv(token_env)
    if not token:
        raise RuntimeError(f"Missing {token_env} in {ROOT_DIR / '.env'}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"demo-{name}-{int(time.time() * 1000)}",
    )
    client.username_pw_set(token, "")
    if USE_TLS:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    client.connect(HOST, PORT, 60)
    client.loop_start()
    try:
        payload = json.dumps(config[state])
        result = client.publish(TELEMETRY_TOPIC, payload, qos=1)
        result.wait_for_publish(timeout=10)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed for {name}: {mqtt.error_string(result.rc)}")
        print(f"{name} [{state}]: {payload}")
    finally:
        client.disconnect()
        client.loop_stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish one-shot simulated ThingsBoard telemetry")
    parser.add_argument(
        "--node",
        choices=["all", *NODES],
        default="all",
        help="Node to publish, or all nodes (default: all)",
    )
    parser.add_argument(
        "--state",
        choices=["alarm", "clear"],
        default="alarm",
        help="Publish alarm or safe clear telemetry (default: alarm)",
    )
    args = parser.parse_args()

    selected = NODES if args.node == "all" else (args.node,)
    for name in selected:
        publish(name, args.state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

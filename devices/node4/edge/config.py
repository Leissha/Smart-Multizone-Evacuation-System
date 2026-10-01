from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


def env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EdgeConfig:
    serial_port: str = os.getenv("SERIAL_PORT", "")
    serial_baud_rate: int = int(os.getenv("SERIAL_BAUD_RATE", "9600"))
    serial_timeout: float = float(os.getenv("SERIAL_TIMEOUT", "0.25"))
    poll_interval: float = float(os.getenv("POLL_INTERVAL", "0.02"))
    ack_timeout: float = float(os.getenv("ACK_TIMEOUT", "3.0"))
    thingsboard_enabled: bool = env_bool("THINGSBOARD_ENABLED", True)
    thingsboard_host: str = os.getenv("THINGSBOARD_HOST", "mqtt.thingsboard.cloud")
    thingsboard_port: int = int(os.getenv("THINGSBOARD_PORT", "8883"))
    thingsboard_access_token: str = os.getenv("THINGSBOARD_ACCESS_TOKEN", "")
    thingsboard_tls: bool = env_bool("THINGSBOARD_TLS", True)
    device_id: str = os.getenv("DEVICE_ID", "node-4-command-centre")


def get_config() -> EdgeConfig:
    return EdgeConfig()

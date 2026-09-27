from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "sound_level",
    "vibration_detected",
    "relay_state",
    "buzzer_state",
}


def parse_bool(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned == "true":
        return True
    if cleaned == "false":
        return False
    raise ValueError("expected true or false")


def parse_telemetry_line(line: str) -> dict[str, Any] | None:
    """Parse one complete Node 3 frame; malformed/status/ACK lines are ignored."""
    cleaned = line.strip()
    if not cleaned or cleaned.startswith(("ACK=", "ERROR=")) or "=" not in cleaned:
        return None

    values: dict[str, str] = {}
    for token in cleaned.split(","):
        key, separator, value = token.strip().partition("=")
        if not separator or not key or not value:
            return None
        values[key.strip().lower()] = value.strip()

    if set(values) != REQUIRED_FIELDS:
        return None

    try:
        sound_level = int(values["sound_level"])
        if not 0 <= sound_level <= 1023:
            return None
        return {
            "sound_level": sound_level,
            "vibration_detected": parse_bool(values["vibration_detected"]),
            "relay_state": parse_bool(values["relay_state"]),
            "buzzer_state": parse_bool(values["buzzer_state"]),
        }
    except (TypeError, ValueError):
        return None


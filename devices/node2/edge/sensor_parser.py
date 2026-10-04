from __future__ import annotations

from typing import Any


BOOLEAN_FIELDS = ("exit_blocked", "evacuation_mode", "exit_closed", "buzzer_state", "sensor_ok")
REQUIRED_FIELDS = {"distance_cm", "threshold_cm", *BOOLEAN_FIELDS}
MAX_DISTANCE_CM = 400.0


def parse_bool(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned == "true":
        return True
    if cleaned == "false":
        return False
    raise ValueError("expected true or false")


def parse_telemetry_line(line: str) -> dict[str, Any] | None:
    """Parse one complete Node 2 frame; malformed/status/ACK lines are ignored."""
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
        distance = round(float(values["distance_cm"]), 1)
        threshold = int(values["threshold_cm"])
        booleans = {key: parse_bool(values[key]) for key in BOOLEAN_FIELDS}
    except (TypeError, ValueError):
        return None

    if not 0 <= distance <= MAX_DISTANCE_CM or threshold <= 0:
        return None

    return {"distance_cm": distance, "threshold_cm": threshold, **booleans}

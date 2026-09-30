from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "manual_emergency",
    "display_state",
    "master_buzzer",
}


def parse_bool(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned == "true":
        return True
    if cleaned == "false":
        return False
    raise ValueError("expected true or false")


def parse_telemetry_line(line: str) -> dict[str, Any] | None:
    """Parse one complete Node 4 frame; malformed/status/ACK lines are ignored."""
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
        return {
            "manual_emergency": parse_bool(values["manual_emergency"]),
            "display_state": values["display_state"],
            "master_buzzer": parse_bool(values["master_buzzer"]),
        }
    except (TypeError, ValueError):
        return None

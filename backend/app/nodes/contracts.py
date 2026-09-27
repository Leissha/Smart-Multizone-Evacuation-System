from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TelemetryType = Literal["number", "boolean", "string"]
Accent = Literal["coral", "sage", "gold", "blue"]


@dataclass(frozen=True)
class TelemetryField:
    key: str
    value_type: TelemetryType
    unit: str | None = None


@dataclass(frozen=True)
class NodeContract:
    device_id: str
    display_name: str
    zone: str
    purpose: str
    telemetry_fields: tuple[TelemetryField, ...]
    rpc_methods: tuple[str, ...] = ()
    freshness_seconds: int = 30
    accent: Accent = "blue"
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def telemetry_keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.telemetry_fields)

    def telemetry_type(self, key: str) -> TelemetryType:
        for item in self.telemetry_fields:
            if item.key == key:
                return item.value_type
        return "string"


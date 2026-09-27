from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, StrictBool, field_validator


class DeviceSummary(BaseModel):
    device_id: str
    name: str
    role: str
    zone: str = ""
    telemetry_contract: list[dict[str, str | None]] = Field(default_factory=list)
    rpc_methods: list[str] = Field(default_factory=list)
    freshness_seconds: int = 30
    accent: str = "blue"
    source: Literal["live", "simulated"] = "simulated"
    online: bool = False
    last_update_ms: int | None = None


class DeviceCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    device_name: str = Field(min_length=3, max_length=120)
    zone: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=2, max_length=200)
    telemetry_contract: list[str] = Field(default_factory=list)
    rpc_methods: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=500)

    @field_validator("device_name")
    @classmethod
    def stable_device_name(cls, value: str) -> str:
        if not all(character.islower() or character.isdigit() or character == "-" for character in value):
            raise ValueError("device_name must use lowercase letters, numbers, and hyphens")
        return value


class DeviceProvisionResponse(BaseModel):
    device_name: str
    device_uuid: str
    edge_config_template: str
    credential_message: str


class DeviceStatus(BaseModel):
    device_id: str
    cloud_configured: bool
    active: bool
    last_update_ms: int | None = None


class ControlRequest(BaseModel):
    enabled: bool


class RpcRequest(BaseModel):
    method: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    params: StrictBool


class ControlResponse(BaseModel):
    accepted: bool
    method: str
    result: dict[str, Any]


class SystemStatus(BaseModel):
    api_healthy: bool = True
    thingsboard_connected: bool
    active_alarm_count: int = 0
    live_nodes: int = 0
    simulated_nodes: int = 4

from __future__ import annotations

import json
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.config import Settings
from backend.app.nodes.contracts import TelemetryField, TelemetryType


class ThingsBoardError(RuntimeError):
    pass


class ThingsBoardRestService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._device_uuid_cache: dict[str, str] = {}

    @property
    def api_configured(self) -> bool:
        return bool(self.settings.thingsboard_base_url and self.settings.thingsboard_api_key)

    @property
    def configured(self) -> bool:
        return self.api_configured

    def get_device(self, device_name: str) -> dict[str, Any]:
        device = self._request(
            "GET",
            f"/api/tenant/devices?{urlencode({'deviceName': device_name})}",
        )
        if not isinstance(device, dict) or not device.get("id", {}).get("id"):
            raise ThingsBoardError(f"ThingsBoard device not found: {device_name}")
        return device

    def resolve_device_uuid(self, device_name: str) -> str:
        cached = self._device_uuid_cache.get(device_name)
        if cached:
            return cached

        device_uuid = str(self.get_device(device_name)["id"]["id"])

        self._device_uuid_cache[device_name] = device_uuid
        return device_uuid

    def get_device_uuid(self, device_name: str) -> str:
        return self.resolve_device_uuid(device_name)

    def latest(self, device_uuid: str, telemetry_fields: Iterable[TelemetryField]) -> dict[str, Any]:
        fields = tuple(telemetry_fields)
        raw = self._request(
            "GET",
            f"/api/plugins/telemetry/DEVICE/{device_uuid}/values/timeseries"
            f"?{urlencode({'keys': ','.join(field.key for field in fields)})}",
        )
        return self._flatten_latest(raw, fields)

    def history(
        self,
        device_uuid: str,
        telemetry_fields: Iterable[TelemetryField],
        start_ts: int,
        end_ts: int,
        limit: int = 500,
    ) -> dict[str, Any]:
        fields = tuple(telemetry_fields)
        query = urlencode({
            "keys": ",".join(field.key for field in fields),
            "startTs": start_ts,
            "endTs": end_ts,
            "limit": limit,
            "agg": "NONE",
        })
        raw = self._request(
            "GET",
            f"/api/plugins/telemetry/DEVICE/{device_uuid}/values/timeseries?{query}",
        )
        field_types = {field.key: field.value_type for field in fields}
        return {
            key: [
                {"ts": sample.get("ts"), "value": self.convert_value(sample.get("value"), field_types.get(key, "string"))}
                for sample in samples
            ]
            for key, samples in raw.items()
            if isinstance(samples, list)
        }

    def status(
        self,
        device_uuid: str,
        device_name: str,
        telemetry_fields: Iterable[TelemetryField],
        freshness_seconds: int = 30,
    ) -> dict[str, Any]:
        latest = self.latest(device_uuid, telemetry_fields)
        timestamps = [item["ts"] for item in latest.values() if isinstance(item, dict) and item.get("ts")]
        last_update = max(timestamps) if timestamps else None
        return {
            "device_id": device_name,
            "cloud_configured": True,
            "active": bool(last_update and int(time.time() * 1000) - last_update <= freshness_seconds * 1000),
            "last_update_ms": last_update,
        }

    def rpc(self, device_uuid: str, method: str, params: bool | str | int | float) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/rpc/twoway/{device_uuid}",
            {"method": method, "params": params},
        )

    def alarms(self, device_uuid: str) -> dict[str, Any]:
        query = urlencode({"pageSize": 50, "page": 0, "sortProperty": "createdTime", "sortOrder": "DESC"})
        return self._request("GET", f"/api/alarm/DEVICE/{device_uuid}?{query}")

    def alarms_for_devices(self, device_uuids: Iterable[str]) -> dict[str, Any]:
        merged: list[dict[str, Any]] = []
        for device_uuid in dict.fromkeys(device_uuids):
            response = self.alarms(device_uuid)
            merged.extend(response.get("data", []))
        merged.sort(key=lambda alarm: alarm.get("createdTime", alarm.get("startTs", 0)), reverse=True)
        return {"data": merged}

    def acknowledge_alarm(self, alarm_id: str) -> None:
        self._request("POST", f"/api/alarm/{alarm_id}/ack")

    def clear_alarm(self, alarm_id: str) -> None:
        self._request("POST", f"/api/alarm/{alarm_id}/clear")

    def create_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        device = self._request("POST", "/api/device", payload)
        if not device.get("id", {}).get("id"):
            raise ThingsBoardError("ThingsBoard did not return the created device UUID")
        name = device.get("name") or payload.get("name")
        if name:
            self._device_uuid_cache[str(name)] = str(device["id"]["id"])
        return device

    def device_identity(self, device_name: str) -> dict[str, Any]:
        device = self.get_device(device_name)
        resolved_uuid = device["id"]["id"]
        return {
            "resolved_name_uuid": resolved_uuid,
            "resolved_name": device.get("name"),
            "identity_matches": device.get("name") == device_name,
        }

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        if not self.api_configured:
            raise ThingsBoardError("ThingsBoard REST API key is not configured")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Authorization": f"ApiKey {self.settings.thingsboard_api_key}",
        }
        request = Request(
            f"{self.settings.thingsboard_base_url.rstrip('/')}{path}",
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=10) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except (HTTPError, URLError, TimeoutError) as error:
            raise ThingsBoardError(f"ThingsBoard REST request failed: {error}") from error

    @staticmethod
    def convert_value(value: Any, value_type: TelemetryType) -> str | int | float | bool | None:
        if value is None:
            return None
        if value_type == "boolean":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"true", "1", "yes", "on"}
        if value_type == "number":
            number = float(value)
            return int(number) if number.is_integer() else number
        return str(value)

    @classmethod
    def _flatten_latest(
        cls,
        raw: dict[str, list[dict[str, Any]]],
        telemetry_fields: Iterable[TelemetryField],
    ) -> dict[str, Any]:
        field_types = {field.key: field.value_type for field in telemetry_fields}
        result: dict[str, Any] = {}
        for key, samples in raw.items():
            if samples:
                sample = samples[0]
                result[key] = {
                    "value": cls.convert_value(sample.get("value"), field_types.get(key, "string")),
                    "ts": sample.get("ts"),
                }
        return result

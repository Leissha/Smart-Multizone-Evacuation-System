from fastapi.testclient import TestClient

from backend.app.api.devices import get_thingsboard_service
from backend.app.config import Settings
from backend.app.main import app
from backend.app.nodes.contracts import TelemetryField
from backend.app.nodes.registry import get_node_contract, list_node_contracts
from backend.app.services.thingsboard_rest import ThingsBoardError, ThingsBoardRestService
import backend.app.services.thingsboard_rest as thingsboard_rest_module


class FakeThingsBoard:
    api_configured = True

    def __init__(self):
        self.rpc_calls = []

    def resolve_device_uuid(self, device_name):
        return f"uuid-{device_name}"

    def status(self, device_uuid, device_name, telemetry_fields, freshness_seconds):
        return {
            "device_id": device_name,
            "cloud_configured": True,
            "active": device_name in {"node-2-exit-monitoring", "node-3-equipment-room"},
            "last_update_ms": 123,
        }

    def latest(self, device_uuid, telemetry_fields):
        field = tuple(telemetry_fields)[0]
        return {field.key: {"value": 116 if field.value_type == "number" else False, "ts": 123}}

    def history(self, device_uuid, telemetry_fields, start_ts, end_ts, limit):
        return {field.key: [] for field in telemetry_fields}

    def rpc(self, device_uuid, method, params):
        self.rpc_calls.append((device_uuid, method, params))
        return {"success": True, "method": method, "applied": params}

    def alarms_for_devices(self, device_uuids):
        return {"data": []}

    def acknowledge_alarm(self, alarm_id): return None
    def clear_alarm(self, alarm_id): return None

    def create_device(self, payload):
        return {"id": {"id": "new-device-uuid"}, "name": payload["name"]}


fake_service = FakeThingsBoard()
app.dependency_overrides[get_thingsboard_service] = lambda: fake_service
client = TestClient(app)


def test_registry_contains_typed_contracts():
    contracts = list_node_contracts()
    assert [contract.device_id for contract in contracts] == [
        "node-1-fire-detection", "node-2-exit-monitoring",
        "node-3-equipment-room", "node-4-command-center",
    ]
    node3 = get_node_contract("node-3-equipment-room")
    assert node3 is not None
    assert node3.telemetry_keys[:2] == ("sound_level", "vibration_detected")
    assert node3.rpc_methods == ("setRelay", "setBuzzer", "setAll")
    assert get_node_contract("unknown") is None


def test_health_and_generic_node_list():
    assert client.get("/health").json() == {"status": "ok"}
    nodes = client.get("/api/nodes").json()
    assert len(nodes) == 4
    assert nodes[0]["telemetry_contract"][0] == {"key": "temperature", "type": "number", "unit": "°C"}
    assert client.get("/api/devices").json() == nodes
    assert client.get("/api/nodes/node-2-exit-monitoring").status_code == 200
    assert client.get("/api/nodes/unknown").status_code == 404


def test_status_latest_and_history_work_for_any_registered_node():
    for node_id in ("node-1-fire-detection", "node-2-exit-monitoring", "node-3-equipment-room", "node-4-command-center"):
        assert client.get(f"/api/nodes/{node_id}/status").status_code == 200
        assert client.get(f"/api/nodes/{node_id}/telemetry/latest").status_code == 200
        assert client.get(f"/api/nodes/{node_id}/telemetry/history").status_code == 200


def test_rpc_validation_depends_on_node_contract():
    valid = client.post(
        "/api/nodes/node-3-equipment-room/rpc",
        json={"method": "setRelay", "params": False},
    )
    assert valid.status_code == 200 and valid.json()["accepted"] is True
    assert fake_service.rpc_calls[-1][1:] == ("setRelay", False)

    unsupported = client.post(
        "/api/nodes/node-1-fire-detection/rpc",
        json={"method": "setRelay", "params": True},
    )
    assert unsupported.status_code == 400
    assert client.post(
        "/api/nodes/node-3-equipment-room/rpc",
        json={"method": "arbitraryMethod", "params": True},
    ).status_code == 400
    assert client.post(
        "/api/nodes/node-3-equipment-room/rpc",
        json={"method": "setRelay", "params": "yes"},
    ).status_code == 422


def test_node3_legacy_control_routes_still_work():
    assert client.post("/api/devices/node-3-equipment-room/relay", json={"enabled": True}).status_code == 200
    assert client.post("/api/devices/node-3-equipment-room/buzzer", json={"enabled": False}).status_code == 200


def test_system_status_counts_each_node_independently():
    body = client.get("/api/system/status").json()
    assert body["live_nodes"] == 2
    assert body["simulated_nodes"] == 2
    assert client.get("/api/monitor/alarms").status_code == 200


def test_one_missing_node_does_not_break_system_status():
    class PartialFake(FakeThingsBoard):
        def resolve_device_uuid(self, device_name):
            if device_name == "node-1-fire-detection":
                raise ThingsBoardError("not provisioned")
            return super().resolve_device_uuid(device_name)

    app.dependency_overrides[get_thingsboard_service] = lambda: PartialFake()
    try:
        response = client.get("/api/system/status")
        assert response.status_code == 200
        assert response.json()["live_nodes"] == 2
        assert client.get("/api/nodes/node-1-fire-detection/status").json()["active"] is False
    finally:
        app.dependency_overrides[get_thingsboard_service] = lambda: fake_service


def test_add_device_does_not_expose_secrets():
    response = client.post("/api/nodes", json={
        "display_name": "Node 2 – Exit Monitoring",
        "device_name": "node-2-exit-monitoring",
        "zone": "Zone 2",
        "purpose": "Hallway / exit zone",
        "telemetry_contract": ["distance_cm", "exit_blocked"],
        "rpc_methods": [],
        "notes": "",
    })
    assert response.status_code == 201
    serialized = response.text
    assert response.json()["device_uuid"] == "new-device-uuid"
    assert "THINGSBOARD_API_KEY" not in serialized
    assert "<copy-from-thingsboard-device-credentials>" in serialized


def test_generic_value_conversion_and_latest_mapping():
    fields = (
        TelemetryField("temperature", "number"),
        TelemetryField("fire_detected", "boolean"),
        TelemetryField("display_state", "string"),
    )
    mapped = ThingsBoardRestService._flatten_latest({
        "temperature": [{"value": "24.5", "ts": 1}],
        "fire_detected": [{"value": "true", "ts": 2}],
        "display_state": [{"value": "Standby", "ts": 3}],
    }, fields)
    assert mapped["temperature"]["value"] == 24.5
    assert mapped["fire_detected"]["value"] is True
    assert mapped["display_state"]["value"] == "Standby"


def test_device_lookup_is_cached():
    service = ThingsBoardRestService(Settings(thingsboard_api_key="test-key"))
    calls = []
    service.get_device = lambda name: calls.append(name) or {"id": {"id": "resolved-uuid"}, "name": name}
    assert service.resolve_device_uuid("node-2-exit-monitoring") == "resolved-uuid"
    assert service.resolve_device_uuid("node-2-exit-monitoring") == "resolved-uuid"
    assert calls == ["node-2-exit-monitoring"]


def test_rest_uses_programmatic_api_key(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"{}"

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("X-authorization")
        return Response()

    monkeypatch.setattr(thingsboard_rest_module, "urlopen", fake_urlopen)
    service = ThingsBoardRestService(Settings(thingsboard_api_key="test-key"))
    service._request("GET", "/api/auth/user")
    assert captured["authorization"] == "ApiKey test-key"

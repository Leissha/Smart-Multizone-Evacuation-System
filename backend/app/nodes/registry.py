from __future__ import annotations

from backend.app.nodes.contracts import NodeContract, TelemetryField


NODE_CONTRACTS: tuple[NodeContract, ...] = (
    NodeContract(
        device_id="node-1-fire-detection",
        display_name="Node 1 – Fire Detection",
        zone="Zone 1",
        purpose="Kitchen / lab fire zone",
        telemetry_fields=(
            TelemetryField("temperature", "number", "°C"),
            TelemetryField("smoke_level", "string"),
            TelemetryField("fire_detected", "boolean"),
        ),
        accent="coral",
    ),
    NodeContract(
        device_id="node-2-exit-monitoring",
        display_name="Node 2 – Exit Monitoring",
        zone="Zone 2",
        purpose="Hallway / exit zone",
        telemetry_fields=(
            TelemetryField("distance_cm", "number", "cm"),
            TelemetryField("exit_blocked", "boolean"),
        ),
        accent="sage",
    ),
    NodeContract(
        device_id="node-3-equipment-room",
        display_name="Node 3 – Equipment Room",
        zone="Zone 3",
        purpose="Server / equipment monitoring",
        telemetry_fields=(
            TelemetryField("sound_level", "number", "ADC"),
            TelemetryField("vibration_detected", "boolean"),
            TelemetryField("relay_state", "boolean"),
            TelemetryField("buzzer_state", "boolean"),
            TelemetryField("equipment_fault", "boolean"),
        ),
        rpc_methods=("setRelay", "setBuzzer", "setAll"),
        accent="gold",
    ),
    NodeContract(
        device_id="node-4-command-center",
        display_name="Node 4 – Command Centre",
        zone="Zone 4",
        purpose="Central command terminal",
        telemetry_fields=(
            TelemetryField("manual_emergency", "boolean"),
            TelemetryField("display_state", "string"),
            TelemetryField("master_buzzer", "boolean"),
        ),
        rpc_methods=("setLockdown", "setBuzzer"),
        accent="blue",
    ),
)

_BY_ID = {contract.device_id: contract for contract in NODE_CONTRACTS}


def list_node_contracts() -> tuple[NodeContract, ...]:
    return NODE_CONTRACTS


def get_node_contract(device_id: str) -> NodeContract | None:
    return _BY_ID.get(device_id)
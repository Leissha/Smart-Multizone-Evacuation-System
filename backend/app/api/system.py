from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends

from backend.app.api.devices import get_thingsboard_service
from backend.app.models.devices import SystemStatus
from backend.app.nodes.registry import list_node_contracts
from backend.app.services.thingsboard_rest import ThingsBoardError, ThingsBoardRestService

router = APIRouter(prefix="/api", tags=["system"])
Service = Annotated[ThingsBoardRestService, Depends(get_thingsboard_service)]


@router.get("/system/status", response_model=SystemStatus)
def system_status(service: Service) -> SystemStatus:
    live_nodes = 0
    resolved_uuids: list[str] = []
    cloud_connected = service.api_configured
    for contract in list_node_contracts():
        try:
            device_uuid = service.resolve_device_uuid(contract.device_id)
            resolved_uuids.append(device_uuid)
            node_status = service.status(
                device_uuid,
                contract.device_id,
                contract.telemetry_fields,
                contract.freshness_seconds,
            )
            live_nodes += int(node_status["active"])
        except ThingsBoardError:
            continue
    try:
        alarms = service.alarms_for_devices(resolved_uuids).get("data", []) if resolved_uuids else []
        active = [alarm for alarm in alarms if not alarm.get("cleared", False)]
        return SystemStatus(
            thingsboard_connected=cloud_connected,
            active_alarm_count=len(active),
            live_nodes=live_nodes,
            simulated_nodes=4 - live_nodes,
        )
    except ThingsBoardError:
        return SystemStatus(
            thingsboard_connected=cloud_connected,
            live_nodes=live_nodes,
            simulated_nodes=4 - live_nodes,
        )


@router.get("/events")
@router.get("/monitor/events")
def events() -> dict[str, object]:
    return {"data": [], "message": "Event persistence is not configured; no production events are fabricated."}


@router.get("/rules")
@router.get("/automation/rules")
def rules() -> dict[str, object]:
    return {
        "data": [],
        "management_supported": False,
        "message": "Rule-chain mutation is intentionally disabled until safe ThingsBoard management is verified.",
    }

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.config import Settings, get_settings
from backend.app.models.devices import (
    ControlRequest,
    ControlResponse,
    DeviceCreateRequest,
    DeviceProvisionResponse,
    DeviceStatus,
    DeviceSummary,
    RpcRequest,
)
from backend.app.nodes.contracts import NodeContract
from backend.app.nodes.registry import get_node_contract, list_node_contracts
from backend.app.services.thingsboard_rest import ThingsBoardError, ThingsBoardRestService

router = APIRouter(prefix="/api", tags=["nodes"])


def get_thingsboard_service(settings: Annotated[Settings, Depends(get_settings)]) -> ThingsBoardRestService:
    return ThingsBoardRestService(settings)


Service = Annotated[ThingsBoardRestService, Depends(get_thingsboard_service)]


def require_registered_node(device_id: str) -> NodeContract:
    contract = get_node_contract(device_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Unknown project node")
    return contract


def translate_error(error: ThingsBoardError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(error))


def contract_summary(contract: NodeContract) -> DeviceSummary:
    return DeviceSummary(
        device_id=contract.device_id,
        name=contract.display_name,
        role=contract.purpose,
        zone=contract.zone,
        telemetry_contract=[
            {"key": field.key, "type": field.value_type, "unit": field.unit}
            for field in contract.telemetry_fields
        ],
        rpc_methods=list(contract.rpc_methods),
        freshness_seconds=contract.freshness_seconds,
        accent=contract.accent,
    )


def unavailable_status(contract: NodeContract, cloud_configured: bool) -> DeviceStatus:
    return DeviceStatus(
        device_id=contract.device_id,
        cloud_configured=cloud_configured,
        active=False,
        last_update_ms=None,
    )


@router.get("/devices", response_model=list[DeviceSummary])
@router.get("/nodes", response_model=list[DeviceSummary])
def list_devices() -> list[DeviceSummary]:
    return [contract_summary(contract) for contract in list_node_contracts()]


@router.get("/nodes/{device_id}", response_model=DeviceSummary)
def node_detail(device_id: str) -> DeviceSummary:
    return contract_summary(require_registered_node(device_id))


@router.get("/nodes/telemetry/latest")
def latest_node_telemetry(service: Service) -> dict[str, dict]:
    """Return the latest telemetry for every registered node in one response."""
    snapshot: dict[str, dict] = {}
    for contract in list_node_contracts():
        try:
            device_uuid = service.resolve_device_uuid(contract.device_id)
            snapshot[contract.device_id] = service.latest(device_uuid, contract.telemetry_fields)
        except ThingsBoardError:
            snapshot[contract.device_id] = {}
    return snapshot


@router.post("/devices", response_model=DeviceProvisionResponse, status_code=201)
@router.post("/nodes", response_model=DeviceProvisionResponse, status_code=201)
def create_device(payload: DeviceCreateRequest, service: Service) -> DeviceProvisionResponse:
    try:
        created = service.create_device({
            "name": payload.device_name,
            "label": payload.display_name,
            "type": "evacuation-node",
            "additionalInfo": {
                "zone": payload.zone,
                "purpose": payload.purpose,
                "telemetryContract": payload.telemetry_contract,
                "rpcMethods": payload.rpc_methods,
                "notes": payload.notes,
            },
        })
        device_uuid = created["id"]["id"]
        template = "\n".join([
            f"DEVICE_ID={payload.device_name}",
            "THINGSBOARD_HOST=mqtt.thingsboard.cloud",
            "THINGSBOARD_PORT=8883",
            "THINGSBOARD_TLS=true",
            "THINGSBOARD_ACCESS_TOKEN=<copy-from-thingsboard-device-credentials>",
        ])
        return DeviceProvisionResponse(
            device_name=payload.device_name,
            device_uuid=device_uuid,
            edge_config_template=template,
            credential_message="Device created. Copy its access token from ThingsBoard Credentials into the edge .env; this API does not return credentials.",
        )
    except ThingsBoardError as error:
        raise translate_error(error) from error


@router.get("/devices/{device_id}/status", response_model=DeviceStatus)
@router.get("/nodes/{device_id}/status", response_model=DeviceStatus)
def device_status(device_id: str, service: Service) -> DeviceStatus:
    contract = require_registered_node(device_id)
    try:
        device_uuid = service.resolve_device_uuid(contract.device_id)
        return DeviceStatus.model_validate(service.status(
            device_uuid,
            contract.device_id,
            contract.telemetry_fields,
            contract.freshness_seconds,
        ))
    except ThingsBoardError:
        return unavailable_status(contract, service.api_configured)


@router.get("/devices/{device_id}/telemetry/latest")
@router.get("/nodes/{device_id}/telemetry/latest")
def latest_telemetry(device_id: str, service: Service) -> dict:
    contract = require_registered_node(device_id)
    try:
        return service.latest(service.resolve_device_uuid(contract.device_id), contract.telemetry_fields)
    except ThingsBoardError:
        return {}


@router.get("/devices/{device_id}/telemetry/history")
@router.get("/nodes/{device_id}/telemetry/history")
def telemetry_history(
    device_id: str,
    service: Service,
    start_ts: int = Query(default_factory=lambda: int((time.time() - 3600) * 1000)),
    end_ts: int = Query(default_factory=lambda: int(time.time() * 1000)),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    contract = require_registered_node(device_id)
    try:
        return service.history(
            service.resolve_device_uuid(contract.device_id),
            contract.telemetry_fields,
            start_ts,
            end_ts,
            limit,
        )
    except ThingsBoardError:
        return {}


def send_control(
    contract: NodeContract,
    method: str,
    params: bool,
    service: ThingsBoardRestService,
) -> ControlResponse:
    if method not in contract.rpc_methods:
        raise HTTPException(status_code=400, detail=f"RPC method is not allowed for {contract.device_id}")
    try:
        result = service.rpc(service.resolve_device_uuid(contract.device_id), method, params)
        return ControlResponse(accepted=bool(result.get("success")), method=method, result=result)
    except ThingsBoardError as error:
        raise translate_error(error) from error


@router.post("/devices/{device_id}/relay", response_model=ControlResponse)
def set_relay(device_id: str, payload: ControlRequest, service: Service) -> ControlResponse:
    return send_control(require_registered_node(device_id), "setRelay", payload.enabled, service)


@router.post("/devices/{device_id}/buzzer", response_model=ControlResponse)
def set_buzzer(device_id: str, payload: ControlRequest, service: Service) -> ControlResponse:
    return send_control(require_registered_node(device_id), "setBuzzer", payload.enabled, service)


@router.post("/nodes/{device_id}/rpc", response_model=ControlResponse)
def node_rpc(device_id: str, payload: RpcRequest, service: Service) -> ControlResponse:
    return send_control(require_registered_node(device_id), payload.method, payload.params, service)


def resolved_project_uuids(service: ThingsBoardRestService, device_id: str | None = None) -> list[str]:
    contracts = [require_registered_node(device_id)] if device_id else list(list_node_contracts())
    resolved: list[str] = []
    for contract in contracts:
        try:
            resolved.append(service.resolve_device_uuid(contract.device_id))
        except ThingsBoardError:
            continue
    return resolved


@router.get("/alarms")
@router.get("/monitor/alarms")
def alarms(service: Service, node_id: str | None = Query(None)) -> dict:
    uuids = resolved_project_uuids(service, node_id)
    if not uuids:
        return {"data": []}
    try:
        return service.alarms_for_devices(uuids)
    except ThingsBoardError as error:
        raise translate_error(error) from error


@router.post("/alarms/{alarm_id}/ack")
@router.post("/monitor/alarms/{alarm_id}/ack")
def acknowledge_alarm(alarm_id: str, service: Service) -> dict[str, bool]:
    try:
        service.acknowledge_alarm(alarm_id)
        return {"success": True}
    except ThingsBoardError as error:
        raise translate_error(error) from error


@router.post("/alarms/{alarm_id}/clear")
@router.post("/monitor/alarms/{alarm_id}/clear")
def clear_alarm(alarm_id: str, service: Service) -> dict[str, bool]:
    try:
        service.clear_alarm(alarm_id)
        return {"success": True}
    except ThingsBoardError as error:
        raise translate_error(error) from error

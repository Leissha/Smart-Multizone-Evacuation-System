from devices.node3.edge.actuator_service import ActuatorService
from devices.node3.edge.sensor_parser import parse_bool, parse_telemetry_line
from devices.node3.edge.thingsboard_client import (
    RPC_COMMANDS,
    TELEMETRY_TOPIC,
    ThingsBoardClient,
    connection_failed,
    rpc_request_id,
    rpc_response_topic,
    token_fingerprint,
)


class FakeSerial:
    def __init__(self, succeeds=True): self.sent, self.succeeds = [], succeeds
    def send_command(self, command): self.sent.append(command); return self.succeeds


class Config:
    thingsboard_enabled = False
    thingsboard_access_token = ""


class FakeReasonCode:
    def __init__(self, is_failure):
        self.is_failure = is_failure

    def __str__(self):
        return "Success" if not self.is_failure else "Not authorized"


class FakePublishResult:
    rc = 0
    mid = 42


class FakeMqttClient:
    def __init__(self): self.published = []
    def publish(self, topic, payload, qos):
        self.published.append((topic, payload, qos))
        return FakePublishResult()


def test_valid_node3_telemetry_and_booleans():
    result = parse_telemetry_line(
        "sound_level=116,vibration_detected=true,relay_state=false,buzzer_state=false"
    )
    assert result == {"sound_level": 116, "vibration_detected": True, "relay_state": False, "buzzer_state": False}
    assert parse_bool("TRUE") is True


def test_malformed_telemetry_is_ignored():
    assert parse_telemetry_line("sound_level=nope,vibration_detected=true") is None
    assert parse_telemetry_line("ACK=RELAY_ON") is None


def test_expected_ack_completes_command():
    outcomes = []
    service = ActuatorService(2)
    serial = FakeSerial()
    service.request("RELAY_ON", lambda ok, message: outcomes.append((ok, message)))
    service.tick(serial, now=10)
    assert serial.sent == ["RELAY_ON"]
    assert service.handle_ack("ACK=RELAY_ON") is True
    assert outcomes[0][0] is True


def test_timeout_wrong_ack_and_serial_failure_fail():
    outcomes = []
    service = ActuatorService(2)
    service.request("BUZZER_ON", lambda ok, message: outcomes.append(ok))
    service.tick(FakeSerial(), now=10)
    service.tick(FakeSerial(), now=12)
    assert outcomes == [False]

    service.request("RELAY_OFF", lambda ok, message: outcomes.append(ok))
    service.tick(FakeSerial(), now=20)
    assert service.handle_ack("ACK=RELAY_ON") is False
    assert outcomes[-1] is False

    service.request("ALL_OFF", lambda ok, message: outcomes.append(ok))
    service.tick(FakeSerial(False), now=30)
    assert outcomes[-1] is False


def test_mqtt_disabled_and_disconnected_are_safe():
    service = ThingsBoardClient(Config(), ActuatorService())
    service.start()
    assert service.publish_telemetry({"sound_level": 12}) is False
    fake = type("Mqtt", (), {"subscribe": lambda *args, **kwargs: (0, 1)})()
    service._on_connect(fake, None, None, FakeReasonCode(False), None)
    assert service.connected is True
    service._on_disconnect(fake, None, None, FakeReasonCode(True), None)
    assert service.connected is False


def test_paho_v2_reason_code_is_not_converted_to_int():
    assert connection_failed(FakeReasonCode(False)) is False
    assert connection_failed(FakeReasonCode(True)) is True
    assert connection_failed(0) is False
    assert connection_failed(5) is True


def test_rpc_topics_and_token_fingerprint_are_safe():
    assert rpc_request_id("v1/devices/me/rpc/request/27") == "27"
    assert rpc_response_topic("27") == "v1/devices/me/rpc/response/27"
    fingerprint = token_fingerprint("abcdefghijklmnop")
    assert fingerprint == "abcd...mnop"
    assert "efghijkl" not in fingerprint


def test_telemetry_publish_omits_none_and_response_topic_is_exact():
    mqtt_client = FakeMqttClient()
    service = ThingsBoardClient(Config(), ActuatorService())
    service.client = mqtt_client
    service.connected = True
    assert service.publish_telemetry({"sound_level": 116, "unused": None}) is True
    assert mqtt_client.published[0] == (TELEMETRY_TOPIC, '{"sound_level":116}', 1)
    service.respond("9", {"success": True})
    assert mqtt_client.published[1][0] == "v1/devices/me/rpc/response/9"


def test_rpc_waits_for_ack_and_returns_state():
    responses = []
    actuators = ActuatorService()
    client = ThingsBoardClient(Config(), actuators)
    client.respond = lambda request_id, response: responses.append((request_id, response))
    client.handle_rpc_payload("7", {"method": "setBuzzer", "params": True})
    assert responses == []
    actuators.tick(FakeSerial(), now=1)
    actuators.handle_ack("ACK=BUZZER_ON")
    assert responses == [("7", {"success": True, "method": "setBuzzer", "buzzer_state": True})]


def test_equipment_alarm_rpc_isolates_equipment_and_uses_matching_acks():
    assert RPC_COMMANDS == {
        "setRelay": ("RELAY_ON", "RELAY_OFF", "relay_state"),
        "setBuzzer": ("BUZZER_ON", "BUZZER_OFF", "buzzer_state"),
        "setEquipmentAlarm": (
            "EQUIPMENT_ALARM_ON",
            "EQUIPMENT_ALARM_OFF",
            "equipment_alarm",
        ),
    }

    for request_id, enabled, command in (
        ("8", True, "EQUIPMENT_ALARM_ON"),
        ("9", False, "EQUIPMENT_ALARM_OFF"),
    ):
        responses = []
        actuators = ActuatorService()
        client = ThingsBoardClient(Config(), actuators)
        client.respond = lambda response_id, response: responses.append((response_id, response))

        client.handle_rpc_payload(
            request_id,
            {"method": "setEquipmentAlarm", "params": enabled},
        )
        serial = FakeSerial()
        actuators.tick(serial, now=1)
        assert serial.sent == [command]
        assert responses == []
        assert actuators.handle_ack(f"ACK={command}") is True
        assert responses == [(
            request_id,
            {
                "success": True,
                "method": "setEquipmentAlarm",
                "equipment_alarm": enabled,
            },
        )]


def test_old_and_unknown_rpc_methods_are_rejected():
    responses = []
    client = ThingsBoardClient(Config(), ActuatorService())
    client.respond = lambda request_id, response: responses.append((request_id, response))

    client.handle_rpc_payload("10", {"method": "setAll", "params": True})
    client.handle_rpc_payload("11", {"method": "notSupported", "params": True})

    assert responses == [
        ("10", {"success": False, "method": "setAll", "error": "unsupported method"}),
        ("11", {"success": False, "method": "notSupported", "error": "unsupported method"}),
    ]

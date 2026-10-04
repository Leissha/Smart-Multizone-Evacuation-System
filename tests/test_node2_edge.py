from devices.node2.edge.actuator_service import ActuatorService, is_valid_command
from devices.node2.edge.sensor_parser import parse_telemetry_line
from devices.node2.edge.thingsboard_client import ThingsBoardClient, threshold_param

FRAME = (
    "distance_cm=23.4, exit_blocked=true, threshold_cm=50, evacuation_mode=false, "
    "exit_closed=false, buzzer_state=false, sensor_ok=true"
)


class FakeSerial:
    def __init__(self, succeeds=True): self.sent, self.succeeds = [], succeeds
    def send_command(self, command): self.sent.append(command); return self.succeeds


class Config:
    thingsboard_enabled = False
    thingsboard_access_token = ""


def make_client():
    responses = []
    actuators = ActuatorService()
    client = ThingsBoardClient(Config(), actuators)
    client.respond = lambda request_id, response: responses.append((request_id, response))
    return client, actuators, responses


def test_valid_node2_frame_is_typed():
    assert parse_telemetry_line(FRAME) == {
        "distance_cm": 23.4, "threshold_cm": 50, "exit_blocked": True, "evacuation_mode": False,
        "exit_closed": False, "buzzer_state": False, "sensor_ok": True,
    }


def test_malformed_out_of_range_and_status_lines_are_ignored():
    assert parse_telemetry_line(FRAME.replace("23.4", "abc")) is None
    assert parse_telemetry_line(FRAME.replace("23.4", "999")) is None
    assert parse_telemetry_line(FRAME.replace(", sensor_ok=true", "")) is None
    assert parse_telemetry_line("ACK=EVAC_ON") is None
    assert parse_telemetry_line("Node 2 exit monitor started") is None


def test_command_validation_includes_threshold_range():
    assert is_valid_command("EXIT_CLOSE")
    assert is_valid_command("THRESHOLD=40")
    assert not is_valid_command("THRESHOLD=2")
    assert not is_valid_command("THRESHOLD=abc")
    assert not is_valid_command("RELAY_ON")


def test_queued_commands_are_sent_one_at_a_time():
    outcomes = []
    service = ActuatorService(2)
    serial = FakeSerial()
    service.request("EVAC_ON", lambda ok, msg: outcomes.append(("evac", ok)))
    service.request("THRESHOLD=40", lambda ok, msg: outcomes.append(("threshold", ok)))
    service.tick(serial, now=1)
    assert serial.sent == ["EVAC_ON"]
    service.tick(serial, now=1.1)
    assert serial.sent == ["EVAC_ON"]
    assert service.handle_ack("ACK=EVAC_ON") is True
    service.tick(serial, now=1.2)
    assert serial.sent == ["EVAC_ON", "THRESHOLD=40"]
    assert service.handle_ack("ACK=THRESHOLD=40") is True
    assert outcomes == [("evac", True), ("threshold", True)]


def test_timeout_and_arduino_error_fail_the_command():
    outcomes = []
    service = ActuatorService(2)
    service.request("BUZZER_ON", lambda ok, msg: outcomes.append(ok))
    service.tick(FakeSerial(), now=10)
    service.tick(FakeSerial(), now=12)
    service.request("THRESHOLD=300", lambda ok, msg: outcomes.append(ok))
    service.tick(FakeSerial(), now=20)
    assert service.handle_error("ERROR=THRESHOLD_OUT_OF_RANGE:THRESHOLD=300") is True
    assert outcomes == [False, False]


def test_boolean_rpc_waits_for_ack_and_returns_state():
    client, actuators, responses = make_client()
    client.handle_rpc_payload("7", {"method": "setExitClosed", "params": True})
    assert responses == []
    serial = FakeSerial()
    actuators.tick(serial, now=1)
    assert serial.sent == ["EXIT_CLOSE"]
    actuators.handle_ack("ACK=EXIT_CLOSE")
    assert responses == [("7", {"success": True, "method": "setExitClosed", "exit_closed": True})]


def test_threshold_rpc_validates_and_configures_arduino():
    client, actuators, responses = make_client()
    client.handle_rpc_payload("8", {"method": "setThreshold", "params": 1000})
    assert responses[-1][1]["success"] is False
    client.handle_rpc_payload("9", {"method": "setThreshold", "params": {"value": 35}})
    serial = FakeSerial()
    actuators.tick(serial, now=1)
    assert serial.sent == ["THRESHOLD=35"]
    actuators.handle_ack("ACK=THRESHOLD=35")
    assert responses[-1] == ("9", {"success": True, "method": "setThreshold", "threshold_cm": 35})


def test_unsupported_rpc_and_get_state():
    client, _, responses = make_client()
    client.handle_rpc_payload("1", {"method": "setRelay", "params": True})
    assert responses[-1][1] == {"success": False, "method": "setRelay", "error": "unsupported method"}
    client.publish_telemetry(parse_telemetry_line(FRAME))
    client.handle_rpc_payload("2", {"method": "getState"})
    assert responses[-1][1]["exit_blocked"] is True and responses[-1][1]["success"] is True


def test_shared_attribute_threshold_is_applied_once():
    client, actuators, _ = make_client()
    client.publish_telemetry(parse_telemetry_line(FRAME))
    client.handle_attributes({"threshold_cm": 50})
    serial = FakeSerial()
    actuators.tick(serial, now=1)
    assert serial.sent == []
    client.handle_attributes({"threshold_cm": "40"})
    client.handle_attributes({"threshold_cm": True})
    actuators.tick(serial, now=2)
    assert serial.sent == ["THRESHOLD=40"]


def test_threshold_param_rejects_bad_values():
    assert threshold_param(30) == 30
    assert threshold_param("30") == 30
    for bad in (True, 30.5, "x", 4, 301, None):
        try:
            threshold_param(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should be rejected")

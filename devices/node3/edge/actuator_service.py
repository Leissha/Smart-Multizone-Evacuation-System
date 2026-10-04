from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
import time
from typing import Callable


Completion = Callable[[bool, str], None]
VALID_COMMANDS = {
    "RELAY_ON",
    "RELAY_OFF",
    "BUZZER_ON",
    "BUZZER_OFF",
    "ALL_ON",
    "ALL_OFF",
    "EQUIPMENT_ALARM_ON",
    "EQUIPMENT_ALARM_OFF",
}


@dataclass
class PendingCommand:
    command: str
    callback: Completion
    sent_at: float | None = None


class ActuatorService:
    """Owns the requested -> sent -> matching ACK command lifecycle."""

    def __init__(self, ack_timeout: float = 3.0) -> None:
        self.ack_timeout = ack_timeout
        self.pending: PendingCommand | None = None
        self._lock = RLock()

    def request(self, command: str, callback: Completion) -> bool:
        if command not in VALID_COMMANDS:
            callback(False, f"unsupported command: {command}")
            return False
        with self._lock:
            if self.pending is not None:
                callback(False, "another actuator command is already pending")
                return False
            self.pending = PendingCommand(command, callback)
            return True

    def tick(self, serial_client: object, now: float | None = None) -> None:
        with self._lock:
            if self.pending is None:
                return
            current = time.monotonic() if now is None else now
            if self.pending.sent_at is None:
                if not serial_client.send_command(self.pending.command):
                    self._finish(False, "serial write failed")
                    return
                self.pending.sent_at = current
            elif current - self.pending.sent_at >= self.ack_timeout:
                self._finish(False, "Arduino acknowledgement timed out")

    def handle_ack(self, line: str) -> bool:
        with self._lock:
            if self.pending is None or self.pending.sent_at is None:
                return False
            expected = f"ACK={self.pending.command}"
            if line != expected:
                self._finish(False, f"unexpected acknowledgement: {line}")
                return False
            self._finish(True, expected)
            return True

    def _finish(self, success: bool, message: str) -> None:
        pending = self.pending
        self.pending = None
        if pending:
            pending.callback(success, message)


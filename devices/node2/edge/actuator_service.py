from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
from threading import RLock
import time
from typing import Callable


Completion = Callable[[bool, str], None]
FIXED_COMMANDS = {
    "EVAC_ON", "EVAC_OFF", "EXIT_CLOSE", "EXIT_OPEN", "BUZZER_ON", "BUZZER_OFF"
}
THRESHOLD_PATTERN = re.compile(r"THRESHOLD=(\d{1,3})")
MIN_THRESHOLD_CM = 5
MAX_THRESHOLD_CM = 300
MAX_QUEUED = 5


def is_valid_command(command: str) -> bool:
    if command in FIXED_COMMANDS:
        return True
    match = THRESHOLD_PATTERN.fullmatch(command)
    return bool(match) and MIN_THRESHOLD_CM <= int(match.group(1)) <= MAX_THRESHOLD_CM


@dataclass
class PendingCommand:
    command: str
    callback: Completion
    sent_at: float | None = None


class ActuatorService:
    """Owns the requested -> sent -> matching ACK command lifecycle.

    Unlike Node 3/4, Node 2 can receive an RPC and a shared-attribute update
    at the same moment, so commands wait in a short queue and are sent to the
    Arduino one at a time.
    """

    def __init__(self, ack_timeout: float = 3.0) -> None:
        self.ack_timeout = ack_timeout
        self.pending: PendingCommand | None = None
        self.queue: deque[PendingCommand] = deque()
        self._lock = RLock()

    def request(self, command: str, callback: Completion) -> bool:
        if not is_valid_command(command):
            callback(False, f"unsupported command: {command}")
            return False
        with self._lock:
            if len(self.queue) >= MAX_QUEUED:
                callback(False, "too many actuator commands are queued")
                return False
            self.queue.append(PendingCommand(command, callback))
            return True

    def tick(self, serial_client: object, now: float | None = None) -> None:
        with self._lock:
            current = time.monotonic() if now is None else now
            if self.pending is None:
                if not self.queue:
                    return
                self.pending = self.queue.popleft()
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

    def handle_error(self, line: str) -> bool:
        """The Arduino rejected the command that is waiting for an ACK."""
        with self._lock:
            if self.pending is None or self.pending.sent_at is None:
                return False
            self._finish(False, line)
            return True

    def _finish(self, success: bool, message: str) -> None:
        pending = self.pending
        self.pending = None
        if pending:
            pending.callback(success, message)

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None  # type: ignore


class SerialClient:
    def __init__(self, port: str = "", baud_rate: int = 9600, timeout: float = 0.25) -> None:
        self.configured_port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.connection: Any = None

    @property
    def connected(self) -> bool:
        return bool(self.connection and self.connection.is_open)

    def find_port(self) -> str | None:
        if self.configured_port.strip():
            return self.configured_port.strip()
        if serial is None:
            return None
        for port in serial.tools.list_ports.comports():
            if port.device.startswith("COM") or "ttyACM" in port.device or "ttyUSB" in port.device:
                return port.device
        return None

    def connect(self) -> bool:
        if self.connected:
            return True
        port = self.find_port()
        if serial is None or not port:
            return False
        try:
            self.connection = serial.Serial(port, self.baud_rate, timeout=self.timeout)
            logger.info("Serial connected on %s at %s baud", port, self.baud_rate)
            return True
        except Exception as error:
            logger.warning("Serial connection failed: %s", error)
            self.connection = None
            return False

    def read_line(self) -> str | None:
        if not self.connect():
            return None
        try:
            raw = self.connection.readline()
            return raw.decode("utf-8", errors="replace").strip() if raw else None
        except Exception as error:
            logger.warning("Serial read failed: %s", error)
            self.close()
            return None

    def send_command(self, command: str) -> bool:
        if not self.connect():
            return False
        try:
            self.connection.write(f"{command}\n".encode("ascii"))
            self.connection.flush()
            logger.info("Serial command sent: %s", command)
            return True
        except Exception as error:
            logger.warning("Serial write failed: %s", error)
            self.close()
            return False

    def close(self) -> None:
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None


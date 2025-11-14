"""
Serial communication helper for the IMU Auto Mode tool.

Handles opening/closing the serial connection, sending command
frames, and reading responses from the Epson M-G552PR80 IMU.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import logging
from typing import List, Optional

try:
    from serial import Serial
except ImportError:  # pragma: no cover - optional dependency check
    Serial = None

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 3.0
DEFAULT_READ_CHUNK_SIZE = 4096


class SensorCommunication:
    """Low-level helper for IMU serial communication."""

    def __init__(self, port: str, baud: int, timeout: float = DEFAULT_TIMEOUT):
        if Serial is None:
            raise ImportError("pyserial is not installed. Install it with: pip install pyserial")

        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.connection: Optional[Serial] = None

    def open(self) -> None:
        logger.debug("Opening connection: %s @ %s baud", self.port, self.baud)
        self.connection = Serial(self.port, self.baud, timeout=self.timeout)

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Connection closed")

    def is_open(self) -> bool:
        return self.connection is not None and self.connection.is_open

    def send_command(self, command: List[int]) -> List[int]:
        if not self.is_open():
            raise RuntimeError("Connection not open")

        # All command frames: first byte is expected response length, rest is payload.
        self.connection.write(bytes(command[1:]))
        self.connection.flush()

        if command[0] <= 0:
            return []

        return list(self.read_bytes(command[0]))

    def read_bytes(self, length: int) -> bytes:
        if not self.is_open():
            raise RuntimeError("Connection not open")

        result = bytes()
        remaining = length
        while remaining > 0:
            to_read = min(remaining, DEFAULT_READ_CHUNK_SIZE)
            chunk = self.connection.read(to_read)
            if len(chunk) == 0:
                raise TimeoutError("Read timeout occurred")

            result += chunk[:remaining]
            remaining -= len(chunk)

        return result

    def send_commands(self, commands: List[List[int]]) -> List[int]:
        buffer: List[int] = []
        for command in commands:
            logger.debug("Sending command: %s", command)
            buffer.extend(self.send_command(command))
        return buffer

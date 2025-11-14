"""
Sensor communication module.

This module handles low-level serial communication with the sensor.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import logging
import time
from typing import List, Optional

try:
    from serial import Serial
except ImportError:
    Serial = None

logger = logging.getLogger(__name__)

# Constants
FLASH_BACKUP_TIMEOUT = 5.0
BACKUP_POLL_INTERVAL = 0.1
DEFAULT_TIMEOUT = 3.0
DEFAULT_READ_CHUNK_SIZE = 4096


class SensorCommunication:
    """Low-level serial communication with sensor."""

    def __init__(self, port: str, baud: int, timeout: float = DEFAULT_TIMEOUT):
        """Initialize communication.
        
        Args:
            port: Serial port path
            baud: Baud rate
            timeout: Communication timeout in seconds
        """
        if Serial is None:
            raise ImportError("pyserial is not installed. Install it with: pip install pyserial")
        
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.connection: Optional[Serial] = None

    def open(self) -> None:
        """Open serial connection to the sensor."""
        logger.debug(f"Opening connection: {self.port} at {self.baud} baud")
        self.connection = Serial(self.port, self.baud, timeout=self.timeout)

    def close(self) -> None:
        """Close serial connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Connection closed")

    def is_open(self) -> bool:
        """Check if connection is open.
        
        Returns:
            bool: True if open, False otherwise
        """
        return self.connection is not None and self.connection.is_open

    def send_command(self, command: List[int]) -> List[int]:
        """Send a command and read response.
        
        Args:
            command: Command bytes [length, byte1, byte2, ..., 0x0D]
            
        Returns:
            Response bytes as list of integers
            
        Raises:
            RuntimeError: If connection is not open
        """
        if not self.is_open():
            raise RuntimeError("Connection not open")
        
        # Send command (skip first byte which is expected response length)
        self.connection.write(bytes(command[1:]))
        self.connection.flush()
        
        # Read response if expected
        result = []
        if command[0] > 0:
            result = list(self.read_bytes(command[0]))
        
        return result

    def read_bytes(self, length: int) -> bytes:
        """Read specified number of bytes from serial port.
        
        Args:
            length: Number of bytes to read
            
        Returns:
            Bytes read from serial port
            
        Raises:
            RuntimeError: If connection is not open
            TimeoutError: If read times out
        """
        if not self.is_open():
            raise RuntimeError("Connection not open")
        
        result = bytes()
        while length > 0:
            read_length = min(length, DEFAULT_READ_CHUNK_SIZE)
            if read_length > 0:
                received = self.connection.read(read_length)
                read_length = len(received)
                
                if read_length == 0:
                    raise TimeoutError("Read timeout occurred")
                
                result += received[0:length]
                length -= read_length
        
        return result

    def send_commands(self, commands: List[List[int]]) -> List[int]:
        """Send multiple commands sequentially.
        
        Args:
            commands: List of command byte lists
            
        Returns:
            Combined response bytes
        """
        result = []
        for command in commands:
            logger.debug(f"Sending command: {command}")
            response = self.send_command(command)
            result.extend(response)
        return result


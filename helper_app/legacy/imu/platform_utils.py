"""
Platform-specific utilities for the IMU Auto Mode tool.

This module provides OS detection and serial port helper utilities
for Linux, Windows, macOS, and other operating systems.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import platform
import sys
from typing import List

try:
    import serial.tools.list_ports
except ImportError:  # pragma: no cover - optional dependency check
    serial = None


class PlatformUtils:
    """Platform-specific utility functions for serial enumeration."""

    @staticmethod
    def get_os() -> str:
        """Return the current operating system identifier."""
        return platform.system()

    @staticmethod
    def is_linux() -> bool:
        """Return True if running on Linux."""
        return PlatformUtils.get_os() == "Linux"

    @staticmethod
    def is_windows() -> bool:
        """Return True if running on Windows."""
        return PlatformUtils.get_os() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        """Return True if running on macOS."""
        return PlatformUtils.get_os() == "Darwin"

    @staticmethod
    def get_default_port_prefix() -> str:
        """Return an OS-specific default serial port prefix."""
        if PlatformUtils.is_windows():
            return "COM"
        if PlatformUtils.is_linux():
            return "/dev/ttyUSB"
        if PlatformUtils.is_macos():
            return "/dev/tty.usbserial"
        return "/dev/ttyUSB"

    @staticmethod
    def list_serial_ports() -> List[str]:
        """Return a sorted list of available serial port device names."""
        if serial is None:
            return []

        ports: List[str] = []
        try:
            for port_info in serial.tools.list_ports.comports():
                port_name = port_info.device

                if PlatformUtils.is_linux():
                    if port_name.startswith("/dev/ttyAMA"):
                        continue
                    if port_name.startswith("/dev/ttyUSB") or port_name.startswith("/dev/ttyACM"):
                        ports.append(port_name)
                elif PlatformUtils.is_windows():
                    if port_name.upper().startswith("COM"):
                        ports.append(port_name)
                elif PlatformUtils.is_macos():
                    if port_name.startswith("/dev/tty.usbserial") or port_name.startswith("/dev/tty.usbmodem"):
                        ports.append(port_name)
                else:
                    ports.append(port_name)
        except Exception:
            pass

        return sorted(ports)

    @staticmethod
    def validate_port(port: str) -> bool:
        """Return True if ``port`` looks valid for the running OS."""
        if not port:
            return False

        if PlatformUtils.is_windows():
            return port.upper().startswith("COM") and port[3:].isdigit()
        if PlatformUtils.is_linux():
            return port.startswith("/dev/tty") or port.startswith("/dev/ttyACM")
        if PlatformUtils.is_macos():
            return port.startswith("/dev/tty.")
        return True

    @staticmethod
    def get_port_permission_help() -> str:
        """Return guidance for resolving permission issues."""
        if PlatformUtils.is_linux():
            return (
                "Permission denied error. To fix:\n"
                "  sudo usermod -a -G dialout $USER\n"
                "  Then log out and log back in\n"
                "Or run with sudo (not recommended):\n"
                "  sudo python configure_imu_auto_start.py <port>"
            )
        if PlatformUtils.is_macos():
            return (
                "Permission denied error. You may need to:\n"
                "  1. Add your user to the dialout group\n"
                "  2. Or run with sudo (not recommended)"
            )
        return "Permission denied. Check if you have access to the serial port."

    @staticmethod
    def format_port_examples() -> str:
        """Return example port names for the current OS."""
        if PlatformUtils.is_windows():
            return "COM1, COM2, COM3, etc."
        if PlatformUtils.is_linux():
            return "/dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0, etc."
        if PlatformUtils.is_macos():
            return "/dev/tty.usbserial-*, /dev/tty.usbmodem-*, etc."
        return "/dev/ttyUSB0, COM1, etc."

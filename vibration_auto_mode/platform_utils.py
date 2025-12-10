"""
Platform-specific utilities for cross-platform compatibility.

This module provides OS detection and platform-specific utilities
for Linux, Windows, macOS, and other operating systems.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import platform
import sys
from typing import List, Optional

try:
    import serial.tools.list_ports
except ImportError:
    serial = None


class PlatformUtils:
    """Platform-specific utility functions."""

    @staticmethod
    def get_os() -> str:
        """Get the operating system name.
        
        Returns:
            str: OS name ('Linux', 'Windows', 'Darwin' for macOS, etc.)
        """
        return platform.system()

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux.
        
        Returns:
            bool: True if Linux, False otherwise
        """
        return PlatformUtils.get_os() == "Linux"

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows.
        
        Returns:
            bool: True if Windows, False otherwise
        """
        return PlatformUtils.get_os() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS.
        
        Returns:
            bool: True if macOS, False otherwise
        """
        return PlatformUtils.get_os() == "Darwin"

    @staticmethod
    def get_default_port_prefix() -> str:
        """Get the default serial port prefix for the current OS.
        
        Returns:
            str: Port prefix ('/dev/ttyUSB' for Linux, 'COM' for Windows, '/dev/tty.usbserial' for macOS)
        """
        if PlatformUtils.is_windows():
            return "COM"
        elif PlatformUtils.is_linux():
            return "/dev/ttyUSB"
        elif PlatformUtils.is_macos():
            return "/dev/tty.usbserial"
        else:
            return "/dev/ttyUSB"  # Default to Linux-style

    @staticmethod
    def list_serial_ports() -> List[str]:
        """List all available serial ports.
        
        Returns:
            List[str]: List of available serial port names
        """
        if serial is None:
            return []
        
        ports = []
        try:
            for port_info in serial.tools.list_ports.comports():
                port_name = port_info.device
                
                # Filter out unwanted ports based on OS
                if PlatformUtils.is_linux():
                    # Skip GPIO ports on Raspberry Pi
                    if port_name.startswith("/dev/ttyAMA"):
                        continue
                    # Include USB serial ports
                    if port_name.startswith("/dev/ttyUSB") or port_name.startswith("/dev/ttyACM"):
                        ports.append(port_name)
                elif PlatformUtils.is_windows():
                    # Include all COM ports
                    if port_name.startswith("COM"):
                        ports.append(port_name)
                elif PlatformUtils.is_macos():
                    # Include USB serial ports
                    if port_name.startswith("/dev/tty.usbserial") or port_name.startswith("/dev/tty.usbmodem"):
                        ports.append(port_name)
                else:
                    # Include all ports for unknown OS
                    ports.append(port_name)
        except Exception:
            pass
        
        return sorted(ports)

    @staticmethod
    def validate_port(port: str) -> bool:
        """Validate if a port name is valid for the current OS.
        
        Args:
            port: Port name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not port:
            return False
        
        if PlatformUtils.is_windows():
            return port.upper().startswith("COM") and port[3:].isdigit()
        elif PlatformUtils.is_linux():
            return port.startswith("/dev/tty") or port.startswith("/dev/ttyACM")
        elif PlatformUtils.is_macos():
            return port.startswith("/dev/tty.")
        else:
            # Accept any port for unknown OS
            return True

    @staticmethod
    def get_port_permission_help() -> str:
        """Get help text for port permission issues.
        
        Returns:
            str: Help text for fixing port permissions
        """
        if PlatformUtils.is_linux():
            return (
                "Permission denied error. To fix:\n"
                "  sudo usermod -a -G dialout $USER\n"
                "  Then log out and log back in\n"
                "Or run with sudo (not recommended):\n"
                "  sudo python configure_auto_start.py <port>"
            )
        elif PlatformUtils.is_macos():
            return (
                "Permission denied error. You may need to:\n"
                "  1. Add your user to the dialout group\n"
                "  2. Or run with sudo (not recommended)"
            )
        else:
            return "Permission denied. Check if you have access to the serial port."

    @staticmethod
    def format_port_examples() -> str:
        """Get port name examples for the current OS.
        
        Returns:
            str: Examples of valid port names
        """
        if PlatformUtils.is_windows():
            return "COM1, COM2, COM3, etc."
        elif PlatformUtils.is_linux():
            return "/dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0, etc."
        elif PlatformUtils.is_macos():
            return "/dev/tty.usbserial-*, /dev/tty.usbmodem-*, etc."
        else:
            return "/dev/ttyUSB0, COM1, etc."


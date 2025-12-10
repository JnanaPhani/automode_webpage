#!/usr/bin/env python3
"""
Accelerometer Auto Start Configuration Tool

A cross-platform tool to configure M-A552AR1 accelerometer sensors to automatically
start transmitting sampling data after power-on or reset by enabling UART Auto Start mode.

This tool works on Linux, Windows, macOS, and other operating systems.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)

Usage:
    python configure_accelerometer_auto_start.py <port> <sps_rate> [baud_rate]
    python configure_accelerometer_auto_start.py <port> --exit-auto
    python configure_accelerometer_auto_start.py --list-ports
    python configure_accelerometer_auto_start.py --help
    
Examples:
    # Linux - Configure for 200 Sps (default factory setting)
    python configure_accelerometer_auto_start.py /dev/ttyUSB0 200
    
    # Configure for 1000 Sps
    python configure_accelerometer_auto_start.py /dev/ttyUSB0 1000
    
    # Windows
    python configure_accelerometer_auto_start.py COM3 500
    
    # macOS
    python configure_accelerometer_auto_start.py /dev/tty.usbserial-1410 100
    
    # Exit auto mode (temporary)
    python configure_accelerometer_auto_start.py /dev/ttyUSB0 --exit-auto
    
    # Exit auto mode (permanent)
    python configure_accelerometer_auto_start.py /dev/ttyUSB0 --exit-auto --persist-disable-auto
    
    # List available ports
    python configure_accelerometer_auto_start.py --list-ports
"""

import argparse
import logging
import sys
from typing import Optional

# Import local modules
try:
    from platform_utils import PlatformUtils
    from sensor_comm import SensorCommunication
    from accelerometer_sensor_config import AccelerometerConfigurator
except ImportError:
    # Try importing from current directory
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    try:
        from platform_utils import PlatformUtils
        from sensor_comm import SensorCommunication
        from accelerometer_sensor_config import AccelerometerConfigurator
    except ImportError as e:
        print(f"Error: Failed to import required modules: {e}")
        print("Make sure all files are in the same directory:")
        print("  - configure_accelerometer_auto_start.py")
        print("  - platform_utils.py")
        print("  - sensor_comm.py")
        print("  - accelerometer_sensor_config.py")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s |%(asctime)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Author and Organization information
AUTHOR = "Jnana Phani A (https://phani.zenithtek.in)"
ORGANIZATION = "Zenith Tek (https://zenithtek.in)"

# Constants
DEFAULT_BAUD_RATE = 230400  # Default baud rate for accelerometer
SUPPORTED_BAUD_RATES = [115200, 230400, 460800]
SUPPORTED_SPS_RATES = [50, 100, 200, 500, 1000]


def list_available_ports() -> None:
    """List all available serial ports."""
    print(f"\nDetected OS: {PlatformUtils.get_os()}")
    print(f"Port prefix: {PlatformUtils.get_default_port_prefix()}")
    print("\nAvailable serial ports:")
    
    ports = PlatformUtils.list_serial_ports()
    if ports:
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port}")
        print(f"\nTotal: {len(ports)} port(s) found")
    else:
        print("  No serial ports found")
        print("\nTroubleshooting:")
        print("  - Ensure the device is connected")
        print("  - Check USB/Serial drivers are installed")
        print("  - On Linux, check permissions: sudo usermod -aG dialout $USER")


def validate_baud_rate(baud: int) -> bool:
    """Validate baud rate.
    
    Args:
        baud: Baud rate to validate
        
    Returns:
        True if valid (or close enough), False otherwise
    """
    # Allow some tolerance for common baud rates
    return baud in SUPPORTED_BAUD_RATES


def validate_sps_rate(sps: int) -> bool:
    """Validate SPS rate.
    
    Args:
        sps: Samples per second to validate
        
    Returns:
        True if valid, False otherwise
    """
    return sps in SUPPORTED_SPS_RATES


def configure_accelerometer(port: str, sps_rate: int, baud: int = DEFAULT_BAUD_RATE) -> bool:
    """Configure accelerometer in auto-start mode.
    
    Args:
        port: Serial port path
        sps_rate: Samples per second (50, 100, 200, 500, or 1000)
        baud: Baud rate (default: 230400)
        
    Returns:
        True if successful, False otherwise
    """
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Accelerometer Auto Start Configuration Tool")
        logger.info("Author: %s", AUTHOR)
        logger.info("Organization: %s", ORGANIZATION)
        logger.info("=" * 64)
        
        if not PlatformUtils.validate_port(port):
            logger.error("Invalid port: %s", port)
            logger.error("Examples: %s", PlatformUtils.format_port_examples())
            return False
        
        if not validate_baud_rate(baud):
            logger.warning("Baud %s not in recommended list %s", baud, SUPPORTED_BAUD_RATES)
            logger.warning("Continuing using provided baud rate...")
        
        if not validate_sps_rate(sps_rate):
            logger.error("Invalid SPS rate: %s. Supported rates: %s", sps_rate, SUPPORTED_SPS_RATES)
            return False
        
        comm = SensorCommunication(port, baud)
        comm.open()
        
        configurator = AccelerometerConfigurator(comm)
        success = configurator.configure(sps_rate)
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return False
    except Exception as e:
        logger.error("Configuration failed: %s", e, exc_info=True)
        return False
    finally:
        if comm:
            comm.close()


def exit_auto_mode(port: str, baud: int = DEFAULT_BAUD_RATE, persist_disable_auto: bool = False) -> bool:
    """Exit auto mode and return to configuration mode.
    
    Args:
        port: Serial port path
        baud: Baud rate (default: 230400)
        persist_disable_auto: If True, permanently disable auto-start by saving to flash
        
    Returns:
        True if successful, False otherwise
    """
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Exit Auto Mode Tool")
        logger.info("Author: %s", AUTHOR)
        logger.info("Organization: %s", ORGANIZATION)
        logger.info("=" * 64)
        
        if not PlatformUtils.validate_port(port):
            logger.error("Invalid port: %s", port)
            logger.error("Examples: %s", PlatformUtils.format_port_examples())
            return False
        
        comm = SensorCommunication(port, baud)
        comm.open()
        
        configurator = AccelerometerConfigurator(comm)
        success = configurator.exit_auto_mode(persist_disable_auto=persist_disable_auto)
        
        if success and persist_disable_auto:
            logger.info("Auto-start has been permanently disabled")
            logger.info("After power cycle, sensor will remain in configuration mode")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return False
    except Exception as e:
        logger.error("Failed to exit auto mode: %s", e, exc_info=True)
        return False
    finally:
        if comm:
            comm.close()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configure M-A552AR1 accelerometer for auto-start mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Linux - Configure for 200 Sps (factory default)
  python configure_accelerometer_auto_start.py /dev/ttyUSB0 200
  
  # Configure for 1000 Sps
  python configure_accelerometer_auto_start.py /dev/ttyUSB0 1000
  
  # Windows
  python configure_accelerometer_auto_start.py COM3 500
  
  # macOS
  python configure_accelerometer_auto_start.py /dev/tty.usbserial-1410 100
  
  # Exit auto mode (temporary)
  python configure_accelerometer_auto_start.py /dev/ttyUSB0 --exit-auto
  
  # Exit auto mode (permanent)
  python configure_accelerometer_auto_start.py /dev/ttyUSB0 --exit-auto --persist-disable-auto
  
  # List available ports
  python configure_accelerometer_auto_start.py --list-ports

Supported SPS Rates: {', '.join(map(str, SUPPORTED_SPS_RATES))}
Supported Baud Rates: {', '.join(map(str, SUPPORTED_BAUD_RATES))}

Configuration (Fixed):
  - Filter: 512 taps (constant)
  - Cutoff frequency: Auto-selected based on SPS rate
  - Output mode: Acceleration (all axes)
  - Measurement mode: Standard noise floor
  - TEMP_STABIL: Enabled
  - Burst control: TEMP_OUT=1, ACC_XYZ_OUT=1
  - Baud rate: 230.4 kbps (can be changed with --baud)

Filter Cutoff Frequency Mapping:
  - 50 Sps:  16 Hz
  - 100 Sps: 16 Hz
  - 200 Sps: 60 Hz (factory default)
  - 500 Sps: 60 Hz
  - 1000 Sps: 210 Hz

Author: {AUTHOR}
Organization: {ORGANIZATION}
        """,
    )
    
    parser.add_argument(
        "port",
        nargs="?",
        help="Serial port path (e.g., /dev/ttyUSB0, COM3, /dev/tty.usbserial-1410)",
    )
    parser.add_argument(
        "sps_rate",
        nargs="?",
        type=int,
        help=f"Samples per second ({', '.join(map(str, SUPPORTED_SPS_RATES))})",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f"Baud rate (default: {DEFAULT_BAUD_RATE})",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List all available serial ports and exit",
    )
    parser.add_argument(
        "--exit-auto",
        action="store_true",
        help="Exit auto mode and return to configuration mode",
    )
    parser.add_argument(
        "--persist-disable-auto",
        action="store_true",
        help="After exiting Auto Mode, save the cleared UART_AUTO/AUTO_START bits via flash backup (permanent)",
    )
    
    args = parser.parse_args()
    
    if args.list_ports:
        list_available_ports()
        return 0
    
    if not args.port:
        parser.print_help()
        print("\nError: Port is required")
        print(f"Use --list-ports to see available ports")
        return 1
    
    if args.exit_auto:
        if not args.port:
            parser.print_help()
            print("\nError: Port is required when using --exit-auto")
            return 1
        # Exit auto mode
        success = exit_auto_mode(args.port, args.baud, persist_disable_auto=args.persist_disable_auto)
        return 0 if success else 1
    
    if not args.sps_rate:
        parser.print_help()
        print("\nError: SPS rate is required")
        print(f"Supported rates: {', '.join(map(str, SUPPORTED_SPS_RATES))}")
        return 1
    
    # Configure accelerometer
    success = configure_accelerometer(args.port, args.sps_rate, args.baud)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Sensor Auto Start Configuration Tool

A cross-platform tool to configure M-A542VR1 sensors (A342/A352) to automatically
start transmitting sampling data after power-on or reset by enabling UART Auto Start mode.

This tool works on Linux, Windows, macOS, and other operating systems.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)

Usage:
    python configure_auto_start.py <port> [baud_rate]
    python configure_auto_start.py --list-ports
    python configure_auto_start.py --help
    
Examples:
    # Linux
    python configure_auto_start.py /dev/ttyUSB0
    python configure_auto_start.py /dev/ttyUSB0 460800
    
    # Windows
    python configure_auto_start.py COM3
    python configure_auto_start.py COM3 460800
    
    # macOS
    python configure_auto_start.py /dev/tty.usbserial-1410
    python configure_auto_start.py /dev/tty.usbserial-1410 460800
    
    # List available ports
    python configure_auto_start.py --list-ports
"""

import argparse
import logging
import sys
from typing import Optional

# Import local modules
try:
    from platform_utils import PlatformUtils
    from sensor_comm import SensorCommunication
    from sensor_config import SensorConfigurator
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
        from sensor_config import SensorConfigurator
    except ImportError as e:
        print(f"Error: Failed to import required modules: {e}")
        print("Make sure all files are in the same directory:")
        print("  - configure_auto_start.py")
        print("  - platform_utils.py")
        print("  - sensor_comm.py")
        print("  - sensor_config.py")
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
DEFAULT_BAUD_RATE = 460800
SUPPORTED_BAUD_RATES = [230400, 460800, 921600]


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
        print("  - Make sure the sensor is connected")
        print("  - Check USB cable connection")
        print("  - Try unplugging and replugging the device")
        if PlatformUtils.is_linux():
            print("  - Check if device appears in: ls -la /dev/ttyUSB*")


def validate_baud_rate(baud: int) -> bool:
    """Validate baud rate.
    
    Args:
        baud: Baud rate to validate
        
    Returns:
        True if valid, False otherwise
    """
    return baud in SUPPORTED_BAUD_RATES


def configure_sensor(port: str, baud: int) -> bool:
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Vibration Sensor Auto Start Configuration Tool")
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

        comm = SensorCommunication(port, baud)
        logger.info("Connecting to %s at %d baud", port, baud)
        comm.open()

        configurator = SensorConfigurator(comm)
        success = configurator.configure()

        if success:
            logger.info("=" * 64)
            logger.info("Configuration succeeded!")
            logger.info("Developed by %s at %s", AUTHOR, ORGANIZATION)
            logger.info("=" * 64)
        return success

    except PermissionError as exc:
        logger.error("Permission denied: %s", exc)
        logger.error("\n" + PlatformUtils.get_port_permission_help())
        return False
    except FileNotFoundError as exc:
        logger.error("Port not found: %s", exc)
        logger.error("Use --list-ports to view available ports")
        return False
    except Exception as exc:
        logger.error("Configuration failed: %s", exc)
        return False
    finally:
        if comm:
            comm.close()


def detect_sensor_identity(port: str, baud: int) -> bool:
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Vibration Sensor Identity Detection")
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

        comm = SensorCommunication(port, baud)
        logger.info("Connecting to %s at %d baud", port, baud)
        comm.open()

        configurator = SensorConfigurator(comm)
        identity = configurator.detect_identity()
        if identity is None:
            logger.error("Failed to read sensor identity registers")
            return False

        product_id = identity.get("product_id", "").strip() or "(unknown)"
        serial_number = identity.get("serial_number", "").strip() or "(unknown)"
        product_words = identity.get("product_words", [])
        serial_words = identity.get("serial_words", [])

        print("\nDetected Sensor Identity:\n")
        print(f"  Product ID   : {product_id}")
        print(f"  Serial Number: {serial_number}\n")
        if product_words:
            print(
                "  Product words: "
                + " ".join(f"0x{word:04X}" for word in product_words)
            )
        if serial_words:
            print(
                "  Serial words : "
                + " ".join(f"0x{word:04X}" for word in serial_words)
            )
        print()
        return True

    except PermissionError as exc:
        logger.error("Permission denied: %s", exc)
        logger.error("\n" + PlatformUtils.get_port_permission_help())
        return False
    except FileNotFoundError as exc:
        logger.error("Port not found: %s", exc)
        logger.error("Use --list-ports to view available ports")
        return False
    except Exception as exc:
        logger.error("Sensor identity detection failed: %s", exc)
        return False
    finally:
        if comm:
            comm.close()


def exit_auto_mode_cli(port: str, baud: int, persist_disable_auto: bool) -> bool:
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Vibration Sensor Auto Mode Exit Utility")
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

        comm = SensorCommunication(port, baud)
        logger.info("Connecting to %s at %d baud", port, baud)
        comm.open()

        configurator = SensorConfigurator(comm)
        success = configurator.exit_auto_mode(persist_disable_auto=persist_disable_auto)

        if success:
            logger.info("=" * 64)
            logger.info("Auto mode disabled successfully")
            if persist_disable_auto:
                logger.info("UART auto bits persisted via flash backup")
            logger.info("=" * 64)
        return success

    except PermissionError as exc:
        logger.error("Permission denied: %s", exc)
        logger.error("\n" + PlatformUtils.get_port_permission_help())
        return False
    except FileNotFoundError as exc:
        logger.error("Port not found: %s", exc)
        logger.error("Use --list-ports to view available ports")
        return False
    except Exception as exc:
        logger.error("Exit auto mode failed: %s", exc)
        return False
    finally:
        if comm:
            comm.close()


def reset_sensor_cli(port: str, baud: int) -> bool:
    comm: Optional[SensorCommunication] = None
    try:
        logger.info("=" * 64)
        logger.info("Vibration Sensor Reset Utility")
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

        comm = SensorCommunication(port, baud)
        logger.info("Connecting to %s at %d baud", port, baud)
        comm.open()

        configurator = SensorConfigurator(comm)
        if configurator.full_reset():
            logger.info("Full reset complete. Auto mode bits cleared and persisted.")
            return True
        logger.error("Full reset failed")
        return False

    except PermissionError as exc:
        logger.error("Permission denied: %s", exc)
        logger.error("\n" + PlatformUtils.get_port_permission_help())
        return False
    except FileNotFoundError as exc:
        logger.error("Port not found: %s", exc)
        logger.error("Use --list-ports to view available ports")
        return False
    except Exception as exc:
        logger.error("Reset failed: %s", exc)
        return False
    finally:
        if comm:
            comm.close()


def main() -> int:
    """Main entry point for the configuration script."""
    parser = argparse.ArgumentParser(
        description="Configure M-A542VR1 sensors in UART Auto Start mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Linux
  python configure_auto_start.py /dev/ttyUSB0
  python configure_auto_start.py /dev/ttyUSB0 460800
  
  # Windows
  python configure_auto_start.py COM3
  python configure_auto_start.py COM3 460800
  
  # macOS
  python configure_auto_start.py /dev/tty.usbserial-1410
  
  # List available ports
  python configure_auto_start.py --list-ports
        """
    )
    
    parser.add_argument(
        "port",
        nargs="?",
        help="Serial port path (e.g., /dev/ttyUSB0, COM3, /dev/tty.usbserial-1410)"
    )
    parser.add_argument(
        "baud",
        nargs="?",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f"Baud rate (default: {DEFAULT_BAUD_RATE}, supported: {SUPPORTED_BAUD_RATES})"
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List all available serial ports"
    )
    parser.add_argument(
        "--baud-rate",
        type=int,
        dest="baud",
        help=f"Baud rate (default: {DEFAULT_BAUD_RATE})"
    )
    parser.add_argument(
        "--exit-auto",
        action="store_true",
        help="Stop streaming and return the sensor to configuration mode",
    )
    parser.add_argument(
        "--persist-disable-auto",
        action="store_true",
        help="After exiting Auto Mode, save the cleared UART_AUTO/AUTO_START bits via flash backup",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Read and print the Product ID and Serial Number from the connected sensor",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Send the full reset sequence (exit auto, flash test, software reset)",
    )
    
    args = parser.parse_args()
    
    if args.list_ports:
        list_available_ports()
        return 0

    if args.exit_auto:
        if not args.port:
            parser.print_help()
            print("\nError: port argument is required when using --exit-auto.")
            return 1
        return (
            0
            if exit_auto_mode_cli(args.port, args.baud, args.persist_disable_auto)
            else 1
        )

    if args.detect:
        if not args.port:
            parser.print_help()
            print("\nError: port argument is required when using --detect.")
            return 1
        return 0 if detect_sensor_identity(args.port, args.baud) else 1

    if args.reset:
        if not args.port:
            parser.print_help()
            print("\nError: port argument is required when using --reset.")
            return 1
        return 0 if reset_sensor_cli(args.port, args.baud) else 1

    if not args.port:
        parser.print_help()
        print("\nError: Port is required")
        print(f"Use --list-ports to see available ports")
        return 1
    
    # Configure sensor
    success = configure_sensor(args.port, args.baud)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

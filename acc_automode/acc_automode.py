#!/usr/bin/env python3
"""
Accelerometer Auto Mode Configuration Script

This script configures the M-A552AR1 accelerometer sensor to automatically
start transmitting sampling data after power-on or reset, following the
sample program flow from datasheet section 8.1.11.

The configuration uses fixed values (no user configuration required):
- Output rate: 200 Sps (factory default)
- Filter: TAP=512, fc=60 Hz
- UART Auto sampling: Enabled
- Auto Start: Enabled
- Burst output: TEMP, ACC_XYZ, COUNT enabled

After configuration, the sensor will automatically enter sampling mode
after power-on or reset.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add parent directory to path to import sensor communication modules
sys.path.insert(0, str(Path(__file__).parent.parent / "Accelerometer_Auto_Mode"))

try:
    from sensor_comm import SensorCommunication
    from platform_utils import PlatformUtils
except ImportError as e:
    print(f"Error: Failed to import required modules: {e}")
    print("Make sure the Accelerometer_Auto_Mode directory exists with:")
    print("  - sensor_comm.py")
    print("  - platform_utils.py")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants from datasheet section 8.1.11
DEFAULT_BAUD_RATE = 230400
FLASH_BACKUP_TIMEOUT = 5.0
BACKUP_POLL_INTERVAL = 0.1

# Fixed configuration values from section 8.1.11
# These values are hardcoded - no user configuration needed
SMPL_CTRL_H = 0x04  # 200 Sps
# FILTER_CTRL_L = 0x08  # TAP=512, fc=60 Hz
FILTER_CTRL_L = 0x07  # TAP=512, fc=16 Hz
UART_CTRL_L = 0x03  # UART Auto sampling=1, Auto start=1
BURST_CTRL_L = 0x02  # COUNT_OUT=1
BURST_CTRL_H = 0x47  # TEMP_OUT=1, ACCX_OUT=1, ACCY_OUT=1, ACCZ_OUT=1


def wait_for_ready(comm: SensorCommunication) -> bool:
    """Wait for sensor to be ready after power-on.
    
    Follows datasheet section 8.1.1 power-on sequence.
    
    Args:
        comm: Sensor communication object
        
    Returns:
        True if sensor is ready, False otherwise
    """
    logger.info("Waiting for sensor to be ready...")
    
    # Wait Power-On Start-Up Time (900ms from datasheet)
    time.sleep(1.0)
    
    # Wait until NOT_READY bit goes to 0
    # NOT_READY is GLOB_CMD[0x0A(W1)] bit[10]
    start_time = time.time()
    timeout = 5.0
    
    while time.time() - start_time < timeout:
        try:
            # Switch to Window 1
            comm.send_commands([[0, 0xFE, 0x01, 0x0D]])  # WINDOW_ID(L) write command (WINDOW=1)
            time.sleep(0.01)  # Small delay between commands
            
            # Read GLOB_CMD
            # Response format: [0x0A, MSByte, LSByte, 0x0D] = 4 bytes total
            result = comm.send_command([4, 0x0A, 0x00, 0x0D])  # GLOB_CMD read command (expect 4 bytes: addr, MSB, LSB, CR)
            
            if len(result) >= 4:
                # Response format: [0x0A, MSByte, LSByte, 0x0D]
                # result[0] = address (0x0A)
                # result[1] = MSByte
                # result[2] = LSByte
                # result[3] = delimiter (0x0D)
                glob_cmd_msb = result[1]
                # NOT_READY is bit[10] in MSByte (bit[2] of MSByte)
                not_ready = (glob_cmd_msb >> 2) & 0x01
                
                if not_ready == 0:
                    logger.info("Sensor is ready (NOT_READY=0)")
                    return True
            elif len(result) >= 3:
                # Try with 3 bytes (might not have delimiter)
                glob_cmd_msb = result[1]
                not_ready = (glob_cmd_msb >> 2) & 0x01
                if not_ready == 0:
                    logger.info("Sensor is ready (NOT_READY=0)")
                    return True
                    
            time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Error checking ready status: {e}")
            time.sleep(0.1)
    
    logger.warning("Timeout waiting for sensor to be ready")
    return False


def check_hardware_error(comm: SensorCommunication) -> bool:
    """Check for hardware errors.
    
    Follows datasheet section 8.1.1 step (d).
    
    Args:
        comm: Sensor communication object
        
    Returns:
        True if no hardware errors, False otherwise
    """
    logger.info("Checking for hardware errors...")
    
    try:
        # Switch to Window 0
        comm.send_commands([[0, 0xFE, 0x00, 0x0D]])  # WINDOW_ID(L) write command (WINDOW=0)
        time.sleep(0.01)  # Small delay between commands
        
        # Read DIAG_STAT
        # Response format: [0x04, MSByte, LSByte, 0x0D] = 4 bytes total
        result = comm.send_command([4, 0x04, 0x00, 0x0D])  # DIAG_STAT read command (expect 4 bytes: addr, MSB, LSB, CR)
        
        if len(result) >= 4:
            # Response format: [0x04, MSByte, LSByte, 0x0D]
            # result[0] = address (0x04)
            # result[1] = MSByte
            # result[2] = LSByte
            # result[3] = delimiter (0x0D)
            if result[0] != 0x04:
                logger.warning(f"Unexpected address byte: 0x{result[0]:02X} (expected 0x04)")
            diag_stat_msb = result[1]
            # HARD_ERR is bit[7:5] in MSByte (bits 7, 6, 5)
            hard_err = (diag_stat_msb >> 5) & 0x07
            
            if hard_err == 0:
                logger.info("No hardware errors detected (HARD_ERR=000)")
                return True
            else:
                logger.error(f"Hardware error detected: HARD_ERR={hard_err:03b}")
                return False
        elif len(result) >= 3:
            # Try with 3 bytes (might not have delimiter)
            logger.debug(f"Got 3-byte response: {[hex(b) for b in result]}")
            diag_stat_msb = result[1] if result[0] == 0x04 else result[0]
            hard_err = (diag_stat_msb >> 5) & 0x07
            if hard_err == 0:
                logger.info("No hardware errors detected (HARD_ERR=000)")
                return True
            else:
                logger.error(f"Hardware error detected: HARD_ERR={hard_err:03b}")
                return False
        elif len(result) > 0:
            logger.warning(f"Unexpected response length: {len(result)} bytes")
            logger.warning(f"Response bytes: {[hex(b) for b in result]}")
            return False
        else:
            logger.warning(f"Could not read DIAG_STAT register (got {len(result)} bytes, expected 4)")
            logger.debug(f"Response bytes: {[hex(b) for b in result] if result else 'empty'}")
            return False
    except Exception as e:
        logger.error(f"Error checking hardware status: {e}")
        return False


def set_registers(comm: SensorCommunication) -> bool:
    """Set all registers according to section 8.1.11 step (a).
    
    Args:
        comm: Sensor communication object
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting registers for auto mode...")
    
    try:
        commands = [
            # Switch to Window 1
            [0, 0xFE, 0x01, 0x0D],  # WINDOW_ID(L) write command (WINDOW=1)
            
            # Set SMPL_CTRL(H) = 0x04 (200 Sps)
            [0, 0x85, SMPL_CTRL_H, 0x0D],  # SMPL_CTRL(H) write command
            
            # Set FILTER_CTRL(L) = 0x08 (TAP=512, fc=60)
            [0, 0x86, FILTER_CTRL_L, 0x0D],  # FILTER_CTRL(L) write command
            
            # Set UART_CTRL(L) = 0x03 (UART Auto sampling, Auto start=on)
            [0, 0x88, UART_CTRL_L, 0x0D],  # UART_CTRL(L) write command
            
            # Set BURST_CTRL(L) = 0x02 (COUNT=on)
            [0, 0x8C, BURST_CTRL_L, 0x0D],  # BURST_CTRL(L) write command
            
            # Set BURST_CTRL(H) = 0x47 (TEMP=on, ACC_XYZ=on)
            [0, 0x8D, BURST_CTRL_H, 0x0D],  # BURST_CTRL(H) write command
        ]
        
        comm.send_commands(commands)
        logger.info("All registers set successfully")
        logger.info("  - Output rate: 200 Sps")
        logger.info("  - Filter: TAP=512, fc=60 Hz")
        logger.info("  - UART Auto sampling: Enabled")
        logger.info("  - Auto Start: Enabled")
        logger.info("  - Burst output: TEMP, ACC_XYZ, COUNT enabled")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set registers: {e}")
        return False


def wait_for_filter_setting(comm: SensorCommunication) -> bool:
    """Wait for filter setting to complete.
    
    Args:
        comm: Sensor communication object
        
    Returns:
        True if filter setting completed, False otherwise
    """
    logger.info("Waiting for filter setting to complete...")
    
    start_time = time.time()
    timeout = 5.0
    
    while time.time() - start_time < timeout:
        try:
            # Switch to Window 1
            comm.send_commands([[0, 0xFE, 0x01, 0x0D]])  # Switch to Window 1
            time.sleep(0.01)  # Small delay between commands
            
            # Read FILTER_CTRL register
            # Response format: [0x06, MSByte, LSByte, 0x0D] = 4 bytes total
            result = comm.send_command([4, 0x06, 0x00, 0x0D])  # Read FILTER_CTRL register (expect 4 bytes: addr, MSB, LSB, CR)
            
            if len(result) >= 4:
                # Response format: [0x06, MSByte, LSByte, 0x0D]
                # result[0] = address (0x06)
                # result[1] = MSByte
                # result[2] = LSByte
                # result[3] = delimiter (0x0D)
                filter_ctrl_lsb = result[2]
                # FILTER_STAT is bit[5] in low byte
                filter_stat = (filter_ctrl_lsb >> 5) & 0x01
                
                if filter_stat == 0:
                    logger.info("Filter setting completed")
                    return True
            elif len(result) >= 3:
                # Try with 3 bytes (might not have delimiter)
                filter_ctrl_lsb = result[2]
                filter_stat = (filter_ctrl_lsb >> 5) & 0x01
                if filter_stat == 0:
                    logger.info("Filter setting completed")
                    return True
                    
            time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Error checking filter status: {e}")
            time.sleep(0.1)
    
    logger.warning("Timeout waiting for filter setting")
    return False


def flash_backup(comm: SensorCommunication) -> bool:
    """Execute flash backup to save settings to non-volatile memory.
    
    Follows datasheet section 8.1.7 procedure.
    
    Args:
        comm: Sensor communication object
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Executing flash backup...")
    
    try:
        # Step (a): Send flash backup command
        # GLOB_CMD register is at 0x0A-0x0B (Window 1)
        # FLASH_BACKUP is bit [3] of LOW byte
        # Write 0x08 to GLOB_CMD(L) at address 0x8A
        comm.send_commands([
            [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
            [0, 0x8A, 0x08, 0x0D],  # Set FLASH_BACKUP bit [3] in GLOB_CMD(L)
        ])
        
        # Step (b): Wait until flash backup has finished
        logger.info("Waiting for flash backup to complete...")
        start_time = time.time()
        flash_backup_cleared = False
        
        while time.time() - start_time < FLASH_BACKUP_TIMEOUT:
            # Switch to Window 1
            comm.send_commands([[0, 0xFE, 0x01, 0x0D]])  # Switch to Window 1
            time.sleep(0.01)  # Small delay between commands
            
            # Read GLOB_CMD register
            # Response format: [0x0A, MSByte, LSByte, 0x0D] = 4 bytes total
            result = comm.send_command([4, 0x0A, 0x00, 0x0D])  # Read GLOB_CMD register (expect 4 bytes: addr, MSB, LSB, CR)
            
            if len(result) >= 4:
                # Response format: [0x0A, MSByte, LSByte, 0x0D]
                # result[0] = address (0x0A)
                # result[1] = MSByte
                # result[2] = LSByte
                # result[3] = delimiter (0x0D)
                glob_cmd_low = result[2]
                # FLASH_BACKUP is bit[3] in low byte
                flash_backup_bit = (glob_cmd_low >> 3) & 0x01
                
                if flash_backup_bit == 0:
                    flash_backup_cleared = True
                    logger.info("Flash backup completed")
                    break
            elif len(result) >= 3:
                # Try with 3 bytes (might not have delimiter)
                glob_cmd_low = result[2]
                flash_backup_bit = (glob_cmd_low >> 3) & 0x01
                if flash_backup_bit == 0:
                    flash_backup_cleared = True
                    logger.info("Flash backup completed")
                    break
                    
            time.sleep(BACKUP_POLL_INTERVAL)
        
        if not flash_backup_cleared:
            logger.error("Flash backup timeout")
            return False
        
        # Step (c): Confirm the result by checking FLASH_BU_ERR
        time.sleep(0.1)
        
        # Switch to Window 0
        comm.send_commands([[0, 0xFE, 0x00, 0x0D]])  # Switch to Window 0
        time.sleep(0.01)  # Small delay between commands
        
        # Read DIAG_STAT register
        # Response format: [0x04, MSByte, LSByte, 0x0D] = 4 bytes total
        result = comm.send_command([4, 0x04, 0x00, 0x0D])  # Read DIAG_STAT register (expect 4 bytes: addr, MSB, LSB, CR)
        
        if len(result) >= 4:
            # Response format: [0x04, MSByte, LSByte, 0x0D]
            # result[0] = address (0x04)
            # result[1] = MSByte
            # result[2] = LSByte (FLASH_BU_ERR is bit[0] in LSByte)
            # result[3] = delimiter (0x0D)
            flash_bu_err = result[2] & 0x01  # Bit [0] is FLASH_BU_ERR
            if flash_bu_err == 0:
                logger.info("Flash backup verified successfully (FLASH_BU_ERR=0)")
                return True
            else:
                logger.error("Flash backup failed: FLASH_BU_ERR=1")
                return False
        elif len(result) >= 3:
            # Try with 3 bytes (might not have delimiter)
            flash_bu_err = result[2] & 0x01
            if flash_bu_err == 0:
                logger.info("Flash backup verified successfully (FLASH_BU_ERR=0)")
                return True
            else:
                logger.error("Flash backup failed: FLASH_BU_ERR=1")
                return False
        else:
            logger.error(f"Failed to read DIAG_STAT register (got {len(result)} bytes, expected 4)")
            logger.debug(f"Response bytes: {[hex(b) for b in result]}")
            return False
            
    except Exception as e:
        logger.error(f"Flash backup failed: {e}")
        return False


def configure_auto_mode(port: str, baud: int = DEFAULT_BAUD_RATE) -> bool:
    """Configure accelerometer in auto mode following section 8.1.11.
    
    Args:
        port: Serial port path
        baud: Baud rate (default: 230400)
        
    Returns:
        True if successful, False otherwise
    """
    comm: Optional[SensorCommunication] = None
    
    try:
        logger.info("=" * 64)
        logger.info("Accelerometer Auto Mode Configuration")
        logger.info("Following datasheet section 8.1.11")
        logger.info("=" * 64)
        logger.info(f"Port: {port}")
        logger.info(f"Baud rate: {baud}")
        logger.info("")
        
        # Validate port
        if not PlatformUtils.validate_port(port):
            logger.error(f"Invalid port: {port}")
            logger.error(f"Examples: {PlatformUtils.format_port_examples()}")
            return False
        
        # Open connection
        logger.info("Opening serial connection...")
        comm = SensorCommunication(port, baud)
        comm.open()
        
        # Step 1: Power-on sequence (section 8.1.1)
        # Note: If sensor is already in auto mode, register reads may not work
        # So we make these checks lenient
        if not wait_for_ready(comm):
            logger.warning("Sensor may not be ready, continuing anyway...")
            logger.warning("This is normal if sensor is already in auto mode")
        
        hardware_check = check_hardware_error(comm)
        if not hardware_check:
            logger.warning("Could not verify hardware status (sensor may be in auto mode)")
            logger.warning("Continuing with configuration anyway...")
            # Don't abort - sensor might be in auto mode where register reads don't work
        
        # Step 2: Set registers (section 8.1.11 step a)
        if not set_registers(comm):
            logger.error("Failed to set registers")
            return False
        
        # Wait for filter setting to complete
        if not wait_for_filter_setting(comm):
            logger.warning("Filter setting may not have completed")
        
        # Step 3: Execute flash backup (section 8.1.11 step b)
        if not flash_backup(comm):
            logger.error("Flash backup failed")
            return False
        
        logger.info("")
        logger.info("=" * 64)
        logger.info("Configuration completed successfully!")
        logger.info("=" * 64)
        logger.info("")
        logger.info("The sensor is now configured for auto mode.")
        logger.info("After power-off and power-on (or reset), the sensor will")
        logger.info("automatically enter sampling mode and start transmitting data.")
        logger.info("")
        logger.info("Configuration summary:")
        logger.info("  - Output rate: 200 Sps")
        logger.info("  - Filter: TAP=512, fc=60 Hz")
        logger.info("  - UART Auto sampling: Enabled")
        logger.info("  - Auto Start: Enabled")
        logger.info("  - Burst output: TEMP, ACC_XYZ, COUNT enabled")
        logger.info("")
        
        return True
        
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return False
    except Exception as e:
        logger.error(f"Configuration failed: {e}", exc_info=True)
        return False
    finally:
        if comm:
            comm.close()


def main() -> int:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Configure M-A552AR1 accelerometer for auto mode (section 8.1.11)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Linux
  python acc_automode.py /dev/ttyUSB0
  
  # Windows
  python acc_automode.py COM3
  
  # macOS
  python acc_automode.py /dev/tty.usbserial-1410
  
  # List available ports
  python acc_automode.py --list-ports

This script uses fixed configuration values (no user input required):
  - Output rate: 200 Sps (factory default)
  - Filter: TAP=512, fc=60 Hz
  - UART Auto sampling: Enabled
  - Auto Start: Enabled
  - Burst output: TEMP, ACC_XYZ, COUNT enabled

After configuration, the sensor will automatically enter sampling mode
after power-on or reset.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
        """,
    )
    
    parser.add_argument(
        "port",
        nargs="?",
        help="Serial port path (e.g., /dev/ttyUSB0, COM3, /dev/tty.usbserial-1410)",
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
    
    args = parser.parse_args()
    
    if args.list_ports:
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
        return 0
    
    if not args.port:
        parser.print_help()
        print("\nError: Port is required")
        print("Use --list-ports to see available ports")
        return 1
    
    success = configure_auto_mode(args.port, args.baud)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())


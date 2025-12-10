"""
Accelerometer sensor configuration module.

This module handles accelerometer (M-A552AR1) configuration operations including
UART Auto Start mode setup and flash backup.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import logging
import sys
import time
from typing import Dict, List, Optional

# Import sensor communication module
try:
    from sensor_comm import SensorCommunication
except ImportError:
    # Try relative import if in package
    try:
        from .sensor_comm import SensorCommunication
    except ImportError:
        print("Error: Could not import sensor_comm module")
        sys.exit(1)

logger = logging.getLogger(__name__)

# Author and Organization information
AUTHOR = "Jnana Phani A (https://phani.zenithtek.in)"
ORGANIZATION = "Zenith Tek (https://zenithtek.in)"

# Constants
FLASH_BACKUP_TIMEOUT = 5.0
BACKUP_POLL_INTERVAL = 0.1

# SPS Rate to SMPL_CTRL_H mapping (high byte value to write to 0x85)
# Following acc_automode.py logic: direct high byte values
SPS_TO_SMPL_CTRL_H: Dict[int, int] = {
    100: 0x05,   # 100 Sps
    200: 0x04,   # 200 Sps (factory default)
    500: 0x03,   # 500 Sps
    1000: 0x02,  # 1000 Sps
}

# Filter cutoff frequency mapping for 512 taps
# Based on Table 5-3 from datasheet
# We use 16 Hz for all rates (compatible with all SPS rates)
FILTER_CUTOFF_512TAPS = {
    9: 0x0006,    # FIR Kaiser Filter TAP=512, fc=9 Hz
    16: 0x0007,   # FIR Kaiser Filter TAP=512, fc=16 Hz (works with all rates)
    60: 0x0008,   # FIR Kaiser Filter TAP=512, fc=60 Hz (factory default, works with 200/500/1000)
    210: 0x0009,  # FIR Kaiser Filter TAP=512, fc=210 Hz (works with 500/1000)
    460: 0x000A,  # FIR Kaiser Filter TAP=512, fc=460 Hz (works with 1000 only)
}

# SPS to recommended filter cutoff frequency
# Uses 16 Hz for all rates (safest option, compatible with all)
# Alternative: could use 60 Hz for 200/500/1000, but 16 Hz is safer
SPS_TO_FILTER_CUTOFF: Dict[int, int] = {
    100: 16,     # Only 16 Hz works
    200: 60,     # 16 Hz or 60 Hz (use 60 Hz as it's factory default)
    500: 60,     # 16 Hz, 60 Hz, or 210 Hz (use 60 Hz for consistency)
    1000: 210,   # 16 Hz, 60 Hz, 210 Hz, or 460 Hz (use 210 Hz for better performance)
}

# Fixed configuration values
FIXED_BAUD_RATE = 0x0200  # 230.4 kbps (bits [9:8] = 10)
# SIG_CTRL: bit[7]=0 (X acceleration), bit[6]=0 (Y acceleration), bit[5]=0 (Z acceleration),
#           bit[4]=0 (standard noise floor), bit[2]=1 (TEMP_STABIL enabled)
# Value: 0x0004 (bit[2] = 1)
FIXED_SIG_CTRL = 0x0004   # Acceleration output (all axes), standard noise floor, TEMP_STABIL=1
# BURST_CTRL: Following acc_automode.py logic
# BURST_CTRL_L = 0x02 (COUNT_OUT=1, bit[1]=1)
# BURST_CTRL_H = 0x47 (TEMP_OUT=1, ACCX_OUT=1, ACCY_OUT=1, ACCZ_OUT=1)
# Value: 0x4702 = high byte 0x47, low byte 0x02
FIXED_BURST_CTRL_L = 0x02  # COUNT_OUT=1
FIXED_BURST_CTRL_H = 0x47  # TEMP_OUT=1, ACCX_OUT=1, ACCY_OUT=1, ACCZ_OUT=1

# Product ID and Serial Number register addresses (Window 1)
PROD_ID_REGISTERS = (0x6A, 0x6C, 0x6E, 0x70)
SERIAL_REGISTERS = (0x74, 0x76, 0x78, 0x7A)

PRODUCT_ID_ALIASES: Dict[str, str] = {
    "A352AD10": "M-A552AR1",
}


class AccelerometerConfigurator:
    """Accelerometer configuration operations."""

    def __init__(self, comm: SensorCommunication):
        self.comm = comm
        self._warnings: List[str] = []

    def _add_warning(self, message: str) -> None:
        self._warnings.append(message)

    def collect_warnings(self) -> List[str]:
        warnings = list(self._warnings)
        self._warnings.clear()
        return warnings

    def _write_commands(self, commands: List[List[int]]) -> None:
        """Send multiple commands to sensor."""
        self.comm.send_commands(commands)

    def reset_sensor(self) -> None:
        """Send reset commands to sensor to exit auto mode and enter configuration mode."""
        logger.info("Resetting sensor...")
        
        # Flush any streaming data first
        if hasattr(self.comm, "flush_input_buffer"):
            for _ in range(10):
                self.comm.flush_input_buffer()
                time.sleep(0.02)
        
        # Exit auto mode: Write "01" to MODE_CMD (MODE_CTRL [0x02(W0)], bit [9:8])
        # First switch to Window 0, then write MODE_CTRL
        # Command format: [0, address, data, 0x0D] (no response expected, so first byte is 0)
        # Address 0x83 = 0x80 | 0x03 (write to MODE_CTRL high byte)
        # Data 0x02 sets bit[9:8] = 01 (Configuration mode)
        self._write_commands([
            [0, 0xFE, 0x00, 0x0D],  # Switch to Window 0 (WINDOW_ID register)
            [0, 0x83, 0x02, 0x0D],  # MODE_CTRL(H) write: return to Configuration mode (bit[9:8]=01)
        ])
        time.sleep(0.5)
        
        # Also clear UART_AUTO to stop streaming
        self._write_commands([
            [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
            [0, 0x88, 0x00, 0x0D],  # UART_CTRL(L): Clear UART_AUTO and AUTO_START
        ])
        time.sleep(0.2)
        
        # Flush again after stopping streaming
        if hasattr(self.comm, "flush_input_buffer"):
            for _ in range(5):
                self.comm.flush_input_buffer()
                time.sleep(0.02)
        
        logger.info("Sensor reset to configuration mode")

    def _wait_for_filter_settle(self, timeout: float = 2.0) -> bool:
        """Wait for filter setting to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if filter setting completed, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Read FILTER_CTRL register (Window 1)
                result = self.comm.send_commands([
                    [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1 (WINDOW_ID register)
                    [4, 0x06, 0x00, 0x0D],  # Read FILTER_CTRL register (at 0x06, expect 4 bytes)
                ])
                if len(result) >= 4:
                    filter_ctrl_low = result[-2]  # Low byte
                    filter_stat = (filter_ctrl_low >> 5) & 0x01  # Bit[5] is FILTER_STAT
                    if filter_stat == 0:  # Filter setting completed
                        return True
            except Exception as e:
                logger.debug(f"Error checking filter status: {e}")
            time.sleep(0.1)
        return False

    def set_output_rate(self, sps_rate: int) -> bool:
        """Set the data output rate (sampling rate).
        
        Following acc_automode.py logic: write SMPL_CTRL_H directly.
        
        Args:
            sps_rate: Samples per second (100, 200, 500, or 1000)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if sps_rate not in SPS_TO_SMPL_CTRL_H:
                logger.error(f"Invalid SPS rate: {sps_rate}. Valid rates: {list(SPS_TO_SMPL_CTRL_H.keys())}")
                return False
            
            smpl_ctrl_h = SPS_TO_SMPL_CTRL_H[sps_rate]
            # SMPL_CTRL register is at 0x04-0x05 (Window 1)
            # Write SMPL_CTRL_H directly to address 0x85 (following acc_automode.py)
            # Address 0x85 = 0x80 | 0x05 (SMPL_CTRL high byte)
            self._write_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1 (WINDOW_ID register)
                [0, 0x85, smpl_ctrl_h, 0x0D],  # Write SMPL_CTRL(H) with rate value
            ])
            logger.info(f"Output rate set to {sps_rate} Sps (SMPL_CTRL_H=0x{smpl_ctrl_h:02X})")
            return True
        except Exception as e:
            logger.error(f"Failed to set output rate: {e}")
            return False

    def set_filter(self, sps_rate: int) -> bool:
        """Set the FIR filter (512 taps) with appropriate cutoff frequency for the SPS rate.
        
        Args:
            sps_rate: Samples per second (determines cutoff frequency)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if sps_rate not in SPS_TO_FILTER_CUTOFF:
                logger.error(f"Invalid SPS rate: {sps_rate}")
                return False
            
            cutoff_hz = SPS_TO_FILTER_CUTOFF[sps_rate]
            if cutoff_hz not in FILTER_CUTOFF_512TAPS:
                logger.error(f"Invalid cutoff frequency: {cutoff_hz} Hz")
                return False
            
            filter_sel = FILTER_CUTOFF_512TAPS[cutoff_hz]
            # FILTER_CTRL register is at 0x06-0x07 (Window 1)
            # FILTER_SEL is in bits [3:0] of low byte
            # Address 0x86 = 0x80 | 0x06 (FILTER_CTRL low byte)
            self._write_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1 (WINDOW_ID register)
                [0, 0x86, filter_sel & 0xFF, 0x0D],  # Write FILTER_CTRL(L) with FILTER_SEL
            ])
            logger.info(f"Filter set to 512 taps, cutoff {cutoff_hz} Hz (for {sps_rate} Sps)")
            
            # Wait for filter setting to complete
            if not self._wait_for_filter_settle():
                logger.warning("Filter setting may not have completed (timeout)")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to set filter: {e}")
            return False

    def set_fixed_configuration(self) -> bool:
        """Set fixed configuration values following acc_automode.py logic.
        
        Sets BURST_CTRL and UART_CTRL registers (matching acc_automode.py set_registers).
        Note: SIG_CTRL is not set in acc_automode.py, so we skip it to match exactly.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Following acc_automode.py set_registers() function
            # All these registers are in Window 1
            commands = [
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1 (WINDOW_ID register)
                # UART_CTRL(L) = 0x03 (UART Auto sampling=1, Auto start=1)
                [0, 0x88, 0x03, 0x0D],  # UART_CTRL(L) write command
                # BURST_CTRL(L) = 0x02 (COUNT_OUT=1)
                [0, 0x8C, FIXED_BURST_CTRL_L, 0x0D],  # BURST_CTRL(L) write command
                # BURST_CTRL(H) = 0x47 (TEMP_OUT=1, ACCX_OUT=1, ACCY_OUT=1, ACCZ_OUT=1)
                [0, 0x8D, FIXED_BURST_CTRL_H, 0x0D],  # BURST_CTRL(H) write command
            ]
            self._write_commands(commands)
            logger.info("Fixed configuration set (following acc_automode.py):")
            logger.info("  - UART_CTRL(L): UART_AUTO=1, AUTO_START=1")
            logger.info("  - BURST_CTRL(L): COUNT_OUT=1")
            logger.info("  - BURST_CTRL(H): TEMP_OUT=1, ACCX_OUT=1, ACCY_OUT=1, ACCZ_OUT=1")
            return True
        except Exception as e:
            logger.error(f"Failed to set fixed configuration: {e}")
            return False

    def flash_backup(self) -> bool:
        """Store current register settings to non-volatile memory.
        
        Follows datasheet section 8.1.7 procedure:
        1. Write FLASH_BACKUP command to GLOB_CMD(L) at 0x8A
        2. Poll GLOB_CMD until FLASH_BACKUP bit[3] goes to 0
        3. Verify FLASH_BU_ERR in DIAG_STAT is 0
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting flash backup...")
            
            # Step (a): Send flash backup command
            # GLOB_CMD register is at 0x0A-0x0B (Window 1)
            # FLASH_BACKUP is bit [3] of LOW byte (not high byte!)
            # Write 0x08 to GLOB_CMD(L) at address 0x8A (0x80 | 0x0A)
            logger.debug("Writing FLASH_BACKUP command to GLOB_CMD(L) at 0x8A")
            self._write_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1 (WINDOW_ID register)
                [0, 0x8A, 0x08, 0x0D],  # Set FLASH_BACKUP bit [3] in GLOB_CMD(L)
            ])
            
            # Step (b): Wait until flash backup has finished
            # Poll GLOB_CMD register (0x0A) until FLASH_BACKUP bit[3] goes to 0
            logger.debug("Polling GLOB_CMD register waiting for FLASH_BACKUP bit to clear...")
            start = time.time()
            flash_backup_cleared = False
            
            while time.time() - start < FLASH_BACKUP_TIMEOUT:
                # Read GLOB_CMD register (0x0A in Window 1)
                result = self.comm.send_commands([
                    [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                    [4, 0x0A, 0x00, 0x0D],  # Read GLOB_CMD register (expect 4 bytes)
                ])
                
                if len(result) >= 4:
                    # Response format: [0x0A, MSByte, LSByte, 0x0D]
                    glob_cmd_low = result[-2]  # Low byte
                    # FLASH_BACKUP is bit[3] in low byte
                    flash_backup_bit = (glob_cmd_low >> 3) & 0x01
                    
                    if flash_backup_bit == 0:
                        flash_backup_cleared = True
                        logger.info("FLASH_BACKUP bit cleared (backup operation complete)")
                        break
                    else:
                        # Still in progress, continue polling
                        time.sleep(BACKUP_POLL_INTERVAL)
                else:
                    time.sleep(BACKUP_POLL_INTERVAL)
            
            if not flash_backup_cleared:
                logger.error("Flash backup timeout: FLASH_BACKUP bit did not clear within timeout period")
                return False
            
            # Step (c): Confirm the result by checking FLASH_BU_ERR
            # FLASH_BU_ERR is in DIAG_STAT[0x04(W0)] bit[0]
            logger.debug("Checking FLASH_BU_ERR in DIAG_STAT register...")
            time.sleep(0.1)  # Small delay before checking error status
            
            result = self.comm.send_commands([
                [0, 0xFE, 0x00, 0x0D],  # Switch to Window 0 (WINDOW_ID register)
                [4, 0x04, 0x00, 0x0D],  # Read DIAG_STAT register (at 0x04, expect 4 bytes)
            ])
            
            if len(result) >= 4:
                flash_bu_err = result[-2] & 0x01  # Bit [0] is FLASH_BU_ERR
                if flash_bu_err == 0:
                    logger.info("Flash backup completed successfully (FLASH_BU_ERR=0)")
                    return True
                else:
                    logger.error("Flash backup failed: FLASH_BU_ERR=1 (error occurred)")
                    return False
            else:
                logger.error("Failed to read DIAG_STAT register for FLASH_BU_ERR verification")
                return False
            
        except Exception as e:
            logger.error(f"Flash backup failed with exception: {e}")
            return False

    def configure(self, sps_rate: int) -> bool:
        """Configure accelerometer in UART Auto Start mode.
        
        Following acc_automode.py logic: set registers, wait for filter, flash backup.
        
        Args:
            sps_rate: Samples per second (100, 200, 500, or 1000)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Configuring accelerometer for {sps_rate} Sps (following acc_automode.py logic)...")
            
            # Reset sensor to configuration mode
            self.reset_sensor()
            time.sleep(0.2)
            
            # Step 1: Set fixed configuration (BURST_CTRL, UART_CTRL)
            # Following acc_automode.py set_registers() - sets UART_CTRL and BURST_CTRL first
            if not self.set_fixed_configuration():
                return False
            time.sleep(0.1)
            
            # Step 2: Set output rate (SMPL_CTRL_H)
            # Following acc_automode.py - sets SMPL_CTRL_H
            if not self.set_output_rate(sps_rate):
                return False
            time.sleep(0.1)
            
            # Step 3: Set filter (FILTER_CTRL_L)
            # Following acc_automode.py - sets FILTER_CTRL_L and waits for filter setting
            if not self.set_filter(sps_rate):
                logger.warning("Filter setting may not have completed, continuing anyway...")
            time.sleep(0.2)
            
            # Step 4: Execute flash backup
            # Following acc_automode.py flash_backup()
            if not self.flash_backup():
                return False
            
            logger.info("Accelerometer configured successfully")
            logger.info("After power cycle or reset, sensor will automatically start transmitting data")
            logger.info(f"Configuration: {sps_rate} Sps, 512 taps, cutoff {SPS_TO_FILTER_CUTOFF[sps_rate]} Hz")
            logger.info(f"Configuration tool by {AUTHOR} at {ORGANIZATION}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False

    def exit_auto_mode(self, persist_disable_auto: bool = False) -> bool:
        """Exit auto mode and return to configuration mode.
        
        Args:
            persist_disable_auto: If True, disable auto-start and save to flash (permanent)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Exiting auto mode...")
            
            # Reset sensor to configuration mode
            self.reset_sensor()
            time.sleep(0.3)  # Increased delay for mode transition
            
            # Verify we're in configuration mode by checking MODE_CTRL
            # MODE_CTRL is at 0x02 (Window 0), bit[9:8] = MODE_CMD
            # In configuration mode, MODE_CMD should be "00" or we just set it to "01"
            verify_mode_result = self.comm.send_commands([
                [0, 0xFE, 0x00, 0x0D],  # Switch to Window 0
                [4, 0x02, 0x00, 0x0D],  # Read MODE_CTRL register (expect 4 bytes)
            ])
            
            if len(verify_mode_result) >= 4:
                mode_ctrl_high = verify_mode_result[-3]  # High byte
                mode_ctrl_low = verify_mode_result[-2]  # Low byte
                mode_ctrl = (mode_ctrl_high << 8) | mode_ctrl_low
                mode_cmd = (mode_ctrl >> 8) & 0x03  # Extract bits [9:8]
                logger.debug(f"MODE_CTRL read: 0x{mode_ctrl:04X}, MODE_CMD: {mode_cmd}")
                if mode_cmd != 0x01 and mode_cmd != 0x00:
                    logger.warning(f"Sensor may not be in configuration mode (MODE_CMD={mode_cmd})")
                else:
                    logger.info("Verified sensor is in configuration mode")
            
            # Read current UART_CTRL to preserve baud rate setting
            # UART_CTRL is at 0x08-0x09 (Window 1)
            # Response format: [0x08, MSB, LSB, 0x0D] = 4 bytes
            result = self.comm.send_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                [4, 0x08, 0x00, 0x0D],  # Read UART_CTRL register (expect 4 bytes)
            ])
            
            if len(result) < 4:
                logger.error("Failed to read UART_CTRL register (got %d bytes, expected 4)", len(result))
                return False
            
            uart_ctrl_high = result[-3]  # High byte: bit[9:8]=BAUD_RATE
            uart_ctrl_low = result[-2]  # Low byte: bit[1]=AUTO_START, bit[0]=UART_AUTO
            
            logger.debug(f"Current UART_CTRL(L): 0x{uart_ctrl_low:02X}, UART_CTRL(H): 0x{uart_ctrl_high:02X}")
            
            # Clear AUTO_START (bit[1]) and UART_AUTO (bit[0]) bits
            # Keep other bits unchanged (though they should be 0)
            new_uart_ctrl_low = uart_ctrl_low & 0xFC  # Clear bits [1:0] = 11111100 mask
            
            # Write updated UART_CTRL(L) with AUTO_START and UART_AUTO disabled
            self._write_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                [0, 0x88, new_uart_ctrl_low, 0x0D],  # UART_CTRL(L): Clear AUTO_START and UART_AUTO
            ])
            logger.info(f"UART_CTRL(L) updated: 0x{uart_ctrl_low:02X} -> 0x{new_uart_ctrl_low:02X} (AUTO_START=0, UART_AUTO=0)")
            
            # Verify the write was successful
            time.sleep(0.1)
            verify_result = self.comm.send_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                [4, 0x08, 0x00, 0x0D],  # Read UART_CTRL register to verify (expect 4 bytes)
            ])
            
            if len(verify_result) >= 4:
                verified_low = verify_result[-2]  # Low byte
                
                if verified_low & 0x03 != 0:  # Check if bits [1:0] are cleared
                    logger.error(f"UART_CTRL verification failed: expected bits [1:0]=00, got 0x{verified_low:02X}")
                    logger.error("Cannot proceed with flash backup if register write failed")
                    return False
                else:
                    logger.info("UART_CTRL write verified successfully (AUTO_START=0, UART_AUTO=0)")
            else:
                logger.error("Failed to read UART_CTRL for verification (got %d bytes, expected 4)", len(verify_result))
                return False
            
            if persist_disable_auto:
                logger.info("Persisting configuration mode via flash backup...")
                time.sleep(0.2)  # Delay before flash backup to ensure register write is complete
                
                if not self.flash_backup():
                    logger.error("Failed to persist configuration mode")
                    return False
                
                # Verify again after flash backup that UART_CTRL is still cleared
                time.sleep(0.2)
                final_verify = self.comm.send_commands([
                    [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                    [4, 0x08, 0x00, 0x0D],  # Read UART_CTRL register (expect 4 bytes)
                ])
                
                if len(final_verify) >= 4:
                    final_low = final_verify[-2]  # Low byte
                    
                    if final_low & 0x03 == 0:
                        logger.info("Final verification: UART_CTRL bits cleared correctly (AUTO_START=0, UART_AUTO=0)")
                    else:
                        logger.error(f"Final verification failed: UART_CTRL(L)=0x{final_low:02X} (bits [1:0] should be 00)")
                        return False
                else:
                    logger.warning("Final verification: Could not read UART_CTRL (got %d bytes, expected 4)", len(final_verify))
                
                logger.info("Configuration mode saved to flash (permanent)")
                logger.info("Auto-start is now permanently disabled")
                logger.info("After power cycle, sensor will remain in configuration mode")
            else:
                logger.info("Sensor is now in configuration mode (temporary)")
                logger.info("After power cycle, sensor will resume auto-start if previously configured")
            
            return True
        except Exception as e:
            logger.error(f"Failed to exit auto mode: {e}")
            return False

    def _enter_configuration_mode(self) -> None:
        """Ensure sensor is in configuration mode."""
        self.reset_sensor()
        time.sleep(0.2)

    def _wait_until_ready(self, timeout: float = 1.0) -> bool:
        """Wait until sensor is ready (NOT_READY bit in GLOB_CMD is 0).
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if sensor is ready, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = self.comm.send_commands([
                    [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                    [4, 0x0A, 0x00, 0x0D],  # Read GLOB_CMD register (expect 4 bytes)
                ])
                if len(result) >= 4:
                    glob_cmd_low = result[-2]  # Low byte
                    not_ready = glob_cmd_low & 0x01  # Bit[0] is NOT_READY
                    if not_ready == 0:
                        return True
            except Exception:
                pass
            time.sleep(0.05)
        return False

    def _read_word(self, address: int, window: int) -> Optional[int]:
        """Read a 16-bit word from a register.
        
        Args:
            address: Register address (low byte)
            window: Window number (0 or 1)
            
        Returns:
            The 16-bit word value, or None if read failed
        """
        commands = [
            [0, 0xFE, window & 0xFF, 0x0D],
            [4, address & 0xFF, 0x00, 0x0D],
        ]
        if hasattr(self.comm, "flush_input_buffer"):
            self.comm.flush_input_buffer()
        result = self.comm.send_commands(commands)
        if len(result) < 4:
            logger.error(
                "Register read returned insufficient data for 0x%02X (got %s bytes: %s)",
                address,
                len(result),
                " ".join(f"0x{byte:02X}" for byte in result) or "none",
            )
            return None
        msb = result[-3]
        lsb = result[-2]
        return (msb << 8) | lsb

    @staticmethod
    def _decode_ascii_words(words: List[int], little_endian: bool = True) -> str:
        """Decode a list of 16-bit words as ASCII characters.
        
        Args:
            words: List of 16-bit word values
            little_endian: If True, treat each word as little-endian (LSB first)
            
        Returns:
            Decoded ASCII string
        """
        chars: List[str] = []
        for word in words:
            if little_endian:
                # Little-endian: LSB first, then MSB
                chars.append(chr(word & 0xFF))  # Low byte
                chars.append(chr((word >> 8) & 0xFF))  # High byte
            else:
                # Big-endian: MSB first, then LSB
                chars.append(chr((word >> 8) & 0xFF))  # High byte
                chars.append(chr(word & 0xFF))  # Low byte
        return "".join(chars).strip("\x00")

    def detect_identity(self) -> Optional[dict]:
        """Detect sensor identity (product ID and serial number).
        
        Returns:
            Dictionary with product_id, product_id_raw, serial_number, or None if failed
        """
        logger.info("Reading product and serial number registers")
        
        # Ensure the sensor is in a clean configuration state before reading
        # This will stop any streaming and enter configuration mode
        self.reset_sensor()
        time.sleep(0.3)
        self._enter_configuration_mode()
        time.sleep(0.2)
        
        product_words = []
        for reg in PROD_ID_REGISTERS:
            word = self._read_word(reg, 0x01)  # Window 1
            if word is None:
                logger.warning("Retrying product ID register 0x%02X", reg)
                # Re-enter configuration mode and flush buffer
                if hasattr(self.comm, "flush_input_buffer"):
                    self.comm.flush_input_buffer()
                self._enter_configuration_mode()
                time.sleep(0.1)
                word = self._read_word(reg, 0x01)
            if word is None:
                logger.error("Failed to read product ID register 0x%02X after retry", reg)
                return None
            product_words.append(word)
            time.sleep(0.05)  # Small delay between reads
        
        logger.info(
            "Product ID raw words: %s",
            " ".join(f"0x{word:04X}" for word in product_words),
        )
        product_id_raw = self._decode_ascii_words(product_words, little_endian=True)
        product_id = PRODUCT_ID_ALIASES.get(product_id_raw, product_id_raw)
        
        serial_words = []
        for reg in SERIAL_REGISTERS:
            word = self._read_word(reg, 0x01)  # Window 1
            if word is None:
                logger.warning("Retrying serial register 0x%02X", reg)
                # Re-enter configuration mode and flush buffer
                if hasattr(self.comm, "flush_input_buffer"):
                    self.comm.flush_input_buffer()
                self._enter_configuration_mode()
                time.sleep(0.1)
                word = self._read_word(reg, 0x01)
            if word is None:
                logger.error("Failed to read serial register 0x%02X after retry", reg)
                return None
            serial_words.append(word)
            time.sleep(0.05)  # Small delay between reads
        
        logger.info(
            "Serial number raw words: %s",
            " ".join(f"0x{word:04X}" for word in serial_words),
        )
        serial_number = self._decode_ascii_words(serial_words, little_endian=True)
        
        # Return to window 0 for safety
        self._write_commands([[0, 0xFE, 0x00, 0x0D]])
        return {
            "product_id": product_id or "",
            "product_id_raw": product_id_raw or "",
            "serial_number": serial_number or "",
            "product_words": product_words,
            "serial_words": serial_words,
        }

    def check_auto_mode(self) -> bool:
        """Check if the sensor is currently in auto mode.
        
        Returns:
            True if sensor is in auto mode, False otherwise
        """
        try:
            logger.info("Checking if sensor is in auto mode...")
            
            # First, try to exit auto mode temporarily to read registers
            # If sensor is streaming, we need to stop it first
            if hasattr(self.comm, "flush_input_buffer"):
                for _ in range(10):  # More aggressive flushing
                    self.comm.flush_input_buffer()
                    time.sleep(0.05)
            
            # Try to read UART_CTRL register to check UART_AUTO and AUTO_START bits
            # UART_CTRL is at 0x08 (Window 1)
            # If sensor is in auto mode, we might not be able to read registers
            # So we'll try to read, and if it fails, assume auto mode
            try:
                result = self.comm.send_commands([
                    [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                    [4, 0x08, 0x00, 0x0D],  # Read UART_CTRL register
                ])
                
                if len(result) >= 4:
                    uart_ctrl_low = result[-2]  # Low byte
                    uart_auto = uart_ctrl_low & 0x01  # Bit[0]
                    auto_start = (uart_ctrl_low >> 1) & 0x01  # Bit[1]
                    
                    if uart_auto == 1 and auto_start == 1:
                        logger.info("Sensor is in auto mode (UART_AUTO=1, AUTO_START=1)")
                        return True
                    else:
                        logger.info("Sensor is not in auto mode (UART_AUTO=%d, AUTO_START=%d)", uart_auto, auto_start)
                        return False
            except Exception as read_err:
                logger.debug("Could not read UART_CTRL register (sensor may be streaming): %s", read_err)
            
            # If we can't read the register, assume auto mode to be safe
            # This is because when in auto mode, register reads are not supported
            logger.warning("Could not read UART_CTRL - assuming auto mode (sensor may be streaming)")
            return True
        except Exception as e:
            logger.warning("Failed to check auto mode status - assuming auto mode to be safe: %s", e)
            return True

    def full_reset(self, persist_disable_auto: bool = True) -> bool:
        """Perform a full reset of the sensor (exit auto mode + flash reset).
        
        Args:
            persist_disable_auto: If True, permanently disable auto-start before reset
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting full accelerometer reset (persist disable=%s)", persist_disable_auto)
        self._warnings.clear()
        try:
            if persist_disable_auto:
                logger.info("Clearing auto mode and persisting before proceeding with reset")
                if not self.exit_auto_mode(persist_disable_auto=True):
                    return False
            
            # Reset sensor to configuration mode
            self.reset_sensor()
            time.sleep(0.2)
            
            # Perform flash reset (GLOB_CMD bit[2] = FLASH_RST)
            logger.info("Performing flash reset...")
            self._write_commands([
                [0, 0xFE, 0x01, 0x0D],  # Switch to Window 1
                [0, 0x8A, 0x04, 0x0D],  # GLOB_CMD(L): Set FLASH_RST bit[2]
            ])
            
            # Wait for flash reset to complete (up to 2 seconds based on datasheet)
            time.sleep(2.0)
            
            logger.info("Accelerometer full reset sequence completed")
            return True
        except Exception as exc:
            logger.error("Full reset sequence failed: %s", exc)
            return False


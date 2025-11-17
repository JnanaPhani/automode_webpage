"""
Sensor configuration module.

This module handles sensor configuration operations including
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

PROD_ID_REGISTERS = (0x6A, 0x6C, 0x6E, 0x70)
SERIAL_REGISTERS = (0x74, 0x76, 0x78, 0x7A)

PRODUCT_ID_ALIASES: Dict[str, str] = {
    "A342VD10": "M-A542VR1",
}


class SensorConfigurator:
    """Sensor configuration operations."""

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
        self.comm.send_commands(commands)

    def reset_sensor(self) -> None:
        """Send reset commands to sensor."""
        self._write_commands(
            [
                [0, 0xFF, 0xFF, 0x0D],
                [0, 0xFF, 0xFF, 0x0D],
                [0, 0xFF, 0xFF, 0x0D],
            ]
        )
        logger.debug("Sensor reset commands sent")

    def _enter_configuration_mode(self) -> None:
        """Ensure the sensor is in configuration mode before issuing reads."""
        if hasattr(self.comm, "flush_input_buffer"):
            self.comm.flush_input_buffer()
        # Request configuration mode (MODE_CMD=0b10)
        self._write_commands(
            [
                [0, 0xFE, 0x00, 0x0D],
                [0, 0x83, 0x02, 0x0D],
            ]
        )
        time.sleep(0.05)
        # Clear UART auto bits so burst streaming pauses while we read registers.
        self._write_commands(
            [
                [0, 0xFE, 0x01, 0x0D],
                [0, 0x88, 0x00, 0x0D],
            ]
        )
        time.sleep(0.05)
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: float = 3.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                if hasattr(self.comm, "flush_input_buffer"):
                    self.comm.flush_input_buffer()
                result = self.comm.send_commands(
                    [
                        [0, 0xFE, 0x01, 0x0D],
                        [4, 0x0A, 0x00, 0x0D],
                    ]
                )
                if len(result) >= 4:
                    glob_cmd = (result[-3] << 8) | result[-2]
                    if (glob_cmd & 0x0400) == 0:
                        return True
            except TimeoutError:
                logger.debug("Waiting for sensor ready... (timeout)")
            except Exception:
                logger.debug("Transient error while waiting for ready", exc_info=True)
            time.sleep(0.05)
        logger.warning("Timed out waiting for sensor ready state")
        return False

    def _read_word(self, address: int, window: int) -> Optional[int]:
        try:
            # Drop any burst/streaming bytes before issuing a register read so that
            # the response contains only the register frame we are expecting.
            if hasattr(self.comm, "flush_input_buffer"):
                self.comm.flush_input_buffer()
            result = self.comm.send_commands(
                [
                    [0, 0xFE, window & 0xFF, 0x0D],
                    [4, address & 0xFF, 0x00, 0x0D],
                ]
            )
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
        except Exception:
            logger.exception("Failed to read register 0x%02X", address)
            return None

    @staticmethod
    def _decode_ascii_words(words: List[int], little_endian: bool = True) -> str:
        chars: List[str] = []
        for word in words:
            low = word & 0xFF
            high = (word >> 8) & 0xFF
            order = (low, high) if little_endian else (high, low)
            for byte in order:
                if byte != 0x00:
                    chars.append(chr(byte))
        return "".join(chars).strip()

    def check_auto_mode(self) -> bool:
        """Check if the sensor is currently in auto mode.
        
        This is a read-only check that does NOT change the sensor's state.
        
        Returns:
            True if AUTO bit is set in MODE_CTRL, False otherwise
        """
        try:
            logger.info("Checking if sensor is in auto mode...")
            # Flush buffer multiple times to clear any streaming data
            # We do this without sending any commands that would change the sensor state
            if hasattr(self.comm, "flush_input_buffer"):
                for _ in range(5):
                    self.comm.flush_input_buffer()
                    time.sleep(0.05)
            
            # Try to read MODE_CTRL register directly without changing sensor state
            # If sensor is streaming, we might get corrupted data, so try a few times
            valid_reads = 0
            auto_mode_reads = 0
            streaming_detected = 0
            
            for attempt in range(5):
                try:
                    # Just read the register - don't send any commands that change state
                    result = self.comm.send_commands(
                        [
                            [0, 0xFE, 0x00, 0x0D],  # Select window 0
                            [4, 0x02, 0x00, 0x0D],  # Read MODE_CTRL register (address 0x02)
                        ]
                    )
                    # Check if we got a valid response (should be exactly 4 bytes: addr, msb, lsb, cr)
                    if len(result) == 4:
                        mode_register = (result[-3] << 8) | result[-2]
                        # If AUTO bit (bit 10 = 0x0400) is set, it's in auto mode
                        if (mode_register & 0x0400) != 0:
                            auto_mode_reads += 1
                            logger.debug("Auto mode detected: MODE_CTRL=0x%04X", mode_register)
                        else:
                            valid_reads += 1
                            logger.debug("Not in auto mode: MODE_CTRL=0x%04X", mode_register)
                    elif len(result) > 4:
                        # Extra bytes indicate streaming data mixed in - sensor is likely in auto mode
                        streaming_detected += 1
                        logger.debug("Response has extra bytes (%d bytes) - likely streaming (auto mode)", len(result))
                        time.sleep(0.1)
                        continue
                    else:
                        # Too few bytes - might be streaming or error
                        logger.debug("Response too short (%d bytes) - retrying", len(result))
                        time.sleep(0.1)
                        continue
                except Exception:
                    if attempt < 4:
                        time.sleep(0.1)
                        continue
                    # If we can't read at all after multiple attempts, likely streaming
                    logger.debug("Could not read MODE_CTRL after %d attempts - sensor likely in auto mode", attempt + 1)
                    streaming_detected += 1
            
            # Decision logic: prioritize actual register reads over streaming detection
            # Trust valid reads - if we get consistent reads, use them
            
            # If we got multiple consistent auto mode reads, return True
            if auto_mode_reads >= 2:
                logger.info("Sensor is in auto mode (AUTO bit set in MODE_CTRL, %d consistent reads)", auto_mode_reads)
                return True
            
            # If we got multiple consistent valid reads saying NOT in auto mode, trust that
            if valid_reads >= 2:
                logger.info("Sensor is not in auto mode (MODE_CTRL AUTO bit not set, %d consistent reads)", valid_reads)
                return False
            
            # If we got one auto mode read and streaming detected, likely auto mode
            if auto_mode_reads >= 1 and streaming_detected >= 2:
                logger.info("Sensor is likely in auto mode (AUTO bit set + streaming detected)")
                return True
            
            # If we got consistent streaming (3+ times) without valid reads, assume auto mode
            if streaming_detected >= 3 and valid_reads == 0:
                logger.info("Consistent streaming detected without valid reads - sensor likely in auto mode")
                return True
            
            # If we got one valid read saying NOT in auto mode and no streaming, trust it
            if valid_reads >= 1 and streaming_detected == 0:
                logger.info("Sensor is not in auto mode (MODE_CTRL AUTO bit not set, 1 valid read, no streaming)")
                return False
            
            # If we got one auto mode read, might be auto mode
            if auto_mode_reads >= 1:
                logger.warning("Got one auto mode read - assuming auto mode to be safe")
                return True
            
            # If we got some streaming but also got valid reads, trust the valid reads
            if valid_reads >= 1:
                logger.info("Got valid read saying not in auto mode despite some streaming - trusting valid read")
                return False
            
            # If we couldn't get any valid reads but got some streaming, assume auto mode
            if streaming_detected >= 1:
                logger.warning("Some streaming detected but no valid reads - assuming auto mode")
                return True
            
            # If we couldn't get any valid reads at all, be conservative and assume NOT in auto mode
            # (Better to try detection than to incorrectly block it)
            logger.warning("Could not get reliable MODE_CTRL reads - assuming NOT in auto mode (will proceed with detection)")
            return False
        except Exception:
            logger.warning("Failed to check auto mode status - assuming auto mode to be safe", exc_info=True)
            # On error, assume auto mode to be safe (better to prompt user than miss it)
            return True

    def detect_identity(self) -> Optional[dict]:
        logger.info("Reading product and serial number registers")

        # Ensure the sensor is in a clean configuration state before reading.
        self.reset_sensor()
        time.sleep(0.2)
        self._enter_configuration_mode()

        product_words = []
        for reg in PROD_ID_REGISTERS:
            word = self._read_word(reg, 0x01)
            if word is None and product_words:
                logger.warning("Retrying product ID register 0x%02X", reg)
                self._enter_configuration_mode()
                word = self._read_word(reg, 0x01)
            if word is None:
                logger.error("Failed to read product ID register 0x%02X", reg)
                return None
            product_words.append(word)
        logger.info(
            "Product ID raw words: %s",
            " ".join(f"0x{word:04X}" for word in product_words),
        )
        product_id_raw = self._decode_ascii_words(product_words, little_endian=True)
        product_id = PRODUCT_ID_ALIASES.get(product_id_raw, product_id_raw)

        serial_words = []
        for reg in SERIAL_REGISTERS:
            word = self._read_word(reg, 0x01)
            if word is None and serial_words:
                logger.warning("Retrying serial register 0x%02X", reg)
                self._enter_configuration_mode()
                word = self._read_word(reg, 0x01)
            if word is None:
                logger.error("Failed to read serial register 0x%02X", reg)
                return None
            serial_words.append(word)
        logger.info(
            "Serial number raw words: %s",
            " ".join(f"0x{word:04X}" for word in serial_words),
        )
        serial_number = self._decode_ascii_words(serial_words, little_endian=True)

        self._write_commands([[0, 0xFE, 0x00, 0x0D]])
        return {
            "product_id": product_id or "",
            "product_id_raw": product_id_raw or "",
            "serial_number": serial_number or "",
            "product_words": product_words,
            "serial_words": serial_words,
        }

    def set_uart_auto_start(self) -> bool:
        try:
            self.reset_sensor()
            time.sleep(0.1)

            commands = [
                [0, 0xFE, 0x01, 0x0D],
                [0, 0x88, 0x03, 0x0D],
            ]
            self._write_commands(commands)
            logger.info("UART_CTRL register set to 0x03 (AUTO_START=1, UART_AUTO=1)")
            return True
        except Exception as e:
            logger.error("Failed to set UART_CTRL: %s", e)
            return False

    def flash_backup(self) -> bool:
        """Perform non-volatile memory backup to persist Auto Start setting.
        
        According to documentation:
        1. Write FLASH_BACKUP command to GLOB_CMD register
        2. Wait for backup completion by polling GLOB_CMD bit [3]
        3. Verify backup result by checking FLASH_BU_ERR in DIAG_STAT1
        
        Returns:
            True if backup successful, False otherwise
        """
        try:
            # Step 1: Write FLASH_BACKUP command
            commands = [
                [0, 0xFE, 0x01, 0x0D],  # Window 1
                [0, 0x8A, 0x08, 0x0D],  # GLOB_CMD: FLASH_BACKUP=1 (bit [3])
            ]
            self.comm.send_commands(commands)
            logger.info("Flash backup command sent")
            
            # Step 2: Wait for backup completion by polling GLOB_CMD
            start_time = time.time()
            while time.time() - start_time < FLASH_BACKUP_TIMEOUT:
                # Read GLOB_CMD register
                read_commands = [
                    [0, 0xFE, 0x01, 0x0D],  # Window 1
                    [4, 0x0A, 0x00, 0x0D],  # Read GLOB_CMD -> 4 bytes
                ]
                result = self.comm.send_commands(read_commands)
                
                # Check bit [3] of GLOB_CMD (FLASH_BACKUP status)
                # Result format: [Addr, MSByte, LSByte, CR] for each read
                if len(result) >= 4:
                    # GLOB_CMD is 16-bit, bit [3] is in the lower byte
                    glob_cmd_low = result[2]  # LSByte
                    if (glob_cmd_low & 0b00001000) == 0:
                        logger.info("Flash backup completed")
                        break
                time.sleep(BACKUP_POLL_INTERVAL)
            else:
                logger.error("Flash backup timeout - backup may not have completed")
                return False
            
            # Step 3: Verify backup result by checking FLASH_BU_ERR
            verify_commands = [
                [0, 0xFE, 0x00, 0x0D],  # Window 0
                [4, 0x04, 0x00, 0x0D],  # Read DIAG_STAT1 -> 4 bytes
            ]
            result = self.comm.send_commands(verify_commands)
            
            if len(result) >= 4:
                # Check FLASH_BU_ERR (bit [0] of DIAG_STAT1)
                diag_stat1_low = result[2]  # LSByte
                if (diag_stat1_low & 0b00000001) == 0:
                    logger.info("Flash backup verified successfully")
                    return True
                else:
                    logger.error("Flash backup error detected (FLASH_BU_ERR=1)")
                    return False
            else:
                logger.error("Failed to read DIAG_STAT1 for verification")
                return False
                
        except Exception as e:
            logger.error(f"Flash backup failed: {e}")
            return False

    def configure(self) -> bool:
        """Configure sensor in UART Auto Start mode."""
        self._warnings.clear()
        try:
            if not self.set_uart_auto_start():
                return False
            if not self.flash_backup():
                warning_message = (
                    "Flash backup failed during configuration. Auto Start is enabled for this session, "
                    "but the setting may not persist after power cycle."
                )
                logger.warning(warning_message)
                self._add_warning(warning_message)
            logger.info("Sensor configured in UART Auto Start mode successfully")
            logger.info("After power cycle or reset, sensor will automatically start transmitting data")
            logger.info(f"Configuration tool by {AUTHOR} at {ORGANIZATION}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False

    def software_reset(self) -> bool:
        try:
            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],
                    [0, 0x8A, 0x80, 0x0D],
                ]
            )
            logger.info("Software reset command issued; waiting for reboot")
            return self._wait_until_ready(timeout=7.0)
        except Exception as exc:
            logger.error("Software reset failed: %s", exc)
            return False

    def flash_test(self) -> bool:
        try:
            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],
                    [0, 0x83, 0x08, 0x0D],
                ]
            )
            logger.info("Flash test command issued")

            start = time.time()
            while time.time() - start < FLASH_BACKUP_TIMEOUT:
                result = self.comm.send_commands(
                    [
                        [0, 0xFE, 0x01, 0x0D],
                        [4, 0x02, 0x00, 0x0D],
                    ]
                )
                if len(result) >= 4:
                    status = (result[-3] << 8) | result[-2]
                    if (status & 0x0400) == 0:
                        logger.debug("FLASH_TEST complete (MSC_CTRL=0x%04X)", status)
                        break
                time.sleep(BACKUP_POLL_INTERVAL)
            else:
                logger.error("Flash test timeout")
                return False

            diag_result = self.comm.send_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],
                    [4, 0x04, 0x00, 0x0D],
                ]
            )
            if len(diag_result) >= 4:
                diag_low = diag_result[-2]
                if diag_low & 0x04:
                    logger.error("FLASH_ERR flag set after flash test")
                    return False
            self._wait_until_ready(timeout=2.0)
            logger.info("Flash test completed successfully")
            return True
        except Exception as exc:
            logger.error("Flash test failed: %s", exc)
            return False

    def exit_auto_mode(self, persist_disable_auto: bool = False) -> bool:
        self._warnings.clear()
        try:
            logger.info("Requesting vibration sensor to exit UART Auto Mode")
            self._write_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],
                    [0, 0x83, 0x02, 0x0D],
                ]
            )
            time.sleep(0.05)

            result = self.comm.send_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],
                    [4, 0x02, 0x00, 0x0D],
                ]
            )

            mode_register = None
            if len(result) < 4:
                logger.warning("MODE_CTRL read response incomplete; assuming configuration mode.")
                self._add_warning("MODE_CTRL read response incomplete; assuming configuration mode.")
            else:
                mode_register = (result[-3] << 8) | result[-2]
                if (mode_register & 0x0400) == 0:
                    logger.info("Sensor reports configuration mode (MODE_CTRL=0x%04X)", mode_register)
                else:
                    logger.warning(
                        "Sensor reported MODE_CTRL=0x%04X with AUTO bit still set; continuing to clear UART_CTRL.",
                        mode_register,
                    )

            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],
                    [0, 0x88, 0x00, 0x0D],
                ]
            )
            logger.info("UART_CTRL cleared (0x88 -> 0x00)")

            if persist_disable_auto:
                logger.info("Persisting UART auto disable state via flash backup")
            if not self.flash_backup():
                logger.warning(
                    "Flash backup confirmation failed while disabling auto mode. Verify persistence after power cycle."
                )
                self._add_warning(
                    "Flash backup confirmation failed while disabling auto mode. Verify persistence after power cycle."
                )

            try:
                verify_result = self.comm.send_commands(
                    [
                        [0, 0xFE, 0x00, 0x0D],
                        [4, 0x02, 0x00, 0x0D],
                    ]
                )
                if len(verify_result) >= 4:
                    final_mode = (verify_result[-3] << 8) | verify_result[-2]
                    if (final_mode & 0x0400) == 0:
                        logger.info("Final MODE_CTRL check indicates configuration mode (0x%04X)", final_mode)
                    else:
                        logger.info(
                            "Post-clear MODE_CTRL still reports AUTO bit set (0x%04X); treating as transient since streaming has stopped.",
                            final_mode,
                        )
                else:
                    logger.info("Final MODE_CTRL verification response incomplete; treating as transient.")
            except Exception as exc:
                logger.info("Failed to verify final MODE_CTRL state: %s", exc)

            self._write_commands([[0, 0xFE, 0x00, 0x0D]])
            return True

        except Exception as exc:
            logger.error("Failed to exit auto mode: %s", exc)
            return False

    def full_reset(self, persist_disable_auto: bool = True) -> bool:
        logger.info(
            "Starting vibration sensor reset (exit auto -> flash test -> software reset, persist disable=%s)",
            persist_disable_auto,
        )
        self._warnings.clear()
        try:
            if persist_disable_auto:
                if not self.exit_auto_mode(persist_disable_auto=True):
                    return False
            else:
                self._write_commands([[0, 0xFE, 0x00, 0x0D]])

            self.reset_sensor()
            time.sleep(0.1)

            if not self.flash_test():
                logger.warning("Flash test reported an error; continuing with reset")
                self._add_warning("Flash test reported an error; configuration may not persist after reset.")

            if not self.software_reset():
                return False

            logger.info("Vibration sensor reset sequence completed. Allowing stabilization")
            time.sleep(0.8)
            return True
        except Exception as exc:
            logger.error("Full reset sequence failed: %s", exc)
            return False


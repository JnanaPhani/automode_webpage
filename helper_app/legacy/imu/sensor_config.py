"""
IMU sensor configuration module.

Implements the UART Auto Start sequence described in the
Epson M-G552PR80 IMU datasheet (sections 4.9, 5.1.4, 6.18,
7.1.7, and 7.1.10).

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import logging
import sys
import time
from typing import List, Optional

try:
    from sensor_comm import SensorCommunication
except ImportError:  # pragma: no cover - fallback for package usage
    try:
        from .sensor_comm import SensorCommunication
    except ImportError as exc:  # pragma: no cover - fatal error path
        print("Error: Could not import sensor_comm module")
        raise exc

logger = logging.getLogger(__name__)

AUTHOR = "Jnana Phani A (https://phani.zenithtek.in)"
ORGANIZATION = "Zenith Tek (https://zenithtek.in)"

FLASH_BACKUP_TIMEOUT = 5.0
BACKUP_POLL_INTERVAL = 0.1

PROD_ID_REGISTERS = (0x6A, 0x6C, 0x6E, 0x70)
SERIAL_REGISTERS = (0x74, 0x76, 0x78, 0x7A)

PRODUCT_ID_ALIASES = {
    "G365PDF1": "M-G552PR80",
}

# Sampling rate configuration mapping
# Format: (sampling_rate_sps, dout_rate_value, min_tap_value)
# Based on datasheet section 6.16 SMPL_CTRL Register
SAMPLING_RATE_CONFIG = {
    2000: (0x00, 0),      # 2000 Sps, TAP ≥ 0
    1000: (0x01, 2),      # 1000 Sps, TAP ≥ 2
    500: (0x02, 4),       # 500 Sps, TAP ≥ 4
    400: (0x08, 8),       # 400 Sps, TAP ≥ 8
    250: (0x03, 8),       # 250 Sps, TAP ≥ 8
    200: (0x09, 16),      # 200 Sps, TAP ≥ 16
    125: (0x04, 16),      # 125 Sps, TAP ≥ 16 (default)
    100: (0x0A, 32),      # 100 Sps, TAP ≥ 32
    80: (0x0B, 32),       # 80 Sps, TAP ≥ 32
    62.5: (0x05, 32),     # 62.5 Sps, TAP ≥ 32
    50: (0x0C, 64),       # 50 Sps, TAP ≥ 64
    40: (0x0D, 64),       # 40 Sps, TAP ≥ 64
    31.25: (0x06, 64),    # 31.25 Sps, TAP ≥ 64
    25: (0x0E, 128),      # 25 Sps, TAP = 128
    20: (0x0F, 128),      # 20 Sps, TAP = 128
    15.625: (0x07, 128),  # 15.625 Sps, TAP = 128
}

DEFAULT_SAMPLING_RATE = 125  # Default: 125 Sps


class SensorConfigurator:
    """Provide high-level configuration operations for the IMU."""

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
        """Send a list of command frames to the IMU."""
        self.comm.send_commands(commands)

    def reset_sensor(self) -> None:
        """Issue the standard reset spell (three 0xFF frames)."""
        self._write_commands(
            [
                [0, 0xFF, 0xFF, 0x0D],
                [0, 0xFF, 0xFF, 0x0D],
                [0, 0xFF, 0xFF, 0x0D],
            ]
        )
        logger.debug("IMU reset command sequence sent")
        self._wait_until_ready()

    def _enter_configuration_mode(self) -> None:
        """Ensure the IMU is in configuration mode before register access."""
        if hasattr(self.comm, "flush_input_buffer"):
            self.comm.flush_input_buffer()
        self._write_commands(
            [
                [0, 0xFE, 0x00, 0x0D],
                [0, 0x83, 0x02, 0x0D],
            ]
        )
        time.sleep(0.05)
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
                logger.debug("Waiting for IMU ready... (timeout)")
            except Exception:
                logger.debug("Transient error while waiting for ready", exc_info=True)
            time.sleep(0.05)
        logger.warning("Timed out waiting for IMU ready state")
        return False

    def software_reset(self) -> bool:
        try:
            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],  # WINDOW = 1
                    [0, 0x8A, 0x80, 0x0D],  # GLOB_CMD: SOFT_RST bit7
                ]
            )
            logger.info("Software reset command issued; waiting for reboot")
            if self._wait_until_ready(timeout=7.0):
                return True
            logger.error("IMU did not report ready after software reset")
            return False
        except Exception as exc:  # pragma: no cover
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
                        logger.debug("Flash test operation complete (MSC_CTRL=0x%04X)", status)
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
        except Exception as exc:  # pragma: no cover
            logger.error("Flash test failed: %s", exc)
            return False

    def full_reset(self, persist_disable_auto: bool = True) -> bool:
        logger.info(
            "Starting full IMU reset (exit auto + flash test + software reset, persist disable=%s)",
            persist_disable_auto,
        )
        self._warnings.clear()
        try:
            if persist_disable_auto:
                logger.info("Clearing auto mode and persisting before proceeding with reset")
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

            logger.info("IMU full reset sequence completed. Allowing reboot stabilization")
            time.sleep(0.8)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("Full reset sequence failed: %s", exc)
            return False

    def _read_word(self, address: int, window: int) -> Optional[int]:
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
        chars: List[str] = []
        for word in words:
            low = word & 0xFF
            high = (word >> 8) & 0xFF
            byte_order = (low, high) if little_endian else (high, low)
            for byte in byte_order:
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
        product_id = self._decode_ascii_words(product_words, little_endian=True)
        friendly_product_id = PRODUCT_ID_ALIASES.get(product_id, product_id)

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

        # Return to window 0 for safety
        self._write_commands([[0, 0xFE, 0x00, 0x0D]])
        return {
            "product_id": friendly_product_id or "",
            "product_id_raw": product_id or "",
            "serial_number": serial_number or "",
            "product_words": product_words,
            "serial_words": serial_words,
        }

    def configure_registers(self, sampling_rate: float = DEFAULT_SAMPLING_RATE, tap_value: Optional[int] = None) -> bool:
        """
        Write the IMU register settings for UART Auto Start.
        
        Args:
            sampling_rate: Sampling rate in SPS (samples per second). Must be one of the supported rates.
            tap_value: Optional TAP value for the moving average filter. If None, uses minimum required TAP.
        
        Returns:
            True if configuration succeeded, False otherwise.
        """
        try:
            # Validate and get sampling rate configuration
            if sampling_rate not in SAMPLING_RATE_CONFIG:
                supported_rates = sorted(SAMPLING_RATE_CONFIG.keys())
                logger.error(
                    "Unsupported sampling rate: %.3f SPS. Supported rates: %s",
                    sampling_rate,
                    ", ".join(f"{r} SPS" if isinstance(r, int) else f"{r:.3f} SPS" for r in supported_rates),
                )
                return False
            
            dout_rate, min_tap = SAMPLING_RATE_CONFIG[sampling_rate]
            
            # Determine TAP value
            if tap_value is None:
                tap_value = min_tap
            elif tap_value < min_tap:
                logger.warning(
                    "TAP value %d is below minimum %d for %.3f SPS. Using minimum TAP value.",
                    tap_value, min_tap, sampling_rate
                )
                tap_value = min_tap
            
            # Validate TAP value is one of the supported values
            supported_taps = [0, 2, 4, 8, 16, 32, 64, 128]
            if tap_value not in supported_taps:
                # Round to nearest supported value
                closest_tap = min(supported_taps, key=lambda x: abs(x - tap_value))
                logger.warning(
                    "TAP value %d is not a standard value. Using closest supported value: %d",
                    tap_value, closest_tap
                )
                tap_value = closest_tap
            
            logger.info(
                "Configuring IMU with sampling rate: %.3f SPS (DOUT_RATE=0x%02X), TAP=%d",
                sampling_rate, dout_rate, tap_value
            )
            
            register_writes: List[List[int]] = [
                [0, 0xFE, 0x01, 0x0D],  # WINDOW = 1
                [0, 0x85, dout_rate, 0x0D],  # SMPL_CTRL: DOUT_RATE in high byte
                [0, 0x86, tap_value, 0x0D],  # TAP: moving average filter taps
                [0, 0x88, 0x03, 0x0D],  # UART_CTRL: UART_AUTO=1, AUTO_START=1
                [0, 0x8C, 0x02, 0x0D],  # BURST_CTRL1: COUNT on, checksum off
                [0, 0x8D, 0xF0, 0x0D],  # BURST_CTRL2: FLAG, TEMP, GYRO, ACCL on
                [0, 0x8F, 0x70, 0x0D],  # BURST_CTRL4: 32-bit outputs
            ]
            self._write_commands(register_writes)
            logger.info(
                "IMU configuration registers programmed for UART Auto Start "
                "(%.3f SPS, TAP=%d)",
                sampling_rate, tap_value
            )
            return True
        except Exception as exc:  # pragma: no cover - serial runtime failure
            logger.error("Failed to configure IMU registers: %s", exc)
            return False

    def flash_backup(self) -> bool:
        """Execute the flash backup flow (datasheet section 7.1.7)."""
        try:
            # (a) Send flash backup command (WINDOW=1, GLOB_CMD bit[3]).
            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],  # WINDOW = 1
                    [0, 0x8A, 0x08, 0x0D],  # GLOB_CMD: FLASH_BACKUP = 1
                ]
            )
            logger.info("Flash backup command issued")

            # (b) Poll FLASH_BACKUP bit until it clears.
            start_time = time.time()
            while time.time() - start_time < FLASH_BACKUP_TIMEOUT:
                result = self.comm.send_commands(
                    [
                        [0, 0xFE, 0x01, 0x0D],  # WINDOW = 1
                        [4, 0x0A, 0x00, 0x0D],  # Read GLOB_CMD
                    ]
                )
                if len(result) >= 4:
                    glob_cmd_low = result[2]
                    if (glob_cmd_low & 0b00001000) == 0:
                        logger.debug("FLASH_BACKUP bit cleared")
                        break
                time.sleep(BACKUP_POLL_INTERVAL)
            else:
                logger.error("Flash backup timeout waiting for FLASH_BACKUP bit to clear")
                return False

            # (c) Confirm result by reading FLASH_BU_ERR (DIAG_STAT bit[0]).
            result = self.comm.send_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],  # WINDOW = 0
                    [4, 0x04, 0x00, 0x0D],  # Read DIAG_STAT
                ]
            )
            if len(result) >= 4:
                diag_stat_low = result[2]
                if (diag_stat_low & 0b00000001) == 0:
                    logger.info("Flash backup completed successfully")
                    return True
                logger.error("Flash backup error detected (FLASH_BU_ERR = 1)")
                return False

            logger.error("Failed to read DIAG_STAT for flash backup confirmation")
            return False

        except Exception as exc:  # pragma: no cover - serial runtime failure
            logger.error("Flash backup failed: %s", exc)
            return False

    def exit_auto_mode(self, persist_disable_auto: bool = False) -> bool:
        """Return the IMU to configuration mode and disable UART Auto/Auto Start."""
        self._warnings.clear()
        try:
            logger.info("Requesting IMU to exit UART Auto Mode and return to configuration state")
            # (a) Switch WINDOW = 0 and command Configuration mode (MODE_CMD = 0b10).
            self._write_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],
                    [0, 0x83, 0x02, 0x0D],
                ]
            )
            time.sleep(0.05)

            # (b) Verify MODE_STAT indicates configuration mode.
            result = self.comm.send_commands(
                [
                    [0, 0xFE, 0x00, 0x0D],
                    [4, 0x02, 0x00, 0x0D],
                ]
            )

            mode_register = None
            if len(result) < 4:
                logger.warning(
                    "MODE_CTRL read response incomplete while verifying configuration mode; assuming config mode"
                )
                self._add_warning("MODE_CTRL read response incomplete while verifying configuration mode.")
            else:
                mode_register = (result[-3] << 8) | result[-2]
                if (mode_register & 0x0400) == 0:
                    logger.info("IMU reports configuration mode (MODE_CTRL=0x%04X)", mode_register)
                else:
                    logger.warning(
                        "IMU MODE_CTRL=0x%04X indicates AUTO bit still set; continuing and clearing UART_CTRL",
                        mode_register,
                    )

            # (c) Clear UART_AUTO and AUTO_START bits so that auto mode stays disabled.
            self._write_commands(
                [
                    [0, 0xFE, 0x01, 0x0D],
                    [0, 0x88, 0x00, 0x0D],
                ]
            )
            logger.info("UART_CTRL reset to disable UART_AUTO and AUTO_START (0x88 -> 0x00)")

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

            # (d) Leave register window set to 0 for subsequent operations.
            self._write_commands([[0, 0xFE, 0x00, 0x0D]])
            return True

        except Exception as exc:  # pragma: no cover - serial runtime failure
            logger.error("Failed to exit auto mode: %s", exc)
            return False

    def configure(self, sampling_rate: float = DEFAULT_SAMPLING_RATE, tap_value: Optional[int] = None) -> bool:
        """
        Perform the complete IMU Auto Start configuration sequence.
        
        Args:
            sampling_rate: Sampling rate in SPS (samples per second). Default is 125 SPS.
            tap_value: Optional TAP value for the moving average filter. If None, uses minimum required TAP.
        
        Returns:
            True if configuration succeeded, False otherwise.
        """
        self._warnings.clear()
        try:
            self.reset_sensor()

            if not self.configure_registers(sampling_rate=sampling_rate, tap_value=tap_value):
                return False

            if not self.flash_backup():
                warning_message = (
                    "Flash backup failed during configuration. Auto Start is enabled for this session, "
                    "but the setting may not persist after power cycle."
                )
                logger.warning(warning_message)
                self._add_warning(warning_message)

            logger.info("IMU configured for UART Auto Start mode")
            logger.info(
                "After power cycle or reset, the IMU will automatically begin outputting sampling data"
            )
            logger.warning("Please restart or power cycle the sensor to activate Auto Mode.")
            logger.info("Configuration tool by %s at %s", AUTHOR, ORGANIZATION)
            return True

        except Exception as exc:  # pragma: no cover
            logger.error("Configuration failed: %s", exc)
            return False

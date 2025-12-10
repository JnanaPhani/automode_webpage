#!/usr/bin/env python3
"""
Raw Vibration Data Collection and Parsing Script

This script collects raw vibration data from the M-A542VR1 sensor
in auto-start mode, saves it as comma-separated hex values, and
simultaneously parses the data according to the datasheet.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import argparse
import csv
import logging
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from sensor_comm import SensorCommunication
except ImportError:
    print("Error: Could not import sensor_comm module")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Parsing Functions (from datasheet and DISPLACEMENT_PARSING_GUIDE.md)
# ============================================================================

def to_int8(b1: int) -> int:
    """Convert 1 byte to 8-bit signed integer."""
    return (0x80 & b1) * -1 + (0x7F & b1)


def to_int16(b1: int, b2: int) -> int:
    """Convert 2 bytes to 16-bit signed integer."""
    num = b1 * 2**8 + b2
    return (0x8000 & num) * -1 + (0x7FFF & num)


def to_uint16(b1: int, b2: int) -> int:
    """Convert 2 bytes to 16-bit unsigned integer."""
    return b1 * 2**8 + b2


def to_dec24(b1: int, b2: int, b3: int) -> float:
    """
    Convert 3 bytes to 24-bit signed decimal.
    
    Returns value in meters (m).
    Multiply by 1000 to convert to millimeters (mm).
    
    Bit format (from datasheet Section 6.11 and 6.12):
    - bit 23: sign
    - bit 22: integer part
    - bits 21-0: decimal part (22 bits)
    """
    # Extract top 2 bits from first byte
    msb2 = (b1 & 0x00C0) >> 6
    # Combine decimal part (lower 6 bits of b1 + all of b2 and b3)
    dec = ((b1 & 0x3F) << 16) + (b2 << 8) + b3
    # Combine: sign*integer + decimal/2^22
    return (msb2 & 0b10) * -1 + (msb2 & 0b01) + dec / 2**22


class RawVibrationDataCollector:
    """Collect, parse and save raw vibration data from sensor."""
    
    def __init__(self, port: str, baud: int = 460800, output_base_dir: str = ".", 
                 output_type: str = "displacement"):
        """
        Initialize data collector.
        
        Args:
            port: Serial port path
            baud: Baud rate (460800 or 921600)
            output_base_dir: Base directory for output files
            output_type: "displacement" or "velocity"
        """
        self.port = port
        self.baud = baud
        self.output_base_dir = Path(output_base_dir)
        self.output_type = output_type.lower()
        
        # Determine packet size based on baud rate
        if baud == 460800:
            self.packet_size = 13
        elif baud == 921600:
            self.packet_size = 19
        else:
            raise ValueError(f"Unsupported baud rate: {baud}. Use 460800 or 921600")
        
        self.comm: Optional[SensorCommunication] = None
        self.raw_file = None
        self.parsed_file = None
        self.parsed_writer = None
        self.raw_packet_count = 0
        self.parsed_packet_count = 0
        self.error_count = 0
        
        # Extract port number from port string (e.g., "COM4" -> "4", "/dev/ttyUSB0" -> "0")
        port_num = self._extract_port_number(port)
        self.port_number = port_num
    
    def _extract_port_number(self, port: str) -> str:
        """Extract port number from port string."""
        # For Windows COM ports: COM3 -> 3
        if port.upper().startswith('COM'):
            return port[3:]
        # For Linux /dev/ttyUSB0 -> 0
        elif 'USB' in port.upper():
            parts = port.split('USB')
            if len(parts) > 1:
                return parts[-1]
        # For /dev/ttyACM0 -> 0
        elif 'ACM' in port.upper():
            parts = port.split('ACM')
            if len(parts) > 1:
                return parts[-1]
        # Fallback: use last part of path
        return Path(port).stem.split('tty')[-1] if 'tty' in port else port.split('/')[-1]
    
    def open(self):
        """Open serial connection."""
        logger.info(f"Opening connection: {self.port} at {self.baud} baud")
        self.comm = SensorCommunication(self.port, self.baud, timeout=1.0)
        self.comm.open()
        logger.info("Connection opened successfully")
    
    def close(self):
        """Close serial connection and files."""
        if self.comm:
            self.comm.close()
            self.comm = None
        if self.raw_file:
            self.raw_file.close()
            self.raw_file = None
        if self.parsed_file:
            self.parsed_file.close()
            self.parsed_file = None
        logger.info("Connection and files closed")
    
    def setup_output_directory(self):
        """
        Setup output directory structure.
        
        Returns:
            Tuple of (raw_data_dir, parsed_data_dir)
        """
        # Create timestamp for collection directory
        collection_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        collection_dir = self.output_base_dir / f"vibration_collection_{collection_timestamp}"
        raw_data_dir = collection_dir / "raw_data"
        parsed_data_dir = collection_dir / "parsed_data"
        raw_data_dir.mkdir(parents=True, exist_ok=True)
        parsed_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Output directories: {raw_data_dir}, {parsed_data_dir}")
        return raw_data_dir, parsed_data_dir
    
    def setup_files(self, raw_data_dir: Path, parsed_data_dir: Path):
        """
        Setup raw and parsed data files for writing.
        
        Args:
            raw_data_dir: Directory for raw data files
            parsed_data_dir: Directory for parsed data files
        
        Returns:
            Tuple of (raw_path, parsed_path)
        """
        # Create filename with timestamp including milliseconds
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        milliseconds = now.microsecond // 1000
        
        # Raw data filename
        raw_filename = f"vibration_raw_Port_{self.port_number}_{timestamp}.{milliseconds:03d}.csv"
        raw_path = raw_data_dir / raw_filename
        
        # Parsed data filename
        parsed_filename = f"vibration_parsed_Port_{self.port_number}_{timestamp}.{milliseconds:03d}.csv"
        parsed_path = parsed_data_dir / parsed_filename
        
        # Open raw data file
        self.raw_file = open(raw_path, 'w')
        
        # Open parsed data file
        self.parsed_file = open(parsed_path, 'w', newline='')
        
        # Setup CSV writer for parsed data
        if self.packet_size == 13:
            if self.output_type == "displacement":
                fieldnames = [
                    'temperature', 'x_m', 'y_m', 'z_m',
                    'x_mm', 'y_mm', 'z_mm', 'count', 'flag'
                ]
            else:  # velocity
                fieldnames = [
                    'temperature', 'x_ms', 'y_ms', 'z_ms',
                    'x_mms', 'y_mms', 'z_mms', 'count', 'flag'
                ]
        else:  # 19-byte
            if self.output_type == "displacement":
                fieldnames = [
                    'temperature', 'x_m', 'y_m', 'z_m',
                    'x_mm', 'y_mm', 'z_mm', 'count',
                    'nd_flag', 'ea_flag', 'checksum'
                ]
            else:  # velocity
                fieldnames = [
                    'temperature', 'x_ms', 'y_ms', 'z_ms',
                    'x_mms', 'y_mms', 'z_mms', 'count',
                    'nd_flag', 'ea_flag', 'checksum'
                ]
        
        self.parsed_writer = csv.DictWriter(self.parsed_file, fieldnames=fieldnames)
        self.parsed_writer.writeheader()
        
        logger.info(f"Raw data file opened: {raw_path}")
        logger.info(f"Parsed data file opened: {parsed_path}")
        return raw_path, parsed_path
    
    def parse_packet(self, packet: List[int]) -> Optional[Dict]:
        """
        Parse packet according to datasheet specifications.
        
        Args:
            packet: List of packet bytes
        
        Returns:
            Dictionary with parsed data, or None if invalid
        """
        if self.packet_size == 13:
            return self._parse_13byte_packet(packet)
        else:
            return self._parse_19byte_packet(packet)
    
    def _parse_13byte_packet(self, packet: List[int]) -> Optional[Dict]:
        """Parse 13-byte packet at 460.8 kbps."""
        if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
            return None
        
        try:
            # Extract flags and counter from TEMP2_L (byte 2)
            flag = packet[2] & 0b11111100
            count = packet[2] & 0b11
            
            # Parse temperature (8-bit signed, format 2)
            temperature = to_int8(packet[1]) * -0.9707008 + 34.987
            
            # Parse displacement/velocity (24-bit)
            x_val = to_dec24(packet[3], packet[4], packet[5])
            y_val = to_dec24(packet[6], packet[7], packet[8])
            z_val = to_dec24(packet[9], packet[10], packet[11])
            
            if self.output_type == "displacement":
                return {
                    'temperature': temperature,
                    'x_m': x_val,
                    'y_m': y_val,
                    'z_m': z_val,
                    'x_mm': x_val * 1000.0,
                    'y_mm': y_val * 1000.0,
                    'z_mm': z_val * 1000.0,
                    'count': count,
                    'flag': flag,
                }
            else:  # velocity
                return {
                    'temperature': temperature,
                    'x_ms': x_val,
                    'y_ms': y_val,
                    'z_ms': z_val,
                    'x_mms': x_val * 1000.0,
                    'y_mms': y_val * 1000.0,
                    'z_mms': z_val * 1000.0,
                    'count': count,
                    'flag': flag,
                }
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def _parse_19byte_packet(self, packet: List[int]) -> Optional[Dict]:
        """Parse 19-byte packet at 921.6 kbps."""
        if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
            return None
        
        try:
            # Extract flags
            nd_flag = packet[1]
            ea_flag = packet[2]
            
            # Parse temperature (16-bit signed, format 1)
            temperature = to_int16(packet[3], packet[4]) * -0.0037918 + 34.987
            
            # Parse displacement/velocity (24-bit)
            x_val = to_dec24(packet[5], packet[6], packet[7])
            y_val = to_dec24(packet[8], packet[9], packet[10])
            z_val = to_dec24(packet[11], packet[12], packet[13])
            
            # Parse 16-bit counter and checksum
            count = to_uint16(packet[14], packet[15])
            checksum = to_uint16(packet[16], packet[17])
            
            if self.output_type == "displacement":
                return {
                    'temperature': temperature,
                    'x_m': x_val,
                    'y_m': y_val,
                    'z_m': z_val,
                    'x_mm': x_val * 1000.0,
                    'y_mm': y_val * 1000.0,
                    'z_mm': z_val * 1000.0,
                    'count': count,
                    'nd_flag': nd_flag,
                    'ea_flag': ea_flag,
                    'checksum': checksum,
                }
            else:  # velocity
                return {
                    'temperature': temperature,
                    'x_ms': x_val,
                    'y_ms': y_val,
                    'z_ms': z_val,
                    'x_mms': x_val * 1000.0,
                    'y_mms': y_val * 1000.0,
                    'z_mms': z_val * 1000.0,
                    'count': count,
                    'nd_flag': nd_flag,
                    'ea_flag': ea_flag,
                    'checksum': checksum,
                }
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def format_packet_as_csv(self, packet: List[int]) -> str:
        """
        Format packet bytes as comma-separated hex values.
        
        Args:
            packet: List of packet bytes
        
        Returns:
            Comma-separated hex string
        """
        # Format each byte as hex (lowercase, no 0x prefix)
        # For multi-byte values, combine them
        hex_values = []
        i = 0
        
        while i < len(packet):
            if i == 0:
                # Address byte
                hex_values.append(f"{packet[i]:02x}")
                i += 1
            elif self.packet_size == 13:
                # 13-byte packet format: ADDR, TEMP2_H, TEMP2_L, X(3), Y(3), Z(3), CR
                if i == 1:
                    hex_values.append(f"{packet[i]:02x}")  # TEMP2_H
                    i += 1
                elif i == 2:
                    hex_values.append(f"{packet[i]:02x}")  # TEMP2_L
                    i += 1
                elif i in [3, 6, 9]:
                    # Combine 3 bytes for velocity/displacement (24-bit)
                    val = (packet[i] << 16) | (packet[i+1] << 8) | packet[i+2]
                    hex_values.append(f"{val:06x}")
                    i += 3
                elif i == 12:
                    hex_values.append(f"{packet[i]:02x}")  # CR
                    i += 1
            else:
                # 19-byte packet format: ADDR, ND, EA, TEMP1_H, TEMP1_L, X(3), Y(3), Z(3), COUNT(2), CHECKSUM(2), CR
                if i == 1:
                    hex_values.append(f"{packet[i]:02x}")  # ND
                    i += 1
                elif i == 2:
                    hex_values.append(f"{packet[i]:02x}")  # EA
                    i += 1
                elif i == 3:
                    hex_values.append(f"{packet[i]:02x}")  # TEMP1_H
                    i += 1
                elif i == 4:
                    hex_values.append(f"{packet[i]:02x}")  # TEMP1_L
                    i += 1
                elif i in [5, 8, 11]:
                    # Combine 3 bytes for velocity/displacement (24-bit)
                    val = (packet[i] << 16) | (packet[i+1] << 8) | packet[i+2]
                    hex_values.append(f"{val:06x}")
                    i += 3
                elif i == 14:
                    # Combine 2 bytes for COUNT (16-bit)
                    val = (packet[i] << 8) | packet[i+1]
                    hex_values.append(f"{val:04x}")
                    i += 2
                elif i == 16:
                    # Combine 2 bytes for CHECKSUM (16-bit)
                    val = (packet[i] << 8) | packet[i+1]
                    hex_values.append(f"{val:04x}")
                    i += 2
                elif i == 18:
                    hex_values.append(f"{packet[i]:02x}")  # CR
                    i += 1
        
        return ','.join(hex_values)
    
    def collect_data(self, duration: float, wait_init: float = 2.0):
        """
        Collect raw vibration data for specified duration.
        
        Args:
            duration: Collection duration in seconds
            wait_init: Wait time for sensor initialization (default 2.0s)
        """
        if not self.comm or not self.comm.is_open():
            raise RuntimeError("Connection not open")
        
        if not self.raw_file:
            raw_data_dir, parsed_data_dir = self.setup_output_directory()
            self.setup_files(raw_data_dir, parsed_data_dir)
        
        logger.info(f"Starting data collection for {duration} seconds...")
        logger.info(f"Waiting {wait_init} seconds for sensor initialization...")
        time.sleep(wait_init)
        
        buffer = deque()
        start_time = time.time()
        last_log_time = start_time
        
        logger.info("Collecting data...")
        logger.info("Press Ctrl+C to stop early")
        
        try:
            while time.time() - start_time < duration:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Read available bytes
                if self.comm.connection.in_waiting > 0:
                    new_data = self.comm.connection.read(self.comm.connection.in_waiting)
                    buffer.extend(new_data)
                
                # Process complete packets
                while len(buffer) >= self.packet_size:
                    # Find packet start (0x80)
                    if buffer[0] != 0x80:
                        buffer.popleft()
                        self.error_count += 1
                        continue
                    
                    # Extract packet
                    if len(buffer) >= self.packet_size:
                        packet = [buffer.popleft() for _ in range(self.packet_size)]
                        
                        # Verify packet end
                        if packet[-1] == 0x0D:
                            # Format and save raw packet data
                            csv_line = self.format_packet_as_csv(packet)
                            self.raw_file.write(f"{csv_line}\n")
                            self.raw_file.flush()
                            self.raw_packet_count += 1
                            
                            # Parse and save parsed data immediately
                            parsed_data = self.parse_packet(packet)
                            if parsed_data:
                                self.parsed_writer.writerow(parsed_data)
                                self.parsed_file.flush()
                                self.parsed_packet_count += 1
                            else:
                                # Parsing failed but raw data saved
                                pass
                            
                            # Log progress every second
                            if current_time - last_log_time >= 1.0:
                                rate = self.raw_packet_count / elapsed if elapsed > 0 else 0
                                logger.info(
                                    f"Elapsed: {elapsed:.1f}s | "
                                    f"Raw: {self.raw_packet_count} | "
                                    f"Parsed: {self.parsed_packet_count} | "
                                    f"Rate: {rate:.1f} pkt/s | "
                                    f"Errors: {self.error_count}"
                                )
                                last_log_time = current_time
                        else:
                            # Packet corruption
                            self.error_count += 1
                    else:
                        break
                
                # Small delay to prevent CPU spinning
                time.sleep(0.001)
        
        except KeyboardInterrupt:
            logger.info("\nCollection interrupted by user")
        
        total_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("Collection Summary:")
        logger.info(f"  Total time: {total_time:.2f} seconds")
        logger.info(f"  Raw packets saved: {self.raw_packet_count}")
        logger.info(f"  Parsed packets saved: {self.parsed_packet_count}")
        logger.info(f"  Errors: {self.error_count}")
        if total_time > 0:
            logger.info(f"  Average rate: {self.raw_packet_count/total_time:.2f} packets/second")
        logger.info("="*60)


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Collect and parse raw vibration data from M-A542VR1 sensor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect and parse displacement data for 60 seconds (default)
  python collect_raw_vibration_data.py COM4 --duration 60
  
  # Collect and parse velocity data
  python collect_raw_vibration_data.py COM4 --duration 60 --output-type velocity
  
  # Collect data at 921.6 kbps for 30 seconds
  python collect_raw_vibration_data.py /dev/ttyUSB0 --baud 921600 --duration 30
  
  # Collect data with custom output directory
  python collect_raw_vibration_data.py COM4 --duration 120 --output-dir ./my_data
        """
    )
    
    parser.add_argument(
        'port',
        help='Serial port path (e.g., COM4, /dev/ttyUSB0)'
    )
    
    parser.add_argument(
        '--baud',
        type=int,
        default=460800,
        choices=[460800, 921600],
        help='Baud rate (default: 460800)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=10.0,
        help='Collection duration in seconds (default: 10.0)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Base output directory (default: current directory)'
    )
    
    parser.add_argument(
        '--output-type',
        type=str,
        default='displacement',
        choices=['displacement', 'velocity'],
        help='Output type: displacement or velocity (default: displacement)'
    )
    
    parser.add_argument(
        '--wait-init',
        type=float,
        default=2.0,
        help='Wait time for sensor initialization in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create collector
    collector = RawVibrationDataCollector(
        port=args.port,
        baud=args.baud,
        output_base_dir=args.output_dir,
        output_type=args.output_type
    )
    
    try:
        # Open connection
        collector.open()
        
        # Collect data (files are set up in collect_data)
        collector.collect_data(
            duration=args.duration,
            wait_init=args.wait_init
        )
        
        logger.info(f"\nData collection complete.")
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        collector.close()


if __name__ == "__main__":
    main()


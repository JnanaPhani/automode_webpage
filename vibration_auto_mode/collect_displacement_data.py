#!/usr/bin/env python3
"""
Displacement Data Collection and CSV Export Script

This script collects displacement data from the M-A542VR1 vibration sensor
in auto-start mode, parses the data, and saves it to CSV files.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import argparse
# import csv  # COMMENTED OUT - No CSV file
import logging
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import List, Optional
# from typing import Dict  # COMMENTED OUT - No parsing

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
# Parsing Functions (from DISPLACEMENT_PARSING_GUIDE.md)
# ============================================================================
# PARSING FUNCTIONS COMMENTED OUT - ONLY RAW DATA COLLECTION ENABLED

# def to_int8(b1: int) -> int:
#     """Convert 1 byte to 8-bit signed integer."""
#     return (0x80 & b1) * -1 + (0x7F & b1)
#
#
# def to_int16(b1: int, b2: int) -> int:
#     """Convert 2 bytes to 16-bit signed integer."""
#     num = b1 * 2**8 + b2
#     return (0x8000 & num) * -1 + (0x7FFF & num)
#
#
# def to_uint16(b1: int, b2: int) -> int:
#     """Convert 2 bytes to 16-bit unsigned integer."""
#     return b1 * 2**8 + b2
#
#
# def to_dec24(b1: int, b2: int, b3: int) -> float:
#     """
#     Convert 3 bytes to 24-bit signed decimal.
#     
#     Returns value in meters (m).
#     Multiply by 1000 to convert to millimeters (mm).
#     
#     Bit format:
#     - bit 23: sign
#     - bit 22: integer part
#     - bits 21-0: decimal part (22 bits)
#     """
#     # Extract top 2 bits from first byte
#     msb2 = (b1 & 0x00C0) >> 6
#     # Combine decimal part (lower 6 bits of b1 + all of b2 and b3)
#     dec = ((b1 & 0x3F) << 16) + (b2 << 8) + b3
#     # Combine: sign*integer + decimal/2^22
#     return (msb2 & 0b10) * -1 + (msb2 & 0b01) + dec / 2**22
#
#
# def parse_displacement_460k(packet: List[int]) -> Optional[Dict]:
#     """
#     Parse 13-byte displacement packet at 460.8 kbps.
#     
#     Args:
#         packet: List of 13 bytes starting with 0x80
#     
#     Returns:
#         Dictionary with parsed displacement data, or None if invalid
#     """
#     if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
#         return None
#     
#     try:
#         # Extract flags and counter from TEMP2_L
#         flag = packet[2] & 0b11111100
#         count = packet[2] & 0b11
#         
#         # Parse temperature (8-bit signed)
#         temperature = to_int8(packet[1]) * -0.9707008 + 34.987
#         
#         # Parse displacement (24-bit, returns meters)
#         x_m = to_dec24(packet[3], packet[4], packet[5])
#         y_m = to_dec24(packet[6], packet[7], packet[8])
#         z_m = to_dec24(packet[9], packet[10], packet[11])
#         
#         # Convert to millimeters
#         return {
#             'temperature': temperature,
#             'x_m': x_m,
#             'y_m': y_m,
#             'z_m': z_m,
#             'x_mm': x_m * 1000.0,
#             'y_mm': y_m * 1000.0,
#             'z_mm': z_m * 1000.0,
#             'count': count,
#             'flag': flag,
#         }
#     except Exception as e:
#         logger.debug(f"Parse error: {e}")
#         return None
#
#
# def parse_displacement_921k(packet: List[int]) -> Optional[Dict]:
#     """
#     Parse 19-byte displacement packet at 921.6 kbps.
#     
#     Args:
#         packet: List of 19 bytes starting with 0x80
#     
#     Returns:
#         Dictionary with parsed displacement data, or None if invalid
#     """
#     if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
#         return None
#     
#     try:
#         # Extract flags
#         nd_flag = packet[1]
#         ea_flag = packet[2]
#         
#         # Parse temperature (16-bit signed)
#         temperature = to_int16(packet[3], packet[4]) * -0.0037918 + 34.987
#         
#         # Parse displacement (24-bit, returns meters)
#         x_m = to_dec24(packet[5], packet[6], packet[7])
#         y_m = to_dec24(packet[8], packet[9], packet[10])
#         z_m = to_dec24(packet[11], packet[12], packet[13])
#         
#         # Parse counter and checksum
#         count = to_uint16(packet[14], packet[15])
#         checksum = to_uint16(packet[16], packet[17])
#         
#         # Convert to millimeters
#         return {
#             'temperature': temperature,
#             'x_m': x_m,
#             'y_m': y_m,
#             'z_m': z_m,
#             'x_mm': x_m * 1000.0,
#             'y_mm': y_m * 1000.0,
#             'z_mm': z_m * 1000.0,
#             'count': count,
#             'nd_flag': nd_flag,
#             'ea_flag': ea_flag,
#             'checksum': checksum,
#         }
#     except Exception as e:
#         logger.debug(f"Parse error: {e}")
#         return None
#
#
# def verify_checksum(packet: List[int]) -> bool:
#     """Verify packet checksum (19-byte packets only)."""
#     if len(packet) != 19:
#         return False
#     
#     # Calculate checksum from bytes after address (byte 1) to before checksum (byte 15)
#     calculated = 0
#     for byte in packet[1:16]:
#         calculated = (calculated + byte) & 0xFFFF
#     
#     received_checksum = to_uint16(packet[16], packet[17])
#     return calculated == received_checksum


# ============================================================================
# Data Collection Class
# ============================================================================

class DisplacementDataCollector:
    """Collect and save displacement data from sensor."""
    
    def __init__(self, port: str, baud: int = 460800, output_dir: str = "data"):
        """
        Initialize data collector.
        
        Args:
            port: Serial port path
            baud: Baud rate (460800 or 921600)
            output_dir: Directory to save CSV files
        """
        self.port = port
        self.baud = baud
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine packet size based on baud rate
        if baud == 460800:
            self.packet_size = 13
            # self.parse_func = parse_displacement_460k  # COMMENTED OUT
        elif baud == 921600:
            self.packet_size = 19
            # self.parse_func = parse_displacement_921k  # COMMENTED OUT
        else:
            raise ValueError(f"Unsupported baud rate: {baud}. Use 460800 or 921600")
        
        self.comm: Optional[SensorCommunication] = None
        # self.csv_file = None  # COMMENTED OUT - No CSV file
        # self.csv_writer = None  # COMMENTED OUT - No CSV writer
        self.raw_file = None
        # self.packet_count = 0  # COMMENTED OUT - No parsed packets
        self.raw_packet_count = 0  # Total raw packets saved
        self.error_count = 0
        
    def open(self):
        """Open serial connection."""
        logger.info(f"Opening connection: {self.port} at {self.baud} baud")
        self.comm = SensorCommunication(self.port, self.baud, timeout=1.0)
        self.comm.open()
        logger.info("Connection opened successfully")
    
    def close(self):
        """Close serial connection and raw data file."""
        if self.comm:
            self.comm.close()
            self.comm = None
        # if self.csv_file:  # COMMENTED OUT
        #     self.csv_file.close()
        #     self.csv_file = None
        if self.raw_file:
            self.raw_file.close()
            self.raw_file = None
        logger.info("Connection and file closed")
    
    def setup_files(self, filename: Optional[str] = None):
        """
        Setup raw data file for writing.
        
        Args:
            filename: Optional filename. If None, generates timestamp-based name.
        
        Returns:
            Path to raw data file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_filename = f"displacement_data_{timestamp}.txt"
        else:
            # Add .txt extension if not provided
            raw_filename = filename if filename.endswith('.txt') else f"{filename}.txt"
        
        raw_path = self.output_dir / raw_filename
        
        # Open raw data file (hex-encoded text format, no headers)
        self.raw_file = open(raw_path, 'w')
        
        # CSV file setup COMMENTED OUT
        # csv_path = self.output_dir / f"{base_name}_parsed.csv"
        # self.csv_file = open(csv_path, 'w', newline='')
        # if self.packet_size == 13:
        #     fieldnames = [
        #         'timestamp', 'elapsed_time', 'temperature', 
        #         'x_m', 'y_m', 'z_m', 'x_mm', 'y_mm', 'z_mm', 
        #         'count', 'flag'
        #     ]
        # else:  # 19-byte packet
        #     fieldnames = [
        #         'timestamp', 'elapsed_time', 'temperature',
        #         'x_m', 'y_m', 'z_m', 'x_mm', 'y_mm', 'z_mm',
        #         'count', 'nd_flag', 'ea_flag', 'checksum'
        #     ]
        # self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        # self.csv_writer.writeheader()
        
        logger.info(f"Raw data file opened: {raw_path}")
        return raw_path
    
    def collect_data(self, duration: float, wait_init: float = 2.0):
        """
        Collect displacement data for specified duration.
        
        Args:
            duration: Collection duration in seconds
            wait_init: Wait time for sensor initialization (default 2.0s)
        """
        if not self.comm or not self.comm.is_open():
            raise RuntimeError("Connection not open")
        
        if not self.raw_file:
            self.setup_files()
        
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
                            # Save raw packet data (only hex bytes, no metadata)
                            hex_bytes = ' '.join(f'{b:02X}' for b in packet)
                            self.raw_file.write(f"{hex_bytes}\n")
                            self.raw_file.flush()
                            self.raw_packet_count += 1
                            
                            # PARSING LOGIC COMMENTED OUT
                            # timestamp = datetime.now().isoformat()
                            # data = self.parse_func(packet)
                            # if data:
                            #     data['timestamp'] = timestamp
                            #     data['elapsed_time'] = elapsed
                            #     self.csv_writer.writerow(data)
                            #     self.csv_file.flush()
                            #     self.packet_count += 1
                            
                            # Log progress every second
                            if current_time - last_log_time >= 1.0:
                                rate = self.raw_packet_count / elapsed if elapsed > 0 else 0
                                logger.info(
                                    f"Elapsed: {elapsed:.1f}s | "
                                    f"Packets: {self.raw_packet_count} | "
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
        description="Collect raw displacement data from M-A542VR1 sensor and save to file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect data for 60 seconds at default baud rate (460800)
  python collect_displacement_data.py COM3 --duration 60
  
  # Collect data at 921.6 kbps for 30 seconds
  python collect_displacement_data.py /dev/ttyUSB0 --baud 921600 --duration 30
  
  # Collect data with custom output directory
  python collect_displacement_data.py COM3 --duration 120 --output-dir ./my_data
        """
    )
    
    parser.add_argument(
        'port',
        help='Serial port path (e.g., COM3, /dev/ttyUSB0)'
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
        default='data',
        help='Output directory for CSV files (default: data)'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='Output filename (default: auto-generated with timestamp). '
             'Will create: <name>.txt'
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
    collector = DisplacementDataCollector(
        port=args.port,
        baud=args.baud,
        output_dir=args.output_dir
    )
    
    try:
        # Open connection
        collector.open()
        
        # Setup raw data file
        raw_path = collector.setup_files(args.output_file)
        logger.info(f"Raw data will be saved to: {raw_path}")
        
        # Collect data
        collector.collect_data(
            duration=args.duration,
            wait_init=args.wait_init
        )
        
        logger.info(f"\nData collection complete.")
        logger.info(f"  Raw data file: {raw_path}")
        
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


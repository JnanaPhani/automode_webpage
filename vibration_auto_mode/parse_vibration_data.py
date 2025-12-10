#!/usr/bin/env python3
"""
Vibration Data Parser

This script parses raw vibration data CSV files according to the M-A542VR1
datasheet specifications and saves parsed data to CSV files.

Author: Jnana Phani A (https://phani.zenithtek.in)
Organization: Zenith Tek (https://zenithtek.in)
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

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


def parse_csv_line_to_bytes(line: str, packet_size: int = 13) -> Optional[List[int]]:
    """
    Parse a CSV line back into byte list.
    
    Args:
        line: CSV line with comma-separated hex values
        packet_size: Expected packet size (13 or 19 bytes)
    
    Returns:
        List of bytes, or None if invalid
    """
    try:
        parts = line.strip().split(',')
        if not parts:
            return None
        
        bytes_list = []
        i = 0
        
        while i < len(parts) and len(bytes_list) < packet_size:
            hex_val = parts[i].strip()
            
            if len(hex_val) == 2:
                # Single byte (2 hex digits)
                bytes_list.append(int(hex_val, 16))
                i += 1
            elif len(hex_val) == 6:
                # 24-bit value (6 hex digits) - split into 3 bytes
                val = int(hex_val, 16)
                bytes_list.append((val >> 16) & 0xFF)  # High byte
                bytes_list.append((val >> 8) & 0xFF)    # Middle byte
                bytes_list.append(val & 0xFF)           # Low byte
                i += 1
            elif len(hex_val) == 4:
                # 16-bit value (4 hex digits) - split into 2 bytes
                val = int(hex_val, 16)
                bytes_list.append((val >> 8) & 0xFF)   # High byte
                bytes_list.append(val & 0xFF)            # Low byte
                i += 1
            else:
                # Invalid format
                return None
        
        return bytes_list if len(bytes_list) == packet_size else None
        
    except (ValueError, IndexError) as e:
        logger.debug(f"Error parsing line: {e}")
        return None


def parse_packet_13byte(packet: List[int], output_type: str = "displacement") -> Optional[Dict]:
    """
    Parse 13-byte packet at 460.8 kbps.
    
    Args:
        packet: List of 13 bytes starting with 0x80
        output_type: "displacement" or "velocity"
    
    Returns:
        Dictionary with parsed data, or None if invalid
    """
    if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
        return None
    
    try:
        # Extract flags and counter from TEMP2_L (byte 2)
        # Bits 7-2: flags, bits 1-0: 2-bit counter
        flag = packet[2] & 0b11111100
        count = packet[2] & 0b11
        
        # Parse temperature (8-bit signed, format 2)
        # From datasheet Table 1.3: Scale Factor = -0.9707008 °C/LSB, offset = 34.987 °C
        temperature = to_int8(packet[1]) * -0.9707008 + 34.987
        
        # Parse displacement/velocity (24-bit, returns meters or m/s)
        x_val = to_dec24(packet[3], packet[4], packet[5])
        y_val = to_dec24(packet[6], packet[7], packet[8])
        z_val = to_dec24(packet[9], packet[10], packet[11])
        
        # Convert to millimeters or mm/s
        if output_type.lower() == "displacement":
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


def parse_packet_19byte(packet: List[int], output_type: str = "displacement") -> Optional[Dict]:
    """
    Parse 19-byte packet at 921.6 kbps.
    
    Args:
        packet: List of 19 bytes starting with 0x80
        output_type: "displacement" or "velocity"
    
    Returns:
        Dictionary with parsed data, or None if invalid
    """
    if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
        return None
    
    try:
        # Extract flags
        nd_flag = packet[1]  # New Data flags
        ea_flag = packet[2]  # Error/Status flags
        
        # Parse temperature (16-bit signed, format 1)
        # From datasheet Table 1.3: Scale Factor = -0.0037918 °C/LSB, offset = 34.987 °C
        temperature = to_int16(packet[3], packet[4]) * -0.0037918 + 34.987
        
        # Parse displacement/velocity (24-bit, returns meters or m/s)
        x_val = to_dec24(packet[5], packet[6], packet[7])
        y_val = to_dec24(packet[8], packet[9], packet[10])
        z_val = to_dec24(packet[11], packet[12], packet[13])
        
        # Parse 16-bit counter
        count = to_uint16(packet[14], packet[15])
        
        # Parse checksum
        checksum = to_uint16(packet[16], packet[17])
        
        # Convert to millimeters or mm/s
        if output_type.lower() == "displacement":
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


# ============================================================================
# Main Parser Class
# ============================================================================

class VibrationDataParser:
    """Parse raw vibration data CSV files."""
    
    def __init__(self, input_file: str, output_file: Optional[str] = None, 
                 packet_size: int = 13, output_type: str = "displacement"):
        """
        Initialize parser.
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file (auto-generated if None)
            packet_size: Packet size (13 or 19 bytes)
            output_type: "displacement" or "velocity"
        """
        self.input_file = Path(input_file)
        self.packet_size = packet_size
        self.output_type = output_type.lower()
        
        if output_file:
            self.output_file = Path(output_file)
        else:
            # Generate output filename
            stem = self.input_file.stem.replace('_raw', '_parsed')
            self.output_file = self.input_file.parent / f"{stem}.csv"
        
        # Select parser function
        if packet_size == 13:
            self.parse_func = parse_packet_13byte
        elif packet_size == 19:
            self.parse_func = parse_packet_19byte
        else:
            raise ValueError(f"Invalid packet size: {packet_size}. Use 13 or 19")
    
    def parse_file(self):
        """Parse the input CSV file and save to output CSV."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        logger.info(f"Parsing file: {self.input_file}")
        logger.info(f"Output file: {self.output_file}")
        logger.info(f"Packet size: {self.packet_size} bytes")
        logger.info(f"Output type: {self.output_type}")
        
        parsed_count = 0
        error_count = 0
        
        # Determine fieldnames based on packet size and output type
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
        
        with open(self.input_file, 'r') as infile, \
             open(self.output_file, 'w', newline='') as outfile:
            
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for line_num, line in enumerate(infile, 1):
                # Parse CSV line to bytes
                packet = parse_csv_line_to_bytes(line, self.packet_size)
                
                if packet is None:
                    error_count += 1
                    if error_count <= 10:  # Log first 10 errors
                        logger.warning(f"Line {line_num}: Failed to parse")
                    continue
                
                # Parse packet
                data = self.parse_func(packet, self.output_type)
                
                if data is None:
                    error_count += 1
                    if error_count <= 10:  # Log first 10 errors
                        logger.warning(f"Line {line_num}: Failed to parse packet")
                    continue
                
                # Write parsed data
                writer.writerow(data)
                parsed_count += 1
                
                # Progress update every 10000 lines
                if parsed_count % 10000 == 0:
                    logger.info(f"Parsed {parsed_count} packets...")
        
        logger.info("\n" + "="*60)
        logger.info("Parsing Summary:")
        logger.info(f"  Parsed packets: {parsed_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Output file: {self.output_file}")
        logger.info("="*60)


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Parse raw vibration data CSV files according to M-A542VR1 datasheet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse displacement data (13-byte packets, default)
  python parse_vibration_data.py vibration_raw_Port_3_2025-12-03_12-20-23.304.csv
  
  # Parse velocity data
  python parse_vibration_data.py input.csv --output-type velocity
  
  # Parse 19-byte packets
  python parse_vibration_data.py input.csv --packet-size 19
  
  # Specify output file
  python parse_vibration_data.py input.csv --output parsed_data.csv
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input CSV file with raw vibration data'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output CSV file (default: auto-generated from input filename)'
    )
    
    parser.add_argument(
        '--packet-size',
        type=int,
        default=13,
        choices=[13, 19],
        help='Packet size in bytes (default: 13)'
    )
    
    parser.add_argument(
        '--output-type',
        type=str,
        default='displacement',
        choices=['displacement', 'velocity'],
        help='Output type: displacement or velocity (default: displacement)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        parser_obj = VibrationDataParser(
            input_file=args.input_file,
            output_file=args.output,
            packet_size=args.packet_size,
            output_type=args.output_type
        )
        
        parser_obj.parse_file()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()










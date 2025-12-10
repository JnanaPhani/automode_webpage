# Displacement Data Parsing Guide

## Overview

This guide explains how to parse displacement output data from the M-A542VR1 vibration sensor when configured for auto-start with displacement output.

## Data Format Specification

### Displacement Data Format (from datasheet Section 6.12)

- **Data Type**: 24-bit two's complement
- **Unit**: Meters (m)
- **Scale Factor**: 2^-22 m/LSB = 2.38 × 10^-4 mm/LSB
- **Output Range**: -200 to +200 mm
- **Sampling Rate**: 300 Sps (fixed for RAW displacement)

### Bit Layout (24-bit format)

- **Bit 23**: Sign bit
- **Bit 22**: Integer part
- **Bits 21-0**: Decimal part (22 bits)

## Packet Structure

The packet structure depends on the baud rate and BURST_CTRL register settings:

### For 460.8 kbps (13-byte packet)

Default BURST_CTRL = 0x4700 (TEMP, Displacement-XYZ)

```
Byte  Index  Field Name          Description
----  -----  ------------------  ----------------------------------------
0     0x80   ADDRESS             Always 0x80
1     0x??   TEMP2_H             Temperature high byte (16-bit format)
2     0x??   TEMP2_L             Temperature low byte + flags
3     0x??   XDISP_HIGH_L        X displacement high byte (LSB part)
4     0x??   XDISP_LOW_H         X displacement low byte (MSB part)
5     0x??   XDISP_LOW_L         X displacement low byte (LSB part)
6     0x??   YDISP_HIGH_L        Y displacement high byte (LSB part)
7     0x??   YDISP_LOW_H         Y displacement low byte (MSB part)
8     0x??   YDISP_LOW_L         Y displacement low byte (LSB part)
9     0x??   ZDISP_HIGH_L        Z displacement high byte (LSB part)
10    0x??   ZDISP_LOW_H         Z displacement low byte (MSB part)
11    0x??   ZDISP_LOW_L         Z displacement low byte (LSB part)
12    0x0D   CR                  Carriage return delimiter
```

### For 921.6 kbps (19-byte packet)

Default BURST_CTRL = 0xC703 (FLAG, TEMP, Displacement-XYZ, COUNT, CHECKSUM)

```
Byte  Index  Field Name          Description
----  -----  ------------------  ----------------------------------------
0     0x80   ADDRESS             Always 0x80
1     0x??   ND                  New Data flags (high byte)
2     0x??   EA                  Error/Status flags (low byte)
3     0x??   TEMP1_H             Temperature high byte (16-bit format)
4     0x??   TEMP1_L             Temperature low byte
5     0x??   XDISP_HIGH_L        X displacement high byte (LSB part)
6     0x??   XDISP_LOW_H         X displacement low byte (MSB part)
7     0x??   XDISP_LOW_L         X displacement low byte (LSB part)
8     0x??   YDISP_HIGH_L        Y displacement high byte (LSB part)
9     0x??   YDISP_LOW_H         Y displacement low byte (MSB part)
10    0x??   YDISP_LOW_L         Y displacement low byte (LSB part)
11    0x??   ZDISP_HIGH_L        Z displacement high byte (LSB part)
12    0x??   ZDISP_LOW_H         Z displacement low byte (MSB part)
13    0x??   ZDISP_LOW_L         Z displacement low byte (LSB part)
14    0x??   COUNT_H             16-bit counter high byte
15    0x??   COUNT_L             16-bit counter low byte
16    0x??   CHECKSUM_H          Checksum high byte
17    0x??   CHECKSUM_L          Checksum low byte
18    0x0D   CR                  Carriage return delimiter
```

## Parsing Functions

### Python Implementation

Based on the existing `to_dec24` function from `convert.py`:

```python
def to_dec24(b1: int, b2: int, b3: int) -> float:
    """
    3 bytes -> 24-bit signed decimal conversion
    Specification:
      - 24-bit, two's complement
        - bit 23: sign bit (also acts as integer part)
        - bit 22: integer part
        - bit 21-0: decimal part (22 bits)
    
    Returns value in meters (m)
    To convert to mm: multiply by 1000
    """
    # Extract top 2 bits from first byte
    msb2 = (b1 & 0x00C0) >> 6
    # Combine decimal part
    dec = ((b1 & 0x3F) << 16) + (b2 << 8) + b3
    # Combine sign and integer
    return (msb2 & 0b10) * -1 + (msb2 & 0b01) + dec / 2**22


def parse_displacement_packet_460k(packet: List[int]) -> dict:
    """
    Parse 13-byte displacement packet at 460.8 kbps.
    
    Args:
        packet: List of 13 bytes starting with 0x80
    
    Returns:
        Dictionary with parsed data
    """
    if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
        raise ValueError("Invalid packet format")
    
    # Extract flags from TEMP2_L (bits 7-2)
    flag = packet[2] & 0b11111100
    # Extract 2-bit counter from TEMP2_L (bits 1-0)
    count = packet[2] & 0b11
    
    # Parse temperature (8-bit signed, format 2)
    temperature = to_int8(packet[1]) * -0.9707008 + 34.987
    
    # Parse displacement (24-bit, returns in meters)
    x_m = to_dec24(packet[3], packet[4], packet[5])
    y_m = to_dec24(packet[6], packet[7], packet[8])
    z_m = to_dec24(packet[9], packet[10], packet[11])
    
    # Convert to mm
    x_mm = x_m * 1000.0
    y_mm = y_m * 1000.0
    z_mm = z_m * 1000.0
    
    return {
        'temperature': temperature,
        'x_m': x_m,
        'y_m': y_m,
        'z_m': z_m,
        'x_mm': x_mm,
        'y_mm': y_mm,
        'z_mm': z_mm,
        'count': count,
        'flag': flag,
    }


def parse_displacement_packet_921k(packet: List[int]) -> dict:
    """
    Parse 19-byte displacement packet at 921.6 kbps.
    
    Args:
        packet: List of 19 bytes starting with 0x80
    
    Returns:
        Dictionary with parsed data
    """
    if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
        raise ValueError("Invalid packet format")
    
    # Extract flags
    nd_flag = packet[1]  # New Data flags
    ea_flag = packet[2]  # Error/Status flags
    
    # Parse temperature (16-bit signed, format 1)
    temperature = to_int16(packet[3], packet[4]) * -0.0037918 + 34.987
    
    # Parse displacement (24-bit, returns in meters)
    x_m = to_dec24(packet[5], packet[6], packet[7])
    y_m = to_dec24(packet[8], packet[9], packet[10])
    z_m = to_dec24(packet[11], packet[12], packet[13])
    
    # Convert to mm
    x_mm = x_m * 1000.0
    y_mm = y_m * 1000.0
    z_mm = z_m * 1000.0
    
    # Parse 16-bit counter
    count = to_uint16(packet[14], packet[15])
    
    # Parse checksum
    checksum = to_uint16(packet[16], packet[17])
    
    return {
        'temperature': temperature,
        'x_m': x_m,
        'y_m': y_m,
        'z_m': z_m,
        'x_mm': x_mm,
        'y_mm': y_mm,
        'z_mm': z_mm,
        'count': count,
        'nd_flag': nd_flag,
        'ea_flag': ea_flag,
        'checksum': checksum,
    }


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
```

### Example Usage

```python
from serial import Serial

# Open serial connection
ser = Serial('/dev/ttyUSB0', 460800, timeout=1.0)

# Read packet
packet = list(ser.read(13))

# Verify packet structure
if packet[0] == 0x80 and packet[12] == 0x0D:
    # Parse displacement data
    data = parse_displacement_packet_460k(packet)
    
    print(f"Temperature: {data['temperature']:.2f} °C")
    print(f"X Displacement: {data['x_mm']:.4f} mm")
    print(f"Y Displacement: {data['y_mm']:.4f} mm")
    print(f"Z Displacement: {data['z_mm']:.4f} mm")
    print(f"Count: {data['count']}")
else:
    print("Invalid packet")
```

## Continuous Reading Loop

For auto-start mode, the sensor continuously sends packets. Here's how to handle the stream:

```python
import serial
from collections import deque

def read_displacement_stream(port: str, baud: int = 460800, packet_size: int = 13):
    """
    Continuously read and parse displacement packets from sensor.
    
    Args:
        port: Serial port path
        baud: Baud rate (460800 or 921600)
        packet_size: Packet size (13 for 460.8k, 19 for 921.6k)
    """
    ser = serial.Serial(port, baud, timeout=1.0)
    buffer = deque()
    
    parse_func = parse_displacement_packet_460k if packet_size == 13 else parse_displacement_packet_921k
    
    try:
        while True:
            # Read available bytes
            new_data = ser.read(ser.in_waiting or 1)
            buffer.extend(new_data)
            
            # Look for complete packets
            while len(buffer) >= packet_size:
                # Find packet start (0x80)
                if buffer[0] != 0x80:
                    buffer.popleft()
                    continue
                
                # Check if we have a complete packet
                if len(buffer) >= packet_size:
                    packet = [buffer.popleft() for _ in range(packet_size)]
                    
                    # Verify packet end
                    if packet[-1] == 0x0D:
                        try:
                            data = parse_func(packet)
                            yield data
                        except ValueError as e:
                            print(f"Parse error: {e}")
                    else:
                        # Packet corruption, skip
                        pass
                else:
                    break
                    
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        ser.close()


# Usage
for data in read_displacement_stream('/dev/ttyUSB0', 460800):
    print(f"X: {data['x_mm']:.4f} mm, "
          f"Y: {data['y_mm']:.4f} mm, "
          f"Z: {data['z_mm']:.4f} mm")
```

## Important Notes

### 1. Transient Response Time
- **Displacement RAW**: ~1.736 seconds transient response at start
- Wait at least 2 seconds after sensor start before using data

### 2. Sampling Rate
- **Displacement RAW**: Fixed at 300 Sps (samples per second)
- Packet arrival rate: ~300 packets/second at 460.8 kbps
- Packet arrival rate: ~300 packets/second at 921.6 kbps

### 3. Value Range
- Valid displacement range: -200.0 to +200.0 mm
- Values outside this range indicate sensor saturation or error

### 4. Checksum Validation (921.6 kbps only)
The checksum is calculated as a simple 16-bit sum of data bytes (excluding address and delimiter):

```python
def verify_checksum(packet: List[int]) -> bool:
    """Verify packet checksum (19-byte packets only)."""
    if len(packet) != 19:
        return False
    
    # Calculate checksum from bytes after address (byte 1) to before checksum (byte 15)
    calculated = 0
    for byte in packet[1:16]:
        calculated = (calculated + byte) & 0xFFFF
    
    received_checksum = to_uint16(packet[16], packet[17])
    return calculated == received_checksum
```

### 5. Error Flags
Check the error flags in the packet:
- **EA flag** (bit 0): All error flag - set if any diagnostic error
- **X/Y/Z_EXI_ERR** (bits 7/6/5): Structural resonance warning
- **X/Y/Z_ALARM_ERR** (bits 4/3/2): Threshold exceeded

### 6. Temperature Conversion
- **8-bit format** (460.8 kbps, TEMP2): Scale factor = -0.9707008 °C/LSB, offset = 34.987 °C
- **16-bit format** (921.6 kbps, TEMP1): Scale factor = -0.0037918 °C/LSB, offset = 34.987 °C

## Comparison with Velocity Parsing

The parsing method is **identical** to velocity parsing. The only differences are:

1. **Units**: Displacement in mm vs Velocity in mm/s
2. **Range**: ±200 mm vs ±100 mm/s  
3. **Sampling Rate**: 300 Sps vs 3000 Sps
4. **Physical Meaning**: Displacement vs Velocity

The same `to_dec24()` function works for both!


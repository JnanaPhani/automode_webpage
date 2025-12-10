# Complete Guide: Displacement Output in Auto-Start Mode

This guide explains how to configure the M-A542VR1 vibration sensor to output displacement data in auto-start mode and how to parse the received data.

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Steps](#configuration-steps)
3. [Register Settings](#register-settings)
4. [Verification](#verification)
5. [Data Parsing](#data-parsing)
6. [Complete Python Example](#complete-python-example)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The M-A542VR1 sensor can be configured to automatically start and output displacement data on power-up. This is achieved by:

1. Setting the output physical quantity to **Displacement**
2. Enabling **UART Auto Sampling** mode
3. Enabling **Auto Start** function
4. Saving settings to non-volatile memory (flash)

Once configured, the sensor will automatically enter sampling mode and transmit displacement data after power-on or reset.

---

## Configuration Steps

### Step 1: Set Output to Displacement

The sensor must be in **Configuration Mode** to change settings.

**Register**: `SIG_CTRL [0x00(W1)]` - Signal Control Register  
**Bits [7:4]**: `OUTPUT_SEL` - Output Physical Quantity Selection

| Value | Output Type |
|-------|-------------|
| `0000` | Velocity RAW (factory default) |
| `0100` | **Displacement RAW** ← Use this |
| `0101` | Displacement RMS |
| `0110` | Displacement P-P |

**Command sequence:**
```
1. Set Window 1:    0xFE, 0x01, 0x0D
2. Set Displacement: 0x80, 0x40, 0x0D  (OUTPUT_SEL = 0100)
   Note: 0x40 = 01000000 in binary (bits [7:4] = 0100)
3. Wait ~118ms for setting to complete
4. Verify OUTPUT_STAT bit [0] returns to 0
```

### Step 2: Enable UART Auto Sampling and Auto Start

**Register**: `UART_CTRL [0x08(W1)]` - UART Control Register

| Bit | Name | Description |
|-----|------|-------------|
| [1] | `AUTO_START` | Enable automatic start on power-up |
| [0] | `UART_AUTO` | Enable UART Auto sampling mode |

**Command sequence:**
```
1. Set Window 1:           0xFE, 0x01, 0x0D
2. Enable Auto Start:      0x88, 0x03, 0x0D
   Note: 0x03 = 00000011 (both bits set)
```

### Step 3: Configure Burst Output (Optional)

**Register**: `BURST_CTRL [0x0C(W1)]` - Burst Control Register

This controls what data is included in each packet. Default factory settings work fine, but you can customize:

**For 460.8 kbps (default):**
- `BURST_CTRL = 0x4700`
- Output: TEMP (format 2), Displacement-XYZ
- Packet size: 13 bytes

**For 921.6 kbps:**
- `BURST_CTRL = 0xC703`
- Output: FLAG, TEMP (format 1), Displacement-XYZ, COUNT, CHECKSUM
- Packet size: 19 bytes

### Step 4: Save to Non-Volatile Memory

**Register**: `GLOB_CMD [0x0A(W1)]` - Global Command Register  
**Bit [3]**: `FLASH_BACKUP` - Save settings to flash

**Command sequence:**
```
1. Set Window 1:      0xFE, 0x01, 0x0D
2. Flash Backup:      0x8A, 0x08, 0x0D  (FLASH_BACKUP = 1)
3. Wait ~310ms for backup to complete
4. Verify FLASH_BU_ERR bit [0] in DIAG_STAT1 is 0
```

### Step 5: Power Cycle or Reset

After saving, power cycle the sensor or perform a software reset. The sensor will automatically:
- Complete internal initialization (~900ms)
- Enter Sampling Mode automatically
- Start transmitting displacement data

---

## Register Settings

### Summary of Register Values

| Register | Address | Window | Value | Description |
|----------|---------|--------|-------|-------------|
| `SIG_CTRL` | 0x00 | W1 | 0x40 | Displacement RAW output |
| `UART_CTRL` | 0x08 | W1 | 0x03 | Auto Start + UART Auto enabled |
| `BURST_CTRL` | 0x0C | W1 | 0x4700 (or 0xC703) | Burst output configuration |
| `GLOB_CMD` | 0x0A | W1 | 0x08 | Flash backup command |

---

## Verification

### Check Configuration Status

After configuration, verify the settings:

```python
# Read SIG_CTRL to verify OUTPUT_SEL
Window 1: 0xFE, 0x01, 0x0D
Read SIG_CTRL: 0x00, 0x00, 0x0D
Response: 0x00, [MSB], [LSB], 0x0D
# Check bits [7:4] should be 0100

# Read UART_CTRL to verify Auto Start
Read UART_CTRL: 0x08, 0x00, 0x0D
Response: 0x08, [MSB], [LSB], 0x0D
# Check bits [1:0] should be 11 (both set)
```

### Verify Auto Start Works

1. Power cycle the sensor
2. Wait ~2 seconds for initialization and transient response
3. Data packets should start arriving automatically (no commands needed)
4. Packet format: Starts with `0x80`, ends with `0x0D`

---

## Data Parsing

### Packet Structure

#### For 460.8 kbps (13-byte packet)

```
Byte  Index  Field             Description
----  -----  ----------------- ------------------------------------
0     0x80   ADDRESS           Packet identifier (always 0x80)
1     0x??   TEMP2_H           Temperature high byte
2     0x??   TEMP2_L           Temperature low + flags
3     0x??   XDISP_HIGH_L      X displacement byte 1 (24-bit format)
4     0x??   XDISP_LOW_H       X displacement byte 2
5     0x??   XDISP_LOW_L       X displacement byte 3
6     0x??   YDISP_HIGH_L      Y displacement byte 1
7     0x??   YDISP_LOW_H       Y displacement byte 2
8     0x??   YDISP_LOW_L       Y displacement byte 3
9     0x??   ZDISP_HIGH_L      Z displacement byte 1
10    0x??   ZDISP_LOW_H       Z displacement byte 2
11    0x??   ZDISP_LOW_L       Z displacement byte 3
12    0x0D   CR                Carriage return delimiter
```

#### For 921.6 kbps (19-byte packet)

```
Byte  Index  Field             Description
----  -----  ----------------- ------------------------------------
0     0x80   ADDRESS           Packet identifier
1     0x??   ND                New Data flags
2     0x??   EA                Error/Status flags
3     0x??   TEMP1_H           Temperature high byte
4     0x??   TEMP1_L           Temperature low byte
5-7   0x??   X Displacement    24-bit X displacement
8-10  0x??   Y Displacement    24-bit Y displacement
11-13 0x??   Z Displacement    24-bit Z displacement
14-15 0x??   COUNT             16-bit counter
16-17 0x??   CHECKSUM          16-bit checksum
18    0x0D   CR                Delimiter
```

### Displacement Data Format

- **Format**: 24-bit two's complement
- **Unit**: Meters (m)
- **Scale Factor**: 2^-22 m/LSB = 2.38 × 10^-4 mm/LSB
- **Range**: -200.0 to +200.0 mm
- **Bit Layout**:
  - Bit 23: Sign bit
  - Bit 22: Integer part
  - Bits 21-0: Decimal part (22 bits)

### Parsing Functions

```python
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
    
    Bit format:
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


def parse_displacement_460k(packet: list) -> dict:
    """
    Parse 13-byte displacement packet at 460.8 kbps.
    
    Args:
        packet: List of 13 bytes starting with 0x80
    
    Returns:
        Dictionary with parsed displacement data
    """
    if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
        raise ValueError("Invalid packet format")
    
    # Extract flags and counter from TEMP2_L
    flag = packet[2] & 0b11111100
    count = packet[2] & 0b11
    
    # Parse temperature (8-bit signed)
    temperature = to_int8(packet[1]) * -0.9707008 + 34.987
    
    # Parse displacement (24-bit, returns meters)
    x_m = to_dec24(packet[3], packet[4], packet[5])
    y_m = to_dec24(packet[6], packet[7], packet[8])
    z_m = to_dec24(packet[9], packet[10], packet[11])
    
    # Convert to millimeters
    return {
        'temperature': temperature,
        'x_m': x_m,
        'y_m': y_m,
        'z_m': z_m,
        'x_mm': x_m * 1000.0,
        'y_mm': y_m * 1000.0,
        'z_mm': z_m * 1000.0,
        'count': count,
        'flag': flag,
    }


def parse_displacement_921k(packet: list) -> dict:
    """
    Parse 19-byte displacement packet at 921.6 kbps.
    
    Args:
        packet: List of 19 bytes starting with 0x80
    
    Returns:
        Dictionary with parsed displacement data
    """
    if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
        raise ValueError("Invalid packet format")
    
    # Extract flags
    nd_flag = packet[1]
    ea_flag = packet[2]
    
    # Parse temperature (16-bit signed)
    temperature = to_int16(packet[3], packet[4]) * -0.0037918 + 34.987
    
    # Parse displacement (24-bit, returns meters)
    x_m = to_dec24(packet[5], packet[6], packet[7])
    y_m = to_dec24(packet[8], packet[9], packet[10])
    z_m = to_dec24(packet[11], packet[12], packet[13])
    
    # Parse counter and checksum
    count = to_uint16(packet[14], packet[15])
    checksum = to_uint16(packet[16], packet[17])
    
    # Convert to millimeters
    return {
        'temperature': temperature,
        'x_m': x_m,
        'y_m': y_m,
        'z_m': z_m,
        'x_mm': x_m * 1000.0,
        'y_mm': y_m * 1000.0,
        'z_mm': z_m * 1000.0,
        'count': count,
        'nd_flag': nd_flag,
        'ea_flag': ea_flag,
        'checksum': checksum,
    }
```

---

## Complete Python Example

Here's a complete example that configures the sensor and reads displacement data:

```python
#!/usr/bin/env python3
"""
Example: Configure M-A542VR1 for Displacement Auto-Start and Parse Data
"""

import serial
import time
from typing import List, Optional
from collections import deque


class DisplacementSensor:
    """M-A542VR1 Displacement Sensor Interface"""
    
    def __init__(self, port: str, baud: int = 460800):
        self.port = port
        self.baud = baud
        self.packet_size = 13 if baud == 460800 else 19
        self.ser: Optional[serial.Serial] = None
    
    def open(self):
        """Open serial connection."""
        self.ser = serial.Serial(self.port, self.baud, timeout=1.0)
        time.sleep(0.1)
        print(f"Opened {self.port} at {self.baud} baud")
    
    def close(self):
        """Close serial connection."""
        if self.ser:
            self.ser.close()
            self.ser = None
    
    def send_command(self, cmd: List[int], expect_response: int = 0) -> List[int]:
        """Send command and read response."""
        if not self.ser:
            raise RuntimeError("Connection not open")
        
        # Send command (skip first byte if it's response length)
        cmd_bytes = bytes(cmd) if isinstance(cmd[0], int) else bytes(cmd[1:])
        self.ser.write(cmd_bytes)
        self.ser.flush()
        
        # Read response
        if expect_response > 0:
            return list(self.ser.read(expect_response))
        return []
    
    def configure_displacement_autostart(self) -> bool:
        """Configure sensor for displacement output in auto-start mode."""
        try:
            print("Configuring sensor for displacement auto-start...")
            
            # Step 1: Set Window 1
            self.send_command([0xFE, 0x01, 0x0D])
            time.sleep(0.01)
            
            # Step 2: Set output to Displacement RAW
            print("  Setting output to Displacement RAW...")
            self.send_command([0x80, 0x40, 0x0D])
            time.sleep(0.12)  # Wait for OUTPUT_STAT to complete
            
            # Verify OUTPUT_STAT (should be 0 when complete)
            self.send_command([0xFE, 0x01, 0x0D])
            response = self.send_command([0x00, 0x00, 0x0D], 4)
            if len(response) >= 4:
                output_stat = response[2] & 0x01
                if output_stat != 0:
                    print("  Warning: OUTPUT_STAT still in progress")
            
            # Step 3: Enable UART Auto and Auto Start
            print("  Enabling UART Auto and Auto Start...")
            self.send_command([0xFE, 0x01, 0x0D])
            self.send_command([0x88, 0x03, 0x0D])
            time.sleep(0.01)
            
            # Step 4: Flash backup
            print("  Saving settings to flash...")
            self.send_command([0xFE, 0x01, 0x0D])
            self.send_command([0x8A, 0x08, 0x0D])
            time.sleep(0.32)  # Wait for flash backup
            
            # Verify flash backup
            self.send_command([0xFE, 0x00, 0x0D])
            response = self.send_command([0x04, 0x00, 0x0D], 4)
            if len(response) >= 4:
                flash_error = response[2] & 0x01
                if flash_error != 0:
                    print("  Error: Flash backup failed!")
                    return False
            
            print("  Configuration complete!")
            return True
            
        except Exception as e:
            print(f"Configuration error: {e}")
            return False
    
    def to_dec24(self, b1: int, b2: int, b3: int) -> float:
        """Convert 3 bytes to 24-bit signed decimal (meters)."""
        msb2 = (b1 & 0x00C0) >> 6
        dec = ((b1 & 0x3F) << 16) + (b2 << 8) + b3
        return (msb2 & 0b10) * -1 + (msb2 & 0b01) + dec / 2**22
    
    def to_int8(self, b: int) -> int:
        """Convert byte to 8-bit signed integer."""
        return (0x80 & b) * -1 + (0x7F & b)
    
    def parse_packet(self, packet: List[int]) -> Optional[dict]:
        """Parse displacement packet."""
        if self.packet_size == 13:
            if len(packet) != 13 or packet[0] != 0x80 or packet[12] != 0x0D:
                return None
            
            temp = self.to_int8(packet[1]) * -0.9707008 + 34.987
            x_m = self.to_dec24(packet[3], packet[4], packet[5])
            y_m = self.to_dec24(packet[6], packet[7], packet[8])
            z_m = self.to_dec24(packet[9], packet[10], packet[11])
            count = packet[2] & 0b11
            
            return {
                'temp': temp,
                'x_mm': x_m * 1000.0,
                'y_mm': y_m * 1000.0,
                'z_mm': z_m * 1000.0,
                'count': count,
            }
        else:
            # 921.6 kbps parsing (similar structure)
            if len(packet) != 19 or packet[0] != 0x80 or packet[18] != 0x0D:
                return None
            # Implementation for 19-byte packets...
            return None
    
    def read_continuous(self, duration: float = 10.0):
        """Continuously read and display displacement data."""
        if not self.ser:
            raise RuntimeError("Connection not open")
        
        print(f"\nReading displacement data for {duration} seconds...")
        print("Waiting for sensor initialization (2 seconds)...")
        time.sleep(2.0)  # Wait for transient response
        
        buffer = deque()
        start_time = time.time()
        packet_count = 0
        
        print("\nTime(s)    X(mm)      Y(mm)      Z(mm)      Temp(°C)")
        print("-" * 60)
        
        while time.time() - start_time < duration:
            # Read available bytes
            if self.ser.in_waiting > 0:
                new_data = self.ser.read(self.ser.in_waiting)
                buffer.extend(new_data)
            
            # Process complete packets
            while len(buffer) >= self.packet_size:
                # Find packet start
                if buffer[0] != 0x80:
                    buffer.popleft()
                    continue
                
                # Extract packet
                packet = [buffer.popleft() for _ in range(min(self.packet_size, len(buffer)))]
                
                if len(packet) == self.packet_size and packet[-1] == 0x0D:
                    data = self.parse_packet(packet)
                    if data:
                        elapsed = time.time() - start_time
                        print(f"{elapsed:7.2f}   {data['x_mm']:8.4f}   {data['y_mm']:8.4f}   "
                              f"{data['z_mm']:8.4f}   {data['temp']:7.2f}")
                        packet_count += 1
                else:
                    # Packet corruption, reset buffer
                    buffer.clear()
            
            time.sleep(0.001)  # Small delay
        
        print(f"\nReceived {packet_count} packets in {duration:.1f} seconds")
        print(f"Average rate: {packet_count/duration:.1f} packets/second")


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python displacement_autostart.py <serial_port> [configure]")
        print("Example: python displacement_autostart.py /dev/ttyUSB0 configure")
        sys.exit(1)
    
    port = sys.argv[1]
    configure = len(sys.argv) > 2 and sys.argv[2] == "configure"
    
    sensor = DisplacementSensor(port, baud=460800)
    
    try:
        sensor.open()
        
        if configure:
            if sensor.configure_displacement_autostart():
                print("\nConfiguration saved! Power cycle the sensor to activate.")
                print("After power cycle, the sensor will automatically start sending displacement data.")
            else:
                print("\nConfiguration failed!")
                sys.exit(1)
        else:
            # Just read data (assumes already configured)
            sensor.read_continuous(duration=10.0)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sensor.close()


if __name__ == "__main__":
    main()
```

### Usage

```bash
# Configure sensor for displacement auto-start
python displacement_autostart.py /dev/ttyUSB0 configure

# After power cycle, read data (no configure flag)
python displacement_autostart.py /dev/ttyUSB0
```

---

## Troubleshooting

### Issue: Sensor doesn't start automatically after power cycle

**Solutions:**
1. Verify `UART_CTRL` register: bits [1:0] should be `11`
2. Verify flash backup completed successfully (`FLASH_BU_ERR = 0`)
3. Wait at least 900ms after power-on for initialization
4. Check that sensor is in Sampling Mode (read `MODE_STAT`)

### Issue: Invalid packet format

**Solutions:**
1. Verify packet starts with `0x80` and ends with `0x0D`
2. Check baud rate matches configuration (460800 or 921600)
3. Verify `BURST_CTRL` register settings match expected packet size
4. Ensure no other process is accessing the serial port

### Issue: Displacement values out of range

**Solutions:**
1. Check for structural resonance warnings (`EXI_ERR` flags)
2. Verify sensor mounting (should be firmly attached)
3. Check for alarm conditions (`ALARM_ERR` flags)
4. Values outside ±200 mm indicate saturation or error

### Issue: No data after configuration

**Solutions:**
1. Wait for transient response period (~1.736s for displacement)
2. Verify sensor entered Sampling Mode automatically
3. Check `NOT_READY` bit in `GLOB_CMD` (should be 0)
4. Verify `OUTPUT_STAT` completed (bit [0] = 0)

### Issue: Flash backup fails

**Solutions:**
1. Ensure sensor is powered properly (12V recommended)
2. Wait longer for flash backup to complete (up to 310ms)
3. Check `FLASH_ERR` in `DIAG_STAT1` for flash memory errors
4. Try flash test to verify non-volatile memory is working

---

## Reference: Key Specifications

### Displacement Output
- **Range**: -200 to +200 mm
- **Scale Factor**: 2.38 × 10^-4 mm/LSB
- **Sampling Rate**: 300 Sps (RAW mode)
- **Frequency Range**: 1 to 100 Hz (-3 dB)
- **Transient Response**: ~1.736 seconds

### Auto-Start Timing
- **Power-On Start-Up**: ~900ms
- **Reset Recovery**: ~970ms
- **Flash Backup**: ~310ms
- **Output Mode Setting**: ~118ms

### Communication
- **Baud Rates**: 115.2k, 230.4k, 460.8k, 921.6k
- **Packet Delimiter**: 0x0D (CR)
- **Address Byte**: 0x80

---

## Additional Resources

- Datasheet: `vibration_sensor.txt` in this directory
- Section 4.11: Automatic Start (For UART Auto Sampling Only)
- Section 4.13: Velocity and Displacement Output
- Section 6.12: DISP Register (Window 0)
- Section 7.1.9: Auto Start (UART)

---

**Note**: This configuration persists after power cycle due to flash backup. To disable auto-start, set `AUTO_START` bit to 0 and perform another flash backup.


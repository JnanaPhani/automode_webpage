# Sensor Auto Start Configuration Tool

A **cross-platform, modular** tool to configure M-A542VR1 sensors (A342/A352) in UART Auto Start mode.

**Author:** [Jnana Phani A](https://phani.zenithtek.in)  
**Organization:** [Zenith Tek](https://zenithtek.in)

## Features

- **Cross-platform**: Works on Linux, Windows, macOS, and other operating systems
- **Modular design**: Separated into logical modules for easy maintenance
- **Port detection**: Automatically lists available serial ports
- **OS-specific handling**: Handles platform differences automatically
- **Error handling**: Comprehensive error messages and troubleshooting help

## Project Structure

```
sensor_auto_start_config/
├── configure_auto_start.py  # Main entry point
├── platform_utils.py        # OS detection and platform utilities
├── sensor_comm.py           # Low-level serial communication
├── sensor_config.py          # Sensor configuration operations
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .gitignore               # Git ignore file
```

## Requirements

- Python 3.6 or higher
- pyserial library

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install pyserial
```

## Usage

### Basic Usage

```bash
python configure_auto_start.py <port> [baud_rate]
```

### List Available Ports

```bash
python configure_auto_start.py --list-ports
```

### Examples

**Linux:**
```bash
# List ports
python configure_auto_start.py --list-ports

# Configure with default baud rate (460800)
python configure_auto_start.py /dev/ttyUSB0

# Configure with custom baud rate
python configure_auto_start.py /dev/ttyUSB0 460800
```

**Windows:**
```bash
# List ports
python configure_auto_start.py --list-ports

# Configure sensor
python configure_auto_start.py COM3
python configure_auto_start.py COM3 460800
```

**macOS:**
```bash
# List ports
python configure_auto_start.py --list-ports

# Configure sensor
python configure_auto_start.py /dev/tty.usbserial-1410
python configure_auto_start.py /dev/tty.usbserial-1410 460800
```

### Command Line Options

```
usage: configure_auto_start.py [-h] [--list-ports] [--baud-rate BAUD]
                               [port] [baud]

positional arguments:
  port              Serial port path
  baud              Baud rate (default: 460800)

options:
  -h, --help        Show help message
  --list-ports      List all available serial ports
  --baud-rate BAUD  Baud rate (default: 460800)
```

## What It Does

1. **Detects your OS** and handles platform-specific differences
2. **Connects to the sensor** on the specified port and baud rate
3. **Sends reset commands** to initialize the sensor
4. **Sets UART_CTRL register** to `0x03` which enables:
   - `AUTO_START=1` (bit [1]): Sensor will auto-start after power-on/reset
   - `UART_AUTO=1` (bit [0]): UART auto sampling mode enabled
5. **Performs flash backup** to save the setting to non-volatile memory
6. **Verifies backup** by checking for errors

## Module Descriptions

### `configure_auto_start.py`
Main entry point with command-line interface and argument parsing.

### `platform_utils.py`
- OS detection (Linux, Windows, macOS)
- Port listing and validation
- Platform-specific port naming
- Permission help messages

### `sensor_comm.py`
- Low-level serial communication
- Connection management
- Command sending and response reading

### `sensor_config.py`
- Sensor configuration operations
- UART Auto Start mode setup
- Flash backup functionality

## Output

The tool provides detailed logging output showing:
- OS detection
- Connection status
- Register configuration
- Flash backup progress
- Verification results
- Success/failure status

## After Configuration

Once configured, the sensor will:
- Automatically start transmitting data after power-on
- Automatically start transmitting after reset
- Persist the setting across power cycles (stored in flash memory)

## Troubleshooting

### Connection Errors

If you get connection errors:
- Use `--list-ports` to see available ports
- Verify the port name is correct for your OS
- Check that the sensor is connected
- Try different baud rates if communication fails

### Permission Denied (Linux)

If you get permission denied errors:
```bash
sudo usermod -a -G dialout $USER
# Then log out and log back in
```

Or run with sudo (not recommended):
```bash
sudo python configure_auto_start.py /dev/ttyUSB0
```

### Permission Denied (macOS)

You may need to:
1. Add your user to the dialout group
2. Or run with sudo (not recommended)

### Port Not Found

- Use `--list-ports` to see available ports
- Check USB cable connection
- Try unplugging and replugging the device
- On Linux: Check if device appears with `ls -la /dev/ttyUSB*`

### Flash Backup Timeout

If flash backup times out:
- Wait a few seconds and try again
- Check sensor power supply
- Verify sensor is responding to commands

## Supported Operating Systems

- **Linux** (Ubuntu, Debian, Raspberry Pi OS, etc.)
- **Windows** (Windows 7, 8, 10, 11)
- **macOS** (10.12 and later)

## Supported Baud Rates

- 230400
- 460800 (default)
- 921600

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2024 [Jnana Phani A](https://phani.zenithtek.in), [Zenith Tek](https://zenithtek.in)**

### Note on Sensor Hardware

This software is based on the M-A542VR1 sensor documentation from Seiko Epson Corporation. The sensor hardware and firmware are proprietary to Seiko Epson Corporation.

## Author & Organization

**Author:** [Jnana Phani A](https://phani.zenithtek.in)  
**Organization:** [Zenith Tek](https://zenithtek.in)

This tool was developed by [Jnana Phani A](https://phani.zenithtek.in) at [Zenith Tek](https://zenithtek.in) for configuring M-A542VR1 vibration sensors in UART Auto Start mode.

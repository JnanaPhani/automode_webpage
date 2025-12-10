# Accelerometer Auto Mode Configuration

This script configures the M-A552AR1 accelerometer sensor to automatically start transmitting sampling data after power-on or reset, following the sample program flow from datasheet section 8.1.11.

## Features

- **No user configuration required** - Uses fixed values from datasheet section 8.1.11
- **Automatic setup** - Configures sensor for auto-start mode
- **Flash backup** - Saves settings to non-volatile memory
- **Cross-platform** - Works on Linux, Windows, and macOS

## Fixed Configuration

The script uses the following fixed values (no user input needed):

- **Output rate**: 200 Sps (factory default)
- **Filter**: TAP=512, fc=60 Hz
- **UART Auto sampling**: Enabled
- **Auto Start**: Enabled
- **Burst output**: TEMP, ACC_XYZ, COUNT enabled
- **Baud rate**: 230.4 kbps (default, can be changed with `--baud`)

## Usage

### Basic Usage

```bash
# Linux
python3 acc_automode.py /dev/ttyUSB0

# Windows
python acc_automode.py COM3

# macOS
python acc_automode.py /dev/tty.usbserial-1410
```

### List Available Ports

```bash
python acc_automode.py --list-ports
```

### Custom Baud Rate

```bash
python acc_automode.py /dev/ttyUSB0 --baud 460800
```

## Requirements

- Python 3.6+
- pyserial library: `pip install pyserial`
- Access to the Accelerometer_Auto_Mode directory (for sensor_comm.py and platform_utils.py)

## How It Works

The script follows the exact procedure from datasheet section 8.1.11:

1. **Power-on sequence** (section 8.1.1)
   - Wait for sensor to be ready
   - Check for hardware errors

2. **Set registers** (section 8.1.11 step a)
   - Set SMPL_CTRL(H) = 0x04 (200 Sps)
   - Set FILTER_CTRL(L) = 0x08 (TAP=512, fc=60)
   - Set UART_CTRL(L) = 0x03 (UART Auto sampling, Auto start=on)
   - Set BURST_CTRL(L) = 0x02 (COUNT=on)
   - Set BURST_CTRL(H) = 0x47 (TEMP=on, ACC_XYZ=on)

3. **Execute flash backup** (section 8.1.11 step b)
   - Save settings to non-volatile memory
   - Verify backup success

After configuration, the sensor will automatically enter sampling mode after power-on or reset.

## Output

After successful configuration, the sensor will:
- Automatically enter sampling mode after power-on or reset
- Start transmitting data automatically at 200 Sps
- Include temperature, acceleration (X, Y, Z), and counter in burst output

## Troubleshooting

### Permission Denied (Linux)

```bash
sudo usermod -a -G dialout $USER
# Then log out and log back in
```

### Port Not Found

Use `--list-ports` to see available serial ports:

```bash
python acc_automode.py --list-ports
```

### Import Errors

Make sure the `Accelerometer_Auto_Mode` directory exists in the parent directory with:
- `sensor_comm.py`
- `platform_utils.py`

## Author

Jnana Phani A (https://phani.zenithtek.in)

## Organization

Zenith Tek (https://zenithtek.in)

## References

- M-A552AR1 Datasheet, Section 8.1.11: Auto Start
- M-A552AR1 Datasheet, Section 8.1.1: Power-on sequence
- M-A552AR1 Datasheet, Section 8.1.7: Flash Backup


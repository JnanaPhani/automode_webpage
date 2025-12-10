# How to Run ZenithTek Sensor Configuration Tool

## Quick Start (Packaged Executable) ✅

The easiest way to run the application is using the pre-built executable:

### Option 1: Double-click
1. Navigate to: `desktop_app\dist\windows\ZenithTek-SensorConfig\`
2. Double-click `ZenithTek-SensorConfig.exe`

### Option 2: Command Line
```powershell
cd desktop_app\dist\windows\ZenithTek-SensorConfig
.\ZenithTek-SensorConfig.exe
```

**Note:** The executable is standalone - no Python installation or dependencies needed!

---

## Development Mode (From Source)

If you want to run from source code for development or testing:

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Steps

1. **Install Dependencies**
   ```bash
   pip install -r helper_app/requirements.txt
   ```

2. **Run the Application**
   
   **Option A: Using the launcher script (Easiest)**
   ```bash
   # From project root directory
   python run_app.py
   ```
   
   **Option B: Run as a module**
   ```bash
   # IMPORTANT: Must run from project root directory
   # Navigate to project root first:
   cd C:\Users\jnana\OneDrive - Zenith Tek\Projects\FY_2025-26\IIT_Project\automode_webpage
   
   # Then run as a module:
   python -m desktop_app.app
   ```
   
   **Note:** You cannot run `python desktop_app/app.py` directly because Python needs the project root in its path to resolve the `desktop_app` module imports. Use `run_app.py` or `python -m desktop_app.app` instead.

### Required Dependencies
The application requires:
- PySide6 (Qt GUI framework)
- pyserial (Serial communication)
- fastapi & uvicorn (Helper service)
- Other dependencies listed in `helper_app/requirements.txt`

---

## Using the Application

Once the application launches:

1. **Connect Your Sensor**
   - Connect your Epson sensor via USB
   - Wait for Windows to recognize the device

2. **Select COM Port**
   - Click the "Select Port" dropdown
   - Choose your sensor's COM port (e.g., COM3)
   - Click "Refresh Ports" if your port doesn't appear

3. **Select Sensor Type**
   - Choose from:
     - **Vibration Sensor** (M-A542VR1)
     - **IMU** (M-G552PR80)
     - **Accelerometer** (M-A552AR1) - NEW!

4. **Connect**
   - Click "Connect" button
   - Wait for connection confirmation dialog

5. **Detect Sensor**
   - Click "Detect" to identify your sensor
   - Sensor information will be displayed

6. **Configure**
   - For IMU: Select sampling rate (125 SPS is default)
   - For Accelerometer: Select SPS rate (200 SPS is default)
   - For Vibration: Rates are fixed
   - Click "Start Configuration"

7. **Complete**
   - Wait for configuration to complete
   - The app will auto-disconnect after setting auto mode
   - Follow the dialog instructions (e.g., restart sensor)

---

## Troubleshooting

### Executable Won't Start
- Check Windows Defender/Antivirus isn't blocking it
- Try running as Administrator
- Check if all files in the `_internal` folder are present

### Development Mode Issues
- Ensure Python 3.8+ is installed: `python --version`
- Install dependencies: `pip install -r helper_app/requirements.txt`
- Check for missing modules in error messages

### COM Port Not Appearing
- Ensure sensor is connected and powered on
- Click "Refresh Ports" button
- Check Device Manager to verify COM port is recognized
- Try unplugging and reconnecting the USB cable

### Connection Timeout
- Verify correct COM port is selected
- Check USB cable connection
- Ensure no other application is using the COM port
- Try disconnecting and reconnecting

---

## System Requirements

- **OS:** Windows 10 or later
- **Hardware:** USB port for sensor connection
- **No additional drivers required** (for packaged executable)

---

## For More Information

See `README.txt` in the distribution package for detailed usage instructions.


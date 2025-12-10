================================================================================
    ZenithTek Sensor Configuration Tool v1.1.0
    Windows Standalone Application
================================================================================

OVERVIEW
--------
The ZenithTek Sensor Configuration Tool is a user-friendly desktop application
for configuring Epson Vibration Sensors and IMU (Inertial Measurement Unit)
sensors. This tool allows you to connect to sensors via USB, detect sensor
types, and configure their settings including sampling rates and filter options.

SYSTEM REQUIREMENTS
-------------------
- Windows 10 or later
- USB port for sensor connection
- No additional software or drivers required (all dependencies included)

INSTALLATION
------------
1. Extract this ZIP file to any location on your computer
2. No installation required - the application is ready to use
3. Double-click "ZenithTek-SensorConfig.exe" to launch the application

QUICK START GUIDE
-----------------
1. CONNECT YOUR SENSOR
   - Connect your Epson sensor to your computer via USB cable
   - Wait for Windows to recognize the device

2. SELECT COM PORT
   - Open the ZenithTek Sensor Configuration Tool
   - In the "Connection" section, click the "Select Port" dropdown
   - Select the COM port that corresponds to your sensor (e.g., COM3)
   - If your port doesn't appear, click "Refresh Ports"

3. SELECT SENSOR TYPE
   - In the "Select Sensor" dropdown, choose either:
     * Vibration Sensor
     * IMU (Inertial Measurement Unit)

4. CONNECT TO SENSOR
   - Click the "Connect" button
   - Wait for the "Connection Established" dialog
   - The connection status will be displayed in the log area

5. DETECT SENSOR
   - Click the "Detect" button
   - The application will identify your sensor and display:
     * Detected sensor type
     * Product ID
     * Serial Number
   - A "Detection Complete" dialog will appear with sensor information

6. CONFIGURE SENSOR
   - For IMU Sensors:
     * Select your desired sampling rate from the dropdown
     * Default is 125 SPS (Samples Per Second) - labeled as "(default)"
     * All sampling rates use TAP = 128 filter automatically
     * Available rates: 2000, 1000, 500, 400, 250, 200, 125, 100, 80, 
       62.5, 50, 40, 31.25, 25, 20, 15.625 SPS
   
   - For Vibration Sensors:
     * RAW data sampling rates are FIXED and cannot be changed
     * Velocity RAW: 3000 Sps (FIXED)
     * Displacement RAW: 300 Sps (FIXED)

7. START CONFIGURATION
   - Click "Start Configuration" button
   - Wait for the configuration to complete
   - A dialog will appear with next steps:
     * If sensor is set to auto mode: "Please restart the sensor (power 
       cycle or reset) to start receiving data"
     * The application will automatically disconnect after setting auto mode

8. DISCONNECT (if needed)
   - Click "Disconnect" button to close the connection
   - Or the app will auto-disconnect after configuring auto mode

ADDITIONAL FEATURES
-------------------
- EXIT AUTO MODE: If your sensor is in auto mode and you need to configure 
  it, click "Exit Auto Mode" first, then proceed with detection and 
  configuration.

- FACTORY RESET: Use "Factory Reset" to restore sensor to factory default 
  settings. You will need to restart the sensor after this operation.

- OUTPUT LOGS: The bottom section shows detailed operation logs with 
  timestamps for troubleshooting.

IMPORTANT NOTES
---------------
- TAP FILTER: All IMU sampling rates now use TAP = 128 filter as standard. 
  This setting is automatic and cannot be changed.

- DEFAULT SAMPLING RATE: 125 SPS is the default and recommended sampling 
  rate for IMU sensors.

- AUTO MODE: When you configure a sensor to auto mode, the application will 
  automatically disconnect from the COM port. You must restart the sensor 
  (power cycle or reset) for the configuration to take effect.

- TIMEOUT PROTECTION: All operations have timeout protection to prevent the 
  application from freezing:
  * Connect: 12 seconds
  * Disconnect: 5 seconds
  * Detection: 35 seconds
  * Configuration: 30 seconds

- ERROR HANDLING: If an operation times out, you will see an error message. 
  Check your sensor connection and try again.

TROUBLESHOOTING
---------------
Problem: COM port not appearing in the list
Solution: 
- Click "Refresh Ports" button
- Ensure sensor is properly connected via USB
- Check Device Manager to verify the port is recognized by Windows

Problem: Connection fails or times out
Solution:
- Verify the correct COM port is selected
- Check USB cable connection
- Try disconnecting and reconnecting the sensor
- Ensure no other application is using the COM port

Problem: Detection fails or times out
Solution:
- Make sure sensor is powered on
- Verify sensor type selection matches your actual sensor
- Try exiting auto mode first if sensor is in auto mode
- Check the output logs for detailed error messages

Problem: Configuration fails
Solution:
- Ensure sensor is detected successfully first
- Check that you have selected the correct sensor type
- Review the output logs for specific error messages
- Try disconnecting and reconnecting

SUPPORT
-------
For technical support or questions, please contact Zenith Tek support team.

VERSION INFORMATION
-------------------
Version: 1.1.0
Release Date: 2025
Platform: Windows 10/11

CHANGELOG (v1.1.0)
------------------
- Added completion dialogs with next-step instructions
- Added auto-disconnect after setting sensor to auto mode
- Standardized TAP = 128 filter for all IMU sampling rates
- Removed TAP value selection from UI (now automatic)
- Set 125 SPS as default sampling rate with visual indicator
- Fixed app freezing issues during disconnect operations
- Fixed app freezing issues during detection operations
- Added timeout protection for all operations
- Improved error handling and user feedback

================================================================================
                    Thank you for using ZenithTek products!
================================================================================



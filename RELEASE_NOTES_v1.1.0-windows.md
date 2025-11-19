# Windows Release v1.1.0 - ZenithTek Sensor Configuration Tool

## 🎯 Platform Exclusive
**This release is exclusive for Windows operating systems.**

## 📦 What's Included
- **ZenithTek-SensorConfig.exe** - Standalone Windows executable
- Complete application package with all dependencies
- User-friendly README with installation and usage instructions

## ✨ New Features (v1.1.0)

### Enhanced User Experience
- **Completion Dialogs**: Informative dialog boxes after each action with clear next-step instructions
- **Auto-Disconnect**: Automatically disconnects from COM port after setting sensor to auto mode
- **Default Sampling Rate Indicator**: 125 SPS is pre-selected and clearly labeled as "(default)" in the dropdown
- **Improved Error Handling**: Better timeout protection and error messages for all operations

### Configuration Improvements
- **Standardized Filter Settings**: TAP = 128 filter is now standard for all IMU sampling rates
- **Simplified UI**: Removed TAP value selection component (now automatically set to 128)
- **Default Settings**: 125 SPS is the default sampling rate for IMU sensors

### Reliability Enhancements
- **Timeout Protection**: All operations (connect, disconnect, detect, configure) now have timeout protection to prevent app freezing
  - Connect: 12 seconds timeout
  - Disconnect: 5 seconds timeout
  - Detection: 35 seconds timeout
  - Auto mode check: 6 seconds timeout
- **Robust Disconnect**: Improved disconnect handling with forced state updates even if serial port hangs
- **Non-Blocking Operations**: All async operations are properly protected to keep UI responsive

## ✨ Core Features (from v1.0.0)
- **Sensor Detection**: Manual sensor type selection (Vibration/IMU)
- **Auto Mode Detection**: Automatically detects if sensor is in auto mode before detection
- **Configuration Management**: Easy-to-use interface for sensor configuration
- **Connection Management**: Separate Connect, Detect, and Disconnect controls
- **Branded UI**: Professional interface with Zenith Tek branding

## 🚀 Installation
1. Download the `ZenithTek-SensorConfig-v1.1.0.zip` file
2. Extract to any location on your Windows computer
3. Run `ZenithTek-SensorConfig.exe` from the extracted folder
4. No additional installation required - all dependencies are included

## 📋 System Requirements
- Windows 10 or later
- USB port for sensor connection
- No additional software required

## 🔧 Usage
1. Connect your sensor via USB
2. Select the COM port from the dropdown
3. Choose sensor type (Vibration or IMU)
4. Click "Connect" to establish connection
5. Click "Detect" to identify the sensor
6. Configure sensor settings as needed
   - For IMU: Select sampling rate (125 SPS is default with TAP = 128 filter)
   - For Vibration: Fixed sampling rates apply
7. After configuration, the app will automatically disconnect if sensor is set to auto mode
8. Follow the completion dialog instructions (e.g., restart sensor if needed)

## 🐛 Bug Fixes (v1.1.0)
- Fixed app freezing during disconnect operations
- Fixed app freezing during detection operations
- Fixed timeout issues with serial port operations
- Improved error handling for hung serial connections
- Fixed UI responsiveness during long-running operations

## 🐛 Known Issues
- None at this time

## 📝 Notes
- This is a Windows-only release
- The application is packaged as a standalone executable with all dependencies included
- For Linux or macOS support, please check other releases
- All IMU sampling rates now use TAP = 128 filter as standard
- Timeout values are optimized for typical sensor response times but may need adjustment for slower hardware

## 🔄 Upgrade Notes (from v1.0.0)
- TAP value selection has been removed from the UI - all IMU configurations now use TAP = 128 automatically
- Default sampling rate is now 125 SPS (previously no default was set)
- Disconnect operations are now more reliable and won't freeze the application
- Detection operations have timeout protection to prevent indefinite waiting

## 🔗 Download
Download the release package: [ZenithTek-SensorConfig-v1.1.0.zip](https://dqxfwdaazfzyfrwzkmed.supabase.co/storage/v1/object/public/helper-installers/ZenithTek-SensorConfig-v1.1.0.zip)


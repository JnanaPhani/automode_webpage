#!/usr/bin/env python3
"""
Test script to validate UI logic without requiring PySide6 GUI.
Tests the sampling rate configuration and sensor type switching logic.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_sampling_rate_config():
    """Test that sampling rate configuration is correct."""
    print("Testing Sampling Rate Configuration...")
    
    # Expected supported rates
    expected_rates = [2000, 1000, 500, 400, 250, 200, 125, 100, 80, 62.5, 50, 40, 31.25, 25, 20, 15.625]
    
    # Read UI file to verify rates are present
    ui_file = Path(__file__).parent / "ui.py"
    with open(ui_file, 'r') as f:
        ui_content = f.read()
    
    # Check that all expected rates are in the UI code
    missing_rates = []
    for rate in expected_rates:
        # Check multiple formats
        found = False
        if isinstance(rate, int):
            # Check for integer format
            if str(rate) in ui_content:
                found = True
        else:
            # Check for decimal formats: "62.5", "62.500", "31.25", "31.250"
            rate_strs = [str(rate), f"{rate:.1f}", f"{rate:.2f}", f"{rate:.3f}"]
            for rate_str in rate_strs:
                if rate_str in ui_content:
                    found = True
                    break
        if not found:
            missing_rates.append(rate)
    
    if missing_rates:
        print(f"  ❌ Missing rates: {missing_rates}")
        return False
    else:
        print(f"  ✓ All {len(expected_rates)} sampling rates found in UI code")
    
    # Check default rate (125)
    if "125" in ui_content and "default_idx = supported_rates.index(125)" in ui_content:
        print("  ✓ Default sampling rate (125 SPS) is correctly set")
    else:
        print("  ❌ Default sampling rate not found or incorrectly set")
        return False
    
    return True

def test_sensor_type_switching():
    """Test that sensor type switching logic is correct."""
    print("\nTesting Sensor Type Switching Logic...")
    
    ui_file = Path(__file__).parent / "ui.py"
    with open(ui_file, 'r') as f:
        ui_content = f.read()
    
    # Check for IMU config group
    if "imu_config_group" in ui_content:
        print("  ✓ IMU configuration group found")
    else:
        print("  ❌ IMU configuration group not found")
        return False
    
    # Check for vibration info group
    if "vibration_info_group" in ui_content:
        print("  ✓ Vibration sensor info group found")
    else:
        print("  ❌ Vibration sensor info group not found")
        return False
    
    # Check for sensor type change handler
    if "_on_sensor_type_changed" in ui_content:
        print("  ✓ Sensor type change handler found")
    else:
        print("  ❌ Sensor type change handler not found")
        return False
    
    # Check that handler shows/hides both groups
    if "self.imu_config_group.setVisible(sensor == \"imu\")" in ui_content:
        print("  ✓ IMU config visibility logic found")
    else:
        print("  ❌ IMU config visibility logic not found")
        return False
    
    if "self.vibration_info_group.setVisible(sensor == \"vibration\")" in ui_content:
        print("  ✓ Vibration info visibility logic found")
    else:
        print("  ❌ Vibration info visibility logic not found")
        return False
    
    return True

def test_vibration_info_message():
    """Test that vibration sensor info message is correct."""
    print("\nTesting Vibration Sensor Info Message...")
    
    ui_file = Path(__file__).parent / "ui.py"
    with open(ui_file, 'r') as f:
        ui_content = f.read()
    
    # Check for key messages
    required_messages = [
        "FIXED",
        "3000 Sps",
        "300 Sps",
        "RMS/P-P"
    ]
    
    missing_messages = []
    for msg in required_messages:
        if msg not in ui_content:
            missing_messages.append(msg)
    
    if missing_messages:
        print(f"  ❌ Missing messages: {missing_messages}")
        return False
    else:
        print("  ✓ All required vibration sensor info messages found")
    
    return True

def test_configure_command():
    """Test that configure command passes sampling rate correctly."""
    print("\nTesting Configure Command Logic...")
    
    ui_file = Path(__file__).parent / "ui.py"
    with open(ui_file, 'r') as f:
        ui_content = f.read()
    
    # Check that configure command checks for IMU
    if "if sensor == \"imu\":" in ui_content:
        print("  ✓ IMU sensor check found in configure command")
    else:
        print("  ❌ IMU sensor check not found in configure command")
        return False
    
    # Check that sampling rate is extracted
    if "sampling_rate = self.sampling_rate_combo.currentData()" in ui_content:
        print("  ✓ Sampling rate extraction found")
    else:
        print("  ❌ Sampling rate extraction not found")
        return False
    
    # Check that tap value is extracted
    if "tap_value = self.tap_value_spin.value()" in ui_content:
        print("  ✓ TAP value extraction found")
    else:
        print("  ❌ TAP value extraction not found")
        return False
    
    # Check that values are passed to runtime
    if "self.runtime.configure(sensor, sampling_rate=sampling_rate, tap_value=tap_value)" in ui_content:
        print("  ✓ Runtime configure call with parameters found")
    else:
        print("  ❌ Runtime configure call with parameters not found")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Desktop App UI Logic Tests")
    print("=" * 60)
    
    tests = [
        ("Sampling Rate Configuration", test_sampling_rate_config),
        ("Sensor Type Switching", test_sensor_type_switching),
        ("Vibration Info Message", test_vibration_info_message),
        ("Configure Command", test_configure_command),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n  ❌ Error in {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Launcher script for ZenithTek Sensor Configuration Tool.

This script can be run from anywhere and will automatically
navigate to the correct directory and launch the application.
"""

import sys
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()

# Add the project root to Python path
sys.path.insert(0, str(script_dir))

# Change to project root directory
os.chdir(script_dir)

# Now import and run the application
if __name__ == "__main__":
    from desktop_app.app import run
    run()


Zenith Helper for Windows
=========================

This package contains the Zenith Helper background service for Windows.

Files:

- `zenith-helper.exe` – starts the helper API on `http://127.0.0.1:7421`
- `helper_app\legacy\...` – bundled sensor scripts (do not remove)
- `README.txt` – this guide

Getting Started
---------------

1. Extract this zip to any folder (e.g. `C:\Program Files\ZenithHelper`).
2. Double-click `zenith-helper.exe` to start the helper. A console window will appear with status logs.
3. Leave the helper running while using the Epson Sensor Portal in your browser.
4. To stop the helper, close the console window or press `Ctrl+C` inside it.

Auto-Start (Optional)
---------------------

To keep the helper running automatically:

1. Copy the extracted folder to a fixed location (e.g. `C:\Program Files\ZenithHelper`).
2. Create a shortcut to `zenith-helper.exe` and place it in `shell:startup` so it launches on login.
3. (Upcoming) A Windows Service/tray app will replace this manual step in a later release.

Troubleshooting
---------------

- If the Epson Sensor Portal cannot pair with the helper, ensure no firewall blocks `http://127.0.0.1:7421`.
- The helper logs live in the console window; keep it visible while debugging.
- Delete `%USERPROFILE%\.zenith_helper_token` to regenerate the API token if pairing gets stuck.

Need help? Share the latest helper console output with the ZenithTek team.


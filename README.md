# Epson Sensor Auto Start Portal

A browser-based control panel for configuring Epson M-A542VR1 vibration sensors and M-G552PR80 IMU modules in UART Auto Start mode. The experience runs entirely in the browser via the Web Serial API—no Python or Node backend is required once the page is loaded.

**Author:** Jnana Phani A  
**Organization:** Zenith Tek  
**License:** MIT

---

## Key Features

- **Multi-sensor aware** – switch between the vibration (M-A542VR1) and IMU (M-G552PR80) workflows inside a single interface.
`- **Selectable IMU sampling** – pick from datasheet-approved rates while the UI applies the recommended filter taps automatically.
- **One-click device pairing** – choose the connected Epson hardware through the browser’s secure serial picker.
- **Automatic register programming** – mirrors the register sequences from the Python utilities, including flash backup and verification.
- **Live activity log** – view streaming progress messages and error details directly in the UI.
- **One-click recovery** – Exit Auto Mode or trigger a factory reset from the browser when needed.
- **Brand-consistent design** – Aldrich font, Zenith Tek color palette, and logo integration.
- **Cross-platform ready** – works on Windows, macOS, and Linux desktops as long as the browser supports Web Serial.

---

## Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome (desktop) | ✅ Full support |
| Edge (desktop) | ✅ Full support |
| Chromium-based browsers (desktop) | ✅ Most builds support Web Serial |
| ChromeOS | ✅ Works on recent versions |
| Firefox / Safari | ⚠️ Web Serial is not yet enabled by default |
| Mobile browsers | ❌ Not supported (USB access unavailable) |

> Tip: if the status bar indicates that Web Serial is unavailable, switch to the latest Chrome or Edge release on desktop.

---

## Quick Start (For Operators)

1. **Connect hardware** – plug the Epson logger into your computer via USB and power the sensor.
2. **Open the web tool** – launch `vibrationsensor.zenithtek.in` (or your local development URL) in a supported browser.
3. **Choose the sensor** – pick “Vibration Sensor (M-A542VR1)” or “IMU Sensor (M-G552PR80)” from the dropdown so the right register sequence loads.
4. **Set the sampling rate** – IMU users can choose from datasheet-approved rates (filters apply automatically). Vibration sensor rates are fixed at 3000 sps (velocity) and 300 sps (displacement).
5. **Select the device** – click `Select Sensor`, choose the Epson device when prompted, and confirm browser permissions.
6. **Configure** – keep the default baud rate of 460800 (unless instructed otherwise) and press `Start Configuration`.
7. **Wait for confirmation** – watch the success banner and log panel for the success message before unplugging.
8. **Manage modes** – use “Exit Auto Mode” to stop streaming without power-cycling, or “Factory Reset” if you must restore defaults.

The sensor stores the new UART Auto Start configuration in flash. After a power cycle it will begin streaming immediately without further action.

---

## IMU Sampling Rates

When the IMU sensor is selected, the UI exposes the most common data output rates from the M-G552PR80 datasheet. The recommended moving-average filter tap is applied automatically for each option, and the tool waits for the filter to settle before continuing.

| Rate (sps) | DOUT_RATE code | Filter tap | Notes |
|------------|----------------|------------|-------|
| 2000       | 0x00           | TAP 2      | Requires 921 600 baud to avoid saturation (auto-selected). |
| 1000       | 0x01           | TAP 4      | Works best at ≥ 460 800 baud; 921 600 recommended. |
| 500        | 0x02           | TAP 8      | General-purpose, balanced bandwidth. |
| 250        | 0x04           | TAP 16     | Improved smoothing, moderate latency. |
| 125        | 0x06           | TAP 32     | Strong smoothing for slower dynamics. |
| 62.5       | 0x09           | TAP 32     | Additional averaging with reduced throughput. |
| 31.25      | 0x0C           | TAP 64     | High smoothing, higher latency. |
| 15.625     | 0x0F           | TAP 128    | Maximum smoothing for very slow signals. |

For the vibration sensor, the RAW velocity output is fixed at 3000 sps and the displacement output at 300 sps per the M-A542VR1 datasheet, so no additional sampling controls are required.

> When you pick an IMU sampling rate above 500 sps, the portal automatically bumps the baud rate to **921 600 bps**. You can override it, but the UI (and logs) will warn that lower speeds may drop data.

### Exit Auto Mode & Factory Reset

- **Exit Auto Mode** stops sampling, clears the `AUTO_START` configuration, and runs a flash backup so the device stays in manual/configuration mode after a reboot.
- **Factory Reset** issues the datasheet’s software-reset command (`SOFT_RST`), returning the sensor to its defaults. After the reset, reconnect and reconfigure if needed.

Use these actions only when a sensor should stop streaming, or when a configuration appears corrupted.

---

## Local Development

If you want to customise or host the UI yourself:

```bash
git clone <your-repo>
cd zenithtek_sensor_portal
npm install
npm run dev
```

- `npm run dev` launches Vite’s dev server on `http://localhost:5173`.
- For production, build with `npm run build` and deploy the `dist/` folder to any static hosting provider (Vercel, Netlify, S3, etc.).

You no longer need to start the legacy Express bridge or Python script—the Web Serial workflow replaces that stack.

---

## How the Web Serial Flow Works

1. **Permission handshake** – the browser presents a secure device picker. The app never hardcodes port names.
2. **Register programming** – the UI sends the correct command set for the chosen sensor (vibration or IMU), including UART_CTRL, sampling, and burst registers where applicable.
3. **Flash verification** – the tool polls the `GLOB_CMD` register until bit [3] clears and validates `FLASH_BU_ERR` is zero.
4. **Auto close** – once complete, the port is closed and can be reused by other applications.

All serial traffic happens inside the browser sandbox; no data ever leaves the user’s machine.

---

## Troubleshooting

- **Browser says “Web Serial not supported”**: update to the latest Chrome or Edge on desktop.
- **Device not listed**: unplug/reconnect the USB cable, ensure the sensor is powered, then press `Select Sensor` again.
- **Permission prompt not shown**: some OSes require the page to be reloaded after unplugging devices. Refresh and retry.
- **Log shows read timeout**: verify the USB cable, try a lower baud rate, or power-cycle the sensor before repeating the steps.
- **Need to revoke access**: open `chrome://settings/content/serialPorts` (or corresponding settings page) to remove saved permissions.

For deeper issues, contact Zenith Tek support with the log output copied from the UI.

---

## Project Structure

```
zenithtek_sensor_portal/
├── public/                  # Static assets (logos, favicons)
├── src/
│   ├── components/          # React components (Header, InfoPanel, etc.)
│   ├── services/
│   │   └── webSerial.ts     # Web Serial implementation and sensor command logic
│   ├── types/               # Shared TypeScript definitions
│   ├── App.tsx              # Root component
│   └── main.tsx             # Vite entry point
├── index.html
├── package.json
└── tailwind.config.js
```

---

## Security Notes

- Web Serial access always requires an explicit user gesture and is limited to the selected device.
- The application never stores or transmits sensor data to external servers.
- HTTPS is mandatory when hosting publicly (Vercel, Netlify, etc. handle this automatically).

---

## License & Contact

- License: MIT (see `LICENSE` in the repository)
- Author: Jnana Phani A  
- Organisation: Zenith Tek  
- Website: https://zenithtek.in  
- Email: support@zenithtek.in

For feature requests or integration support, please open an issue or contact Zenith Tek directly.


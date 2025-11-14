# Zenith Tek Sensor Helper – Architecture Plan

## Overview

The helper is a lightweight Python service that owns the serial connection to Epson sensors (M-A542VR1 vibration sensor and M-G552PR80 IMU). It exposes a local API that the existing browser portal can call from any modern browser (Chrome, Edge, Firefox, Safari). Key goals:

- Preserve current CLI behaviour by copying, not modifying, existing Python modules.
- Maintain a single persistent serial session with robust recovery and logging.
- Support Windows, macOS, and Linux, including auto-start and auto-update.
- Provide streaming logs to the portal without writing data to disk.
- Keep the attack surface minimal: localhost only, authenticated requests, strict input validation.

## Project Layout (New Helper Copy)

```
helper/
├── README.md
├── requirements.txt
├── helper_app/
│   ├── __init__.py
│   ├── api.py              # FastAPI/Quart HTTP + WebSocket endpoints
│   ├── auth.py             # Token generation & verification
│   ├── config.py           # Settings (baud defaults, Supabase URLs)
│   ├── controller.py       # High-level commands (detect/configure/reset/exit-auto)
│   ├── serial_engine.py    # Wrapper around copied pyserial-based logic
│   ├── session.py          # Manages persistent connection & background drain loop
│   ├── updater.py          # Auto-update client using Supabase manifest
│   ├── logging.py          # Structured log emitter (in-memory queue -> WebSocket)
│   └── worker.py           # Application entry point (AsyncIO event loop)
├── tests/
│   ├── test_controller.py
│   ├── test_session.py
│   └── fixtures
└── cli.py                  # Console entry for development/debug
```

Existing CLI code from `sensor_auto_start_config/` and `IMU_Auto_Mode/` will be copied into `helper_app/legacy/` and imported to avoid regressions.

## Serial Session Strategy

- The helper opens the serial port once per request session, maintaining a background reader that drains burst data.
- Commands (detect/configure/exit/reset) run within a `with_session_io()` guard that pauses the drain task, executes the command sequence, and resumes draining.
- Automatic recovery:
  - If the OS drops the connection, the helper retries opening the port (limited attempts with exponential backoff).
  - Errors bubble up with structured codes and messages for the portal.

## API Contract (HTTP + WebSocket)

Base URL: `http://127.0.0.1:7421`

All requests include header `X-Zenith-Token: <random-token>` generated per helper install.

### REST Endpoints

| Method & Path      | Payload                          | Response                                    |
|--------------------|----------------------------------|---------------------------------------------|
| `POST /pair`       | –                                | `{ token }` for first-party browser pairing |
| `GET /status`      | –                                | Helper version, platform, port status       |
| `POST /connect`    | `{ "port": "COM3", "baud":... }` | `{ "connected": true, "message": "..." }`   |
| `POST /disconnect` | –                                | `{ "connected": false }`                    |
| `POST /detect`     | optional `{ "sensor": "imu" }`   | `{ success, productId, serialNumber, logs }`|
| `POST /configure`  | `{ "sensor": "vibration", ... }` | `{ success, requiresRestart, logs }`        |
| `POST /exit-auto`  | `{ "persist": true }`            | `{ success, logs }`                         |
| `POST /reset`      | `{ "sensor": "..."} `            | `{ success, warnings, logs }`               |
| `POST /update`     | –                                | Kicks off Supabase manifest lookup          |
| `POST /update/download` | – (optional `{ "platform": "linux" }`) | Downloads latest installer to helper cache |

### WebSocket

- `ws://127.0.0.1:7421/logs` streams live log events:
  ```json
  {
    "level": "info",
    "timestamp": "2025-11-13T09:36:12.123Z",
    "message": "Flash backup completed"
  }
  ```

## Supabase Integration

- **`helper_updates` table**: columns `version`, `platform`, `download_url`, `checksum`, `release_notes`.
- The helper’s `updater.py` polls this table on startup and in the background (configurable interval, default 6 hours) to detect new versions.
- Successful lookups are cached in-memory so portal status checks avoid redundant Supabase calls.
- Downloaded installer packages are saved to `~/.zenith_helper/updates` (override via `ZENITH_HELPER_UPDATES_DIR`), with SHA-256 verification when a checksum is provided.
- `/pair` is only accessible from approved origins (matching the CORS whitelist) so the browser can obtain the token automatically without exposing it publicly.
- The whitelist defaults to local development URLs; set `ZENITH_HELPER_ALLOWED_ORIGINS` (comma-separated, e.g. `https://sensor.zenithtek.in`) to authorise production domains.
- When an update is available, the helper downloads the installer, verifies checksum, and prompts the user via system notification or the portal (API response includes `updateAvailable` flag).

## Portal Changes

- On load, the portal attempts `GET /status`. If unreachable, it shows:
  - “Helper not detected” banner with OS-specific download links (Supabase-hosted files).
  - Step-by-step install instructions.
- All button actions switch from Web Serial calls to REST requests above.
- Logs panel subscribes to the WebSocket stream to display ongoing messages.
- Persisted session state in the portal includes helper connection status, selected sensor, and update availability.

## Auto-start & Packaging Plan

| OS      | Packaging                | Auto-start strategy                         |
|---------|--------------------------|---------------------------------------------|
| Windows | PyInstaller `.exe` + MSI | Windows service (optional tray application) |
| macOS   | `.app` bundle via PyInstaller/Briefcase | LaunchAgent with menu bar icon        |
| Linux   | AppImage or .deb         | systemd user service                        |

Each package embeds the Python runtime, token generator, and update client. The helper must run silently, with an optional tray icon for manual quit/update.

## Security Considerations

- Bind only to `127.0.0.1`.
- Random auth token stored in OS keychain/secure storage; portal fetches it via local handshake (initial QR or user prompt).
- Validate payloads (sensor enum, baud ranges) to avoid malformed commands.
- Enforce rate limiting (e.g., maximum one command every X ms) to prevent abuse.
- No data written to disk except temporary update files.

## Next Steps

1. Fork existing Python CLI code into `helper_app/legacy/`.
2. Implement `session.py` and `serial_engine.py` with persistent connection handling.
3. Build FastAPI/Quart application with endpoints listed.
4. Add Supabase schema migration script and update client.
5. Adjust React portal to consume helper API (create detection hook, fetch wrappers, log streaming).
6. Package helper for each OS and document installation/updating steps.

Once this plan is approved, we move on to implementation starting with the helper copy and session manager.


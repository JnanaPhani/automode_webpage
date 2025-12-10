# Linux Release v1.0.0 - Zenith Tek Sensor Helper

## 🎯 Platform Exclusive
**This release is exclusive for Linux operating systems.**

## 📦 What's Included
- **ZenithHelper-x86_64.AppImage** - Portable Linux application (AppImage format)
- **PyInstaller Bundle** - Standalone executable with all dependencies
- **Systemd Service File** - Optional auto-start service for background operation
- Complete helper application with FastAPI server

## ✨ Features

### Core Functionality
- **HTTP API Server**: Runs on `http://127.0.0.1:7421` for local sensor communication
- **Sensor Support**: Configure Epson M-A542VR1 (Vibration) and M-G552PR80 (IMU) sensors
- **Persistent Serial Session**: Automatic connection management with recovery
- **WebSocket Log Streaming**: Real-time log streaming to web portal via `/logs` endpoint

### API Endpoints
- `POST /pair` - One-time pairing to retrieve auth token
- `GET /status` - Check helper and connection status
- `POST /connect` - Connect to sensor via serial port
- `POST /detect` - Detect sensor identity and type
- `POST /configure` - Configure sensor settings
- `POST /exit-auto` - Exit auto mode
- `POST /reset` - Reset sensor
- `GET /update` - Check for updates
- `POST /update/download` - Download update packages

### Packaging & Distribution
- **AppImage Format**: Portable, no installation required
- **PyInstaller Bundle**: Self-contained executable with embedded Python runtime
- **Systemd Integration**: Optional user service for background operation
- **Update Mechanism**: Automatic update checking via Supabase

## 🚀 Installation

### Option 1: AppImage (Recommended)
1. Download `ZenithHelper-x86_64.AppImage`
2. Make it executable:
   ```bash
   chmod +x ZenithHelper-x86_64.AppImage
   ```
3. Run directly:
   ```bash
   ./ZenithHelper-x86_64.AppImage
   ```

### Option 2: PyInstaller Bundle
1. Extract the bundle from `helper_app/dist/linux/zenith-helper/`
2. Run the executable:
   ```bash
   ./zenith-helper
   ```

### Option 3: Systemd Service (Background Operation)
1. Copy bundle to desired location:
   ```bash
   mkdir -p ~/.zenith-helper
   cp -r helper_app/dist/linux/zenith-helper ~/.zenith-helper/
   ```
2. Install systemd service:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp helper_app/packaging/linux/zenith-helper.service ~/.config/systemd/user/
   ```
3. Enable and start the service:
   ```bash
   systemctl --user enable --now zenith-helper.service
   ```
4. View logs:
   ```bash
   journalctl --user -u zenith-helper.service -f
   ```

## 📋 System Requirements
- Linux x86_64 (64-bit)
- Python 3.11+ (for building from source)
- USB port for sensor connection
- No root privileges required (runs as user service)

## 🔧 Configuration

### Environment Variables
Set these in your environment or `.env` file:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZENITH_SUPABASE_URL` | – | Supabase project URL for update manifests |
| `ZENITH_SUPABASE_ANON_KEY` | – | Public anon key for Supabase REST requests |
| `ZENITH_HELPER_UPDATES_DIR` | `~/.zenith_helper/updates` | Directory for downloaded installers |
| `ZENITH_HELPER_UPDATE_POLL_INTERVAL` | `21600` (6h) | Background polling interval (seconds) |
| `ZENITH_HELPER_ALLOWED_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed web origins |
| `ZENITH_HELPER_HOST` | `127.0.0.1` | Network binding host |
| `ZENITH_HELPER_PORT` | `7421` | Network binding port |
| `ZENITH_HELPER_BAUD` | `460800` | Default serial baud rate |
| `ZENITH_HELPER_LOG_LEVEL` | `INFO` | Root log level |

### Authentication
- API token is automatically generated and stored at `~/.zenith_helper_token`
- Include header `X-Zenith-Token: <token>` in all API requests
- Use `/pair` endpoint for one-time token retrieval

## 🔨 Building from Source

### Prerequisites
```bash
python3 -m venv .packaging-venv
source .packaging-venv/bin/activate
pip install -r helper_app/requirements.txt
pip install pyinstaller
```

### Build PyInstaller Bundle
```bash
python helper_app/scripts/package_linux.py
```

### Build AppImage
```bash
python helper_app/scripts/build_appimage.py
```

Output will be in `helper_app/dist/linux/`:
- `zenith-helper/` - PyInstaller bundle
- `ZenithHelper-x86_64.AppImage` - AppImage wrapper

## 🔗 Integration
The helper service integrates with the Zenith Tek web portal to provide:
- Local sensor communication without Web Serial API
- Background operation for continuous sensor monitoring
- Automatic update checking and downloading
- Real-time log streaming to the web interface

## 🐛 Known Issues
- None at this time

## 📝 Notes
- This is a Linux-only release
- The helper runs as a local service on `127.0.0.1:7421`
- All dependencies are bundled - no system Python installation required
- For Windows or macOS support, please check other releases

## 🔗 Related Resources
- Web Portal: [Zenith Tek Sensor Configuration Portal](https://your-portal-url)
- Documentation: See `helper_app/README.md` and `helper_app/packaging/linux/README.md`
- Systemd Service: `helper_app/packaging/linux/zenith-helper.service`


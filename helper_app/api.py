"""FastAPI application that exposes helper commands."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from helper_app import version
from helper_app.auth import TOKEN, verify_token
from helper_app.config import HelperSettings
from helper_app.controller import CommandResult, DetectionResult, SensorController, SensorType
from helper_app.logging_utils import BroadcastHandler, LogBroadcaster
from helper_app.session import SerialSession
from helper_app.updater import DownloadResult, UpdateInfo, check_for_updates, download_update

try:
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - fallback if pyserial missing
    list_ports = None

LOG = logging.getLogger(__name__)


def create_app(allowed_origins: Optional[List[str]] = None) -> FastAPI:
    settings = HelperSettings.from_env()
    broadcaster = LogBroadcaster()

    root_logger = logging.getLogger()
    try:
        resolved_level = getattr(logging, settings.log_level.upper())
    except AttributeError:
        resolved_level = logging.INFO
    root_logger.setLevel(resolved_level)
    root_logger.addHandler(BroadcastHandler(broadcaster))

    session = SerialSession(settings)
    controller = SensorController(session, broadcaster)

    app = FastAPI(title="Zenith Tek Sensor Helper", version=version.__version__)
    latest_update: Dict[str, UpdateInfo] = {}
    update_task: Optional[asyncio.Task[None]] = None

    def canonical_key(value: Optional[str]) -> str:
        raw = (value or "default").strip()
        return raw.lower() or "default"

    async def refresh_update(platform_hint: Optional[str]) -> Optional[UpdateInfo]:
        if not settings.supabase_url or not settings.supabase_anon_key:
            return None
        update = await check_for_updates(
            settings.supabase_url, settings.supabase_anon_key, version.__version__, platform_hint
        )
        if update:
            latest_update[canonical_key(platform_hint)] = update
        return update

    if allowed_origins is not None and len(allowed_origins) > 0:
        cors_origins = [origin.rstrip("/") for origin in allowed_origins]
    else:
        cors_origins = [origin.rstrip("/") for origin in settings.allowed_origins]
    allowed_pair_origins = {origin.rstrip("/") for origin in cors_origins}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def start_update_poll() -> None:
        nonlocal update_task
        if not settings.supabase_url or not settings.supabase_anon_key:
            return

        async def _poll_loop() -> None:
            platforms_to_query: List[Optional[str]] = [None, "windows", "macos", "linux"]
            try:
                import platform as _platform

                system_platform = _platform.system()
                if system_platform:
                    platforms_to_query.append(system_platform)
            except Exception:  # pragma: no cover - platform module shouldn't fail
                pass

            while True:
                for platform_hint in platforms_to_query:
                    try:
                        await refresh_update(platform_hint)
                    except Exception as exc:  # pragma: no cover - defensive
                        LOG.warning("Background update poll failed: %s", exc)
                await asyncio.sleep(settings.update_poll_interval)

        update_task = asyncio.create_task(_poll_loop())

    @app.on_event("shutdown")
    async def stop_update_poll() -> None:
        nonlocal update_task
        if update_task:
            update_task.cancel()
            with suppress(asyncio.CancelledError):
                await update_task
            update_task = None

    @app.post("/pair")
    async def pair(request: Request) -> Dict[str, str]:
        origin_header = request.headers.get("origin") or request.headers.get("referer")
        if origin_header:
            parsed = urlparse(origin_header)
            base_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else origin_header
            if base_origin.rstrip("/") not in allowed_pair_origins:
                LOG.warning("Pair request rejected for origin %s", origin_header)
                raise HTTPException(status_code=403, detail="Origin not allowed")
        return {"token": TOKEN}

    @app.options("/status")
    async def options_status() -> Dict[str, Any]:
        return {}

    @app.get("/status")
    async def status(platform: Optional[str] = None, token: None = Depends(verify_token)) -> Dict[str, Any]:
        nonlocal latest_update
        key = canonical_key(platform)
        if settings.supabase_url and settings.supabase_anon_key and key not in latest_update:
            await refresh_update(platform)

        response: Dict[str, Any] = {
            "version": version.__version__,
            "connected": session.is_connected(),
            "port": session.port,
            "baudRate": session.baudrate,
        }
        update = latest_update.get(key)
        if update:
            response["updateAvailable"] = {
                "version": update.version,
                "downloadUrl": update.download_url,
                "checksum": update.checksum,
                "releaseNotes": update.release_notes,
            }
        else:
            response["updateAvailable"] = None
        return response

    @app.post("/update")
    async def trigger_update_check(payload: Dict[str, Any] | None = None, token: None = Depends(verify_token)) -> Dict[str, Any]:
        nonlocal latest_update
        if not settings.supabase_url or not settings.supabase_anon_key:
            return {"updateAvailable": None}
        request_platform = (payload or {}).get("platform")
        update = await refresh_update(request_platform)
        key = canonical_key(request_platform)
        if update:
            return {
                "updateAvailable": {
                    "version": update.version,
                    "downloadUrl": update.download_url,
                    "checksum": update.checksum,
                    "releaseNotes": update.release_notes,
                }
            }
        return {"updateAvailable": None}

    @app.post("/update/download")
    async def download_update_package(
        payload: Dict[str, Any] | None = None, token: None = Depends(verify_token)
    ) -> Dict[str, Any]:
        nonlocal latest_update
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise HTTPException(status_code=400, detail="Update service not configured")

        request_platform = (payload or {}).get("platform")
        key = canonical_key(request_platform)
        update = latest_update.get(key)
        if update is None:
            update = await refresh_update(request_platform)
            if update is None:
                raise HTTPException(status_code=404, detail="No update available")

        try:
            result: DownloadResult = await download_update(update, settings.updates_dir)
        except ValueError as exc:
            LOG.warning("Update download checksum failure: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))
        except Exception as exc:
            LOG.exception("Update download failed")
            raise HTTPException(status_code=500, detail="Failed to download update") from exc

        return {
            "version": result.version,
            "path": str(result.path),
            "bytes": result.bytes_downloaded,
            "checksumVerified": result.checksum_verified,
            "updatesDir": str(settings.updates_dir),
        }

    @app.post("/connect")
    async def connect(payload: Dict[str, Any], token: None = Depends(verify_token)) -> Dict[str, Any]:
        port = payload.get("port")
        baud = payload.get("baudRate")
        if not port:
            raise HTTPException(status_code=400, detail="port is required")
        try:
            await session.connect(port=port, baud=baud)
        except RuntimeError as exc:
            LOG.error("Connect failed for port %s: %s", port, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"connected": True, "port": port, "baudRate": session.baudrate}

    @app.get("/ports")
    async def list_available_ports(token: None = Depends(verify_token)) -> Dict[str, Any]:
        if list_ports is None:
            raise HTTPException(status_code=500, detail="pyserial tools not available")
        ports: List[Dict[str, Any]] = []
        for port in list_ports.comports():
            ports.append(
                {
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid,
                    "manufacturer": port.manufacturer,
                    "vid": port.vid,
                    "pid": port.pid,
                    "serialNumber": port.serial_number,
                }
            )
        return {"ports": ports}

    @app.post("/disconnect")
    async def disconnect(token: None = Depends(verify_token)) -> Dict[str, Any]:
        await session.disconnect()
        return {"connected": False}

    @app.post("/detect")
    async def detect(payload: Dict[str, Any], token: None = Depends(verify_token)) -> DetectionResult:
        sensor: SensorType = payload.get("sensor")
        if sensor not in ("vibration", "imu"):
            raise HTTPException(status_code=400, detail="sensor field is required and must be vibration or imu")
        result = await controller.detect(sensor)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message or "Detection failed")
        return {
            "success": True,
            "sensor_type": result.sensor_type,
            "sensorType": result.sensor_type,
            "product_id": result.product_id,
            "productId": result.product_id,
            "product_id_raw": result.product_id_raw,
            "productIdRaw": result.product_id_raw,
            "serial_number": result.serial_number,
            "serialNumber": result.serial_number,
            "message": result.message,
        }

    @app.post("/configure")
    async def configure(payload: Dict[str, Any], token: None = Depends(verify_token)) -> CommandResult:
        sensor: SensorType = payload.get("sensor", "vibration")
        if sensor not in ("vibration", "imu"):
            raise HTTPException(status_code=400, detail="Invalid sensor type")
        config_kwargs = dict(payload)
        config_kwargs.pop("sensor", None)
        result = await controller.configure(sensor, **config_kwargs)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        return result

    @app.post("/exit-auto")
    async def exit_auto(payload: Dict[str, Any], token: None = Depends(verify_token)) -> CommandResult:
        sensor: SensorType = payload.get("sensor", "vibration")
        persist = payload.get("persist", True)
        if sensor not in ("vibration", "imu"):
            raise HTTPException(status_code=400, detail="Invalid sensor type")
        result = await controller.exit_auto(sensor, persist=persist)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        return result

    @app.post("/reset")
    async def full_reset(payload: Dict[str, Any], token: None = Depends(verify_token)) -> CommandResult:
        sensor: SensorType = payload.get("sensor", "vibration")
        if sensor not in ("vibration", "imu"):
            raise HTTPException(status_code=400, detail="Invalid sensor type")
        result = await controller.full_reset(sensor)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        return result

    @app.websocket("/logs")
    async def logs_socket(websocket: WebSocket) -> None:
        token = websocket.query_params.get("token")
        if token != TOKEN:
            await websocket.close(code=4401, reason="Unauthorized")
            return
        await websocket.accept()
        subscriber_id, queue = await broadcaster.attach()
        try:
            while True:
                entry = await queue.get()
                await websocket.send_json(entry)
        except WebSocketDisconnect:
            LOG.debug("WebSocket disconnected")
        finally:
            await broadcaster.detach(subscriber_id)

    return app



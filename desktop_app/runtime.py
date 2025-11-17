from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Optional

from PySide6 import QtCore
from serial.tools import list_ports

from helper_app.config import HelperSettings
from helper_app.controller import CommandResult, DetectionResult, SensorController, SensorType
from helper_app.logging_utils import BroadcastHandler, LogBroadcaster
from helper_app.session import SerialSession


LOG = logging.getLogger(__name__)


class SignalLogHandler(logging.Handler):
    """Forward log lines to a Qt signal."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - Qt side effect
        try:
            message = self.format(record)
            self._callback(message)
        except Exception:
            pass


@dataclass
class DeviceIdentity:
    sensor_type: Optional[SensorType] = None
    product_id: Optional[str] = None
    product_id_raw: Optional[str] = None
    serial_number: Optional[str] = None


class HelperRuntime(QtCore.QObject):
    """Bridge between the PySide UI and the async helper logic."""

    stateChanged = QtCore.Signal(bool, str, int)
    detectionFinished = QtCore.Signal(object)
    commandFinished = QtCore.Signal(str, object)
    operationFailed = QtCore.Signal(str, str)
    logMessage = QtCore.Signal(str)
    portsUpdated = QtCore.Signal(list)
    autoModeDetected = QtCore.Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._settings: Optional[HelperSettings] = None
        self._session: Optional[SerialSession] = None
        self._controller: Optional[SensorController] = None
        self._broadcaster = LogBroadcaster()
        handler = BroadcastHandler(self._broadcaster)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logging.getLogger().addHandler(handler)
        qt_handler = SignalLogHandler(self.logMessage.emit)
        qt_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(qt_handler)
        logging.getLogger().setLevel(logging.INFO)

        init_future = asyncio.run_coroutine_threadsafe(self._initialize(), self._loop)
        init_future.result()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _initialize(self) -> None:
        self._settings = HelperSettings.from_env()
        self._session = SerialSession(self._settings)
        self._controller = SensorController(self._session, self._broadcaster)
        self.publish_ports()

    # Utility -----------------------------------------------------------------
    def _ensure_ready(self) -> None:
        if not self._session or not self._controller:
            raise RuntimeError("Helper runtime not initialized")

    def publish_ports(self) -> None:
        devices = []
        try:
            for port in list_ports.comports():
                devices.append(
                    {
                        "device": port.device,
                        "description": port.description,
                        "hwid": port.hwid,
                    }
                )
        except Exception as exc:
            LOG.warning("Failed to list ports: %s", exc)
        self.portsUpdated.emit(devices)

    def _run_async_operation(self, name: str, coro):
        def _runner() -> None:
            try:
                result = asyncio.run_coroutine_threadsafe(coro, self._loop).result()
                self.commandFinished.emit(name, result)
            except Exception as exc:
                LOG.error("%s failed: %s", name, exc)
                self.operationFailed.emit(name, str(exc))

        threading.Thread(target=_runner, daemon=True).start()

    # Public actions ----------------------------------------------------------
    def connect_port(self, port: str, baud: Optional[int]) -> None:
        self._ensure_ready()
        assert self._session
        async def _do_connect() -> None:
            await self._session.connect(port=port, baud=baud)
            connected = self._session.is_connected()
            self.stateChanged.emit(connected, self._session.port or "", self._session.baudrate)
        self._run_async_operation("connect", _do_connect())

    def disconnect_port(self) -> None:
        self._ensure_ready()
        assert self._session
        async def _do_disconnect() -> None:
            await self._session.disconnect()
            self.stateChanged.emit(False, "", self._session.baudrate)
        self._run_async_operation("disconnect", _do_disconnect())

    def check_auto_mode(self, sensor: SensorType) -> None:
        """Check if sensor is in auto mode and emit signal."""
        self._ensure_ready()
        assert self._controller
        async def _do_check() -> bool:
            return await self._controller.check_auto_mode(sensor)
        def _runner() -> None:
            try:
                is_auto = asyncio.run_coroutine_threadsafe(_do_check(), self._loop).result()
                self.autoModeDetected.emit(is_auto)
            except Exception as exc:
                LOG.debug("Auto mode check failed: %s", exc)
                self.autoModeDetected.emit(False)
        threading.Thread(target=_runner, daemon=True).start()

    def detect(self, sensor: SensorType) -> None:
        self._ensure_ready()
        assert self._controller
        async def _do_detect() -> DetectionResult:
            return await self._controller.detect(sensor)
        def _runner() -> None:
            try:
                result = asyncio.run_coroutine_threadsafe(_do_detect(), self._loop).result()
                if not result.success:
                    raise RuntimeError(result.message or "Detection failed")
                identity = DeviceIdentity(
                    sensor_type=result.sensor_type,
                    product_id=result.product_id,
                    product_id_raw=result.product_id_raw,
                    serial_number=result.serial_number,
                )
                self.detectionFinished.emit(identity)
            except Exception as exc:
                LOG.error("Detection failed: %s", exc)
                self.operationFailed.emit("detect", str(exc))
        threading.Thread(target=_runner, daemon=True).start()

    def configure(self, sensor: SensorType) -> None:
        self._run_command("configure", sensor)

    def exit_auto(self, sensor: SensorType) -> None:
        self._run_command("exit_auto", sensor)

    def full_reset(self, sensor: SensorType) -> None:
        self._run_command("full_reset", sensor)

    def _run_command(self, command: str, sensor: SensorType) -> None:
        self._ensure_ready()
        assert self._controller
        async def _do_command() -> CommandResult:
            if command == "configure":
                return await self._controller.configure(sensor)
            if command == "exit_auto":
                return await self._controller.exit_auto(sensor)
            if command == "full_reset":
                return await self._controller.full_reset(sensor)
            raise RuntimeError(f"Unknown command: {command}")

        self._run_async_operation(command, _do_command())

    def shutdown(self) -> None:
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=1.0)



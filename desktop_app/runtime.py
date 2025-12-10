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

    def _run_async_operation(self, name: str, coro, timeout: Optional[float] = None):
        def _runner() -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(coro, self._loop)
                # Use timeout to prevent indefinite blocking (especially important for disconnect)
                if timeout is not None:
                    result = future.result(timeout=timeout)
                else:
                    # For disconnect, use a shorter timeout to prevent freezing
                    if name == "disconnect":
                        result = future.result(timeout=5.0)  # 5 second timeout for disconnect
                    else:
                        result = future.result(timeout=30.0)  # 30 second timeout for other operations
                self.commandFinished.emit(name, result)
            except asyncio.TimeoutError:
                LOG.error("%s operation timed out after %s seconds", name, timeout or (5.0 if name == "disconnect" else 30.0))
                self.operationFailed.emit(name, f"Operation timed out - the operation may still be in progress")
            except Exception as exc:
                LOG.error("%s failed: %s", name, exc)
                self.operationFailed.emit(name, str(exc))

        threading.Thread(target=_runner, daemon=True).start()

    # Public actions ----------------------------------------------------------
    def connect_port(self, port: str, baud: Optional[int]) -> None:
        self._ensure_ready()
        assert self._session
        async def _do_connect() -> None:
            # Add timeout to connect operation
            await asyncio.wait_for(self._session.connect(port=port, baud=baud), timeout=10.0)
            connected = self._session.is_connected()
            self.stateChanged.emit(connected, self._session.port or "", self._session.baudrate)
        self._run_async_operation("connect", _do_connect(), timeout=12.0)

    def disconnect_port(self) -> None:
        self._ensure_ready()
        assert self._session
        async def _do_disconnect() -> None:
            try:
                # Use asyncio.wait_for to add a timeout to the disconnect operation
                await asyncio.wait_for(self._session.disconnect(), timeout=4.0)
                self.stateChanged.emit(False, "", self._session.baudrate)
            except asyncio.TimeoutError:
                LOG.warning("Disconnect timed out - forcing state update")
                # Force state update even if disconnect timed out
                self.stateChanged.emit(False, "", self._session.baudrate)
                raise
        self._run_async_operation("disconnect", _do_disconnect(), timeout=5.0)

    def check_auto_mode(self, sensor: SensorType) -> None:
        """Check if sensor is in auto mode and emit signal."""
        self._ensure_ready()
        assert self._controller
        async def _do_check() -> bool:
            # Add timeout to auto mode check
            return await asyncio.wait_for(self._controller.check_auto_mode(sensor), timeout=5.0)
        def _runner() -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(_do_check(), self._loop)
                is_auto = future.result(timeout=6.0)  # 6 second timeout for auto mode check
                self.autoModeDetected.emit(is_auto)
            except (asyncio.TimeoutError, Exception) as exc:
                LOG.debug("Auto mode check failed or timed out: %s", exc)
                self.autoModeDetected.emit(False)
        threading.Thread(target=_runner, daemon=True).start()

    def detect(self, sensor: SensorType) -> None:
        self._ensure_ready()
        assert self._controller
        async def _do_detect() -> DetectionResult:
            # Add timeout to detection operation to prevent hanging
            return await asyncio.wait_for(self._controller.detect(sensor), timeout=30.0)
        def _runner() -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(_do_detect(), self._loop)
                result = future.result(timeout=35.0)  # 35 second timeout for detection
                if not result.success:
                    raise RuntimeError(result.message or "Detection failed")
                identity = DeviceIdentity(
                    sensor_type=result.sensor_type,
                    product_id=result.product_id,
                    product_id_raw=result.product_id_raw,
                    serial_number=result.serial_number,
                )
                self.detectionFinished.emit(identity)
            except asyncio.TimeoutError:
                LOG.error("Detection operation timed out after 35 seconds")
                self.operationFailed.emit("detect", "Detection timed out - the sensor may not be responding. Please check the connection and try again.")
            except Exception as exc:
                LOG.error("Detection failed: %s", exc)
                self.operationFailed.emit("detect", str(exc))
        threading.Thread(target=_runner, daemon=True).start()

    def configure(self, sensor: SensorType, sampling_rate: Optional[float] = None, tap_value: Optional[int] = None, sps_rate: Optional[int] = None) -> None:
        self._run_command("configure", sensor, sampling_rate=sampling_rate, tap_value=tap_value, sps_rate=sps_rate)

    def exit_auto(self, sensor: SensorType) -> None:
        self._run_command("exit_auto", sensor)

    def full_reset(self, sensor: SensorType) -> None:
        self._run_command("full_reset", sensor)

    def _run_command(self, command: str, sensor: SensorType, **kwargs) -> None:
        self._ensure_ready()
        assert self._controller
        async def _do_command() -> CommandResult:
            if command == "configure":
                return await self._controller.configure(sensor, **kwargs)
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



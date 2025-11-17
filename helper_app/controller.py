"""High-level command controller wrapping legacy configurator logic."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional

from helper_app.logging_utils import LogBroadcaster
from helper_app.session import SerialSession

from helper_app.legacy.vibration.sensor_config import SensorConfigurator as VibrationConfigurator
from helper_app.legacy.vibration.sensor_comm import SensorCommunication as VibrationComm
from helper_app.legacy.imu.sensor_config import SensorConfigurator as ImuConfigurator
from helper_app.legacy.imu.sensor_comm import SensorCommunication as ImuComm

SensorType = Literal["vibration", "imu"]
LOG = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    success: bool
    sensor_type: Optional[SensorType] = None
    product_id: Optional[str] = None
    serial_number: Optional[str] = None
    product_id_raw: Optional[str] = None
    message: Optional[str] = None


@dataclass
class CommandResult:
    success: bool
    message: str
    requires_restart: bool = False
    warning: Optional[str] = None


class SensorController:
    """Expose sensor commands through the shared serial session."""

    def __init__(self, session: SerialSession, broadcaster: LogBroadcaster) -> None:
        self._session = session
        self._broadcaster = broadcaster

    def _collect_warning(self, configurator: Any) -> Optional[str]:
        collector = getattr(configurator, "collect_warnings", None)
        if callable(collector):
            warnings = [w for w in collector() if w]
            if warnings:
                unique: list[str] = []
                for entry in warnings:
                    if entry not in unique:
                        unique.append(entry)
                return " ".join(unique)
        return None

    async def detect(self, sensor: SensorType) -> DetectionResult:
        loop = asyncio.get_running_loop()
        port = self._session.port
        baud = self._session.baudrate
        if not port:
            return DetectionResult(success=False, message="Serial port is not connected.")

        await self._session.disconnect()
        # Give Windows time to release the port
        await asyncio.sleep(0.5)

        def _detect_with_fresh_connection():
            comm_cls = VibrationComm if sensor == "vibration" else ImuComm
            configurator_cls = VibrationConfigurator if sensor == "vibration" else ImuConfigurator
            comm = comm_cls(port=port, baud=baud)
            # Retry opening the port in case Windows hasn't released it yet
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    comm.open()
                    break
                except Exception as exc:
                    if attempt < max_retries - 1:
                        time.sleep(0.3)
                        continue
                    raise
            try:
                configurator = configurator_cls(comm)
                info = configurator.detect_identity()
                if not info:
                    raise RuntimeError("Unable to determine sensor identity from response.")
                product_raw = (info.get("product_id_raw") or "").strip()
                serial = (info.get("serial_number") or "").strip()
                if len(product_raw) < 4 and len(serial) < 4:
                    raise RuntimeError("Unable to determine sensor identity from response.")
                return info
            finally:
                comm.close()
                # Give Windows time to release before reconnecting
                time.sleep(0.3)

        try:
            info = await loop.run_in_executor(None, _detect_with_fresh_connection)
            return DetectionResult(
                success=True,
                sensor_type=sensor,
                product_id=info.get("product_id"),
                product_id_raw=info.get("product_id_raw"),
                serial_number=info.get("serial_number"),
                message="Sensor identity retrieved successfully.",
            )
        except Exception as exc:
            LOG.exception("Detect failed", exc_info=True)
            return DetectionResult(success=False, message=str(exc))
        finally:
            # Wait a bit more before reconnecting to ensure port is fully released
            await asyncio.sleep(0.3)
            try:
                await self._session.connect(port=port, baud=baud)
            except Exception as reconnect_exc:
                LOG.error("Failed to restore serial connection: %s", reconnect_exc)

    async def configure(self, sensor: SensorType, **kwargs) -> CommandResult:
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
            # Extract sampling_rate and tap_value for IMU
            if sensor == "imu":
                sampling_rate = kwargs.get("sampling_rate", 125.0)
                tap_value = kwargs.get("tap_value")
                success = configurator.configure(sampling_rate=sampling_rate, tap_value=tap_value)
            else:
                success = configurator.configure()
            warning = self._collect_warning(configurator)
            if not success:
                return CommandResult(False, "Configuration failed. Check logs for details.", warning=warning)
            return CommandResult(True, "Configuration completed successfully.", requires_restart=True, warning=warning)

        try:
            LOG.info("Configure command requested for sensor=%s", sensor)
            if sensor == "vibration":
                return await self._session.run(lambda comm: _run(comm, VibrationConfigurator))
            return await self._session.run(lambda comm: _run(comm, ImuConfigurator))
        except Exception as exc:  # pragma: no cover
            LOG.exception("Configure failed: %s", exc)
            return CommandResult(False, str(exc))

    async def check_auto_mode(self, sensor: SensorType) -> bool:
        """Check if the sensor is currently in auto mode.
        
        Returns:
            True if sensor is in auto mode, False otherwise
        """
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
            return configurator.check_auto_mode()

        try:
            if sensor == "vibration":
                return await self._session.run(lambda comm: _run(comm, VibrationConfigurator))
            return await self._session.run(lambda comm: _run(comm, ImuConfigurator))
        except Exception as exc:
            LOG.debug("Failed to check auto mode: %s", exc)
            return False

    async def exit_auto(self, sensor: SensorType, persist: bool = True) -> CommandResult:
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
            success = configurator.exit_auto_mode(persist_disable_auto=persist)
            warning = self._collect_warning(configurator)
            if not success:
                return CommandResult(False, "Failed to disable auto mode.", warning=warning)
            return CommandResult(True, "Auto mode disabled successfully.", warning=warning)

        try:
            LOG.info("Exit auto command requested for sensor=%s persist=%s", sensor, persist)
            if sensor == "vibration":
                return await self._session.run(lambda comm: _run(comm, VibrationConfigurator))
            return await self._session.run(lambda comm: _run(comm, ImuConfigurator))
        except Exception as exc:
            LOG.exception("Exit auto failed: %s", exc)
            return CommandResult(False, str(exc))

    async def full_reset(self, sensor: SensorType) -> CommandResult:
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
            success = configurator.full_reset(persist_disable_auto=True)
            warning = self._collect_warning(configurator)
            if not success:
                return CommandResult(False, "Full reset failed.", warning=warning)
            return CommandResult(True, "Full reset completed successfully.", requires_restart=True, warning=warning)

        try:
            LOG.info("Full reset command requested for sensor=%s", sensor)
            if sensor == "vibration":
                return await self._session.run(lambda comm: _run(comm, VibrationConfigurator))
            return await self._session.run(lambda comm: _run(comm, ImuConfigurator))
        except Exception as exc:
            LOG.exception("Full reset failed: %s", exc)
            return CommandResult(False, str(exc))



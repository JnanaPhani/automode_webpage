"""High-level command controller wrapping legacy configurator logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

from helper_app.logging_utils import LogBroadcaster
from helper_app.session import SerialSession

from helper_app.legacy.vibration.sensor_config import SensorConfigurator as VibrationConfigurator
from helper_app.legacy.imu.sensor_config import SensorConfigurator as ImuConfigurator

SensorType = Literal["vibration", "imu"]
LOG = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    success: bool
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
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
            info = configurator.detect_identity()
            if not info:
                raise RuntimeError("Identity read failed")
            return info

        try:
            LOG.info("Detect command requested for sensor=%s", sensor)
            if sensor == "vibration":
                info = await self._session.run(lambda comm: _run(comm, VibrationConfigurator))
            else:
                info = await self._session.run(lambda comm: _run(comm, ImuConfigurator))
            return DetectionResult(
                success=True,
                product_id=info.get("product_id"),
                product_id_raw=info.get("product_id_raw"),
                serial_number=info.get("serial_number"),
                message="Sensor identity retrieved successfully.",
            )
        except Exception as exc:  # pragma: no cover - legacy logic exceptions
            LOG.exception("Detect failed", exc_info=True)
            return DetectionResult(success=False, message=f"Identity read failed: {exc}")

    async def configure(self, sensor: SensorType, **kwargs) -> CommandResult:
        def _run(comm, configurator_cls):
            configurator = configurator_cls(comm)
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



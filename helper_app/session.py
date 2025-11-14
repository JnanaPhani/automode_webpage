"""Serial session manager that keeps a persistent connection to the sensor."""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional, TypeVar

from helper_app.config import HelperSettings
from helper_app.legacy.vibration.sensor_comm import SensorCommunication

LOG = logging.getLogger(__name__)
T = TypeVar("T")


class SerialSession:
    """Maintain a single persistent serial connection with background draining."""

    def __init__(self, settings: HelperSettings | None = None) -> None:
        self._settings = settings or HelperSettings.from_env()
        self._port: Optional[str] = None
        self._baud: int = self._settings.default_baud_rate
        self._comm: Optional[SensorCommunication] = None
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="serial-session")
        self._drain_stop = threading.Event()
        self._drain_thread: Optional[threading.Thread] = None

    async def connect(self, port: str, baud: Optional[int] = None) -> None:
        """Open or re-open the serial connection with the specified port."""

        async with self._lock:
            target_baud = baud or self._settings.default_baud_rate

            if self._comm and self._port == port and self._baud == target_baud and self._comm.is_open():
                LOG.debug("SerialSession: already connected to %s @ %s", port, target_baud)
                return

            await self._close_locked()

            self._port = port
            self._baud = target_baud
            self._comm = SensorCommunication(port=port, baud=target_baud)
            await asyncio.get_running_loop().run_in_executor(self._executor, self._comm.open)
            LOG.info("SerialSession: connected to %s @ %s baud", port, target_baud)
            self._start_drain_locked()

    async def disconnect(self) -> None:
        """Close the serial connection and stop background tasks."""
        async with self._lock:
            await self._close_locked()
            self._port = None
            self._baud = self._settings.default_baud_rate

    def is_connected(self) -> bool:
        """Return True if the underlying serial connection is active."""
        return self._comm is not None and self._comm.is_open()

    @property
    def port(self) -> Optional[str]:
        return self._port

    @property
    def baudrate(self) -> int:
        return self._baud

    async def run(self, func: Callable[[SensorCommunication], T]) -> T:
        """Run a blocking operation using the live serial connection."""
        async with self._lock:
            if not self._comm or not self._comm.is_open():
                if not self._port:
                    raise RuntimeError("Serial port is not connected")
                self._comm = SensorCommunication(port=self._port, baud=self._baud)
                await asyncio.get_running_loop().run_in_executor(self._executor, self._comm.open)
                self._start_drain_locked()

            self._stop_drain_locked()
            if self._comm and self._comm.is_open():
                try:
                    serial_conn = self._comm.connection  # type: ignore[attr-defined]
                    if serial_conn is not None and hasattr(serial_conn, "reset_input_buffer"):
                        serial_conn.reset_input_buffer()  # type: ignore[call-arg]
                        if hasattr(serial_conn, "reset_output_buffer"):
                            serial_conn.reset_output_buffer()  # type: ignore[call-arg]
                except Exception as exc:  # pragma: no cover - defensive
                    LOG.warning("SerialSession: failed to flush buffers before command: %s", exc)
            try:
                return await asyncio.get_running_loop().run_in_executor(self._executor, func, self._comm)
            finally:
                self._start_drain_locked()

    async def _close_locked(self) -> None:
        if self._comm:
            self._stop_drain_locked()
            await asyncio.get_running_loop().run_in_executor(self._executor, self._comm.close)
            LOG.info("SerialSession: disconnected")
        self._comm = None

    def _start_drain_locked(self) -> None:
        if not self._comm or not self._comm.is_open():
            return
        if self._drain_thread and self._drain_thread.is_alive():
            return

        self._drain_stop.clear()

        def _drain_loop() -> None:
            LOG.debug("SerialSession: drain loop started")
            while not self._drain_stop.is_set():
                try:
                    if self._comm and self._comm.is_open():
                        # read small chunks to keep buffer clear
                        self._comm.connection.read(256)  # type: ignore[union-attr]
                    else:
                        break
                except Exception as exc:  # pragma: no cover - defensive
                    LOG.warning("SerialSession: drain loop error: %s", exc)
                    break
            LOG.debug("SerialSession: drain loop stopped")

        self._drain_thread = threading.Thread(target=_drain_loop, name="serial-drain", daemon=True)
        self._drain_thread.start()

    def _stop_drain_locked(self) -> None:
        if self._drain_thread and self._drain_thread.is_alive():
            self._drain_stop.set()
            self._drain_thread.join(timeout=1.0)
        self._drain_thread = None
        self._drain_stop.clear()



"""Structured logging helpers that push entries to subscribers."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections import deque
from typing import Deque, Dict, List, Literal, TypedDict

LogLevel = Literal["debug", "info", "warning", "error"]


class LogEntry(TypedDict):
    level: LogLevel
    timestamp: str
    message: str


class LogBroadcaster:
    """Collect log lines and stream them to async subscribers."""

    def __init__(self, max_history: int = 200) -> None:
        self._history: Deque[LogEntry] = deque(maxlen=max_history)
        self._subscribers: Dict[int, asyncio.Queue[LogEntry]] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def publish(self, level: LogLevel, message: str) -> None:
        entry: LogEntry = {
            "level": level,
            "timestamp": dt.datetime.utcnow().isoformat() + "Z",
            "message": message,
        }
        self._history.append(entry)

        async with self._lock:
            for queue in self._subscribers.values():
                await queue.put(entry)

    def publish_sync(self, level: LogLevel, message: str) -> None:
        entry: LogEntry = {
            "level": level,
            "timestamp": dt.datetime.utcnow().isoformat() + "Z",
            "message": message,
        }
        self._history.append(entry)
        if self._subscribers:
            for queue in self._subscribers.values():
                queue.put_nowait(entry)

    async def attach(self) -> tuple[int, asyncio.Queue[LogEntry]]:
        queue: asyncio.Queue[LogEntry] = asyncio.Queue()
        async with self._lock:
            subscriber_id = self._next_id
            self._next_id += 1
            self._subscribers[subscriber_id] = queue
            for entry in list(self._history):
                await queue.put(entry)
        return subscriber_id, queue

    async def detach(self, subscriber_id: int) -> None:
        async with self._lock:
            self._subscribers.pop(subscriber_id, None)


class BroadcastHandler(logging.Handler):
    """Logging handler that forwards records to the broadcaster."""

    def __init__(self, broadcaster: LogBroadcaster) -> None:
        super().__init__()
        self._broadcaster = broadcaster

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            level: LogLevel = "info"
            if record.levelno >= logging.ERROR:
                level = "error"
            elif record.levelno >= logging.WARNING:
                level = "warning"
            elif record.levelno <= logging.DEBUG:
                level = "debug"
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcaster.publish(level, message))
            except RuntimeError:
                self._broadcaster.publish_sync(level, message)
        except Exception:  # pragma: no cover - logging errors shouldn't explode
            self.handleError(record)



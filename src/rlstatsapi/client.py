from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, Awaitable, Callable

from .models import EventMessage
from ._websocket import SimpleWebSocket, connect_websocket

Handler = Callable[[EventMessage], Awaitable[None] | None]


class StatsClient:
    """High-throughput asyncio client for Rocket League Stats API."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 49123,
        reconnect: bool = True,
        reconnect_delay: float = 0.5,
        include_raw: bool = False,
        queue_size: int = 2048,
        connect_timeout: float = 5.0,
        log_enabled: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.include_raw = include_raw
        self.connect_timeout = connect_timeout
        self.log_enabled = log_enabled

        self._queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=queue_size)
        self._handlers_by_event: dict[str, list[Handler]] = defaultdict(list)
        self._handlers_any: list[Handler] = []
        self._logger = logging.getLogger("rlstatsapi")

        self._ws: SimpleWebSocket | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stopping = False

    async def connect(self) -> None:
        if self._reader_task and not self._reader_task.done():
            self._log("connect() ignored: reader already running")
            return

        self._stopping = False
        self._reader_task = asyncio.create_task(self._run(), name="rlstatsapi-reader")
        self._log("reader task started")

    async def disconnect(self) -> None:
        self._stopping = True
        self._log("disconnect requested")

        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None

        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
            self._reader_task = None
        self._log("disconnected")

    def on(self, event_name: str, handler: Handler) -> None:
        self._handlers_by_event[event_name].append(handler)

    def on_any(self, handler: Handler) -> None:
        self._handlers_any.append(handler)

    async def events(self) -> AsyncIterator[EventMessage]:
        while True:
            yield await self._queue.get()

    async def _run(self) -> None:
        while not self._stopping:
            try:
                self._log(f"connecting to ws://{self.host}:{self.port}")
                self._ws = await connect_websocket(
                    host=self.host,
                    port=self.port,
                    timeout=self.connect_timeout,
                )
                self._log("websocket connected")
                await self._read_loop(self._ws)
            except asyncio.CancelledError:
                self._log("reader task cancelled")
                raise
            except Exception as exc:
                self._log(f"connection/read error: {exc}")
                if not self.reconnect or self._stopping:
                    self._log("stopping reader (reconnect disabled or stopping)")
                    return
                self._log(f"reconnecting in {self.reconnect_delay:.2f}s")
                await asyncio.sleep(self.reconnect_delay)
            finally:
                if self._ws is not None:
                    with contextlib.suppress(Exception):
                        await self._ws.close()
                    self._ws = None
                    self._log("websocket closed")

    async def _read_loop(self, ws: SimpleWebSocket) -> None:
        while not self._stopping:
            raw = await ws.recv_text()
            message = _parse_message(raw, include_raw=self.include_raw)
            if message is None:
                self._log("ignored invalid message (json/envelope)")
                continue

            await self._queue.put(message)
            await self._dispatch(message)

    async def _dispatch(self, message: EventMessage) -> None:
        handlers = self._handlers_any + self._handlers_by_event.get(message.event, [])

        for handler in handlers:
            try:
                result = handler(message)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                # Never kill the stream because of user handlers.
                self._log(f"handler error for {message.event}: {exc}")
                continue

    def _log(self, message: str) -> None:
        if self.log_enabled:
            self._logger.info("[StatsClient] %s", message)


def _parse_message(raw: str, *, include_raw: bool) -> EventMessage | None:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None

    event = decoded.get("Event")
    data = decoded.get("Data")

    if not isinstance(event, str) or not isinstance(data, dict):
        return None

    return EventMessage(event=event, data=data, raw=raw if include_raw else None)

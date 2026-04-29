"""Core async TCP client for Rocket League's live Stats exporter.

This module handles socket lifecycle, JSON stream framing, dispatching to user
handlers, reconnect strategy, and queue backpressure behavior.
"""
from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import random
from collections import defaultdict
from typing import Any, AsyncIterator, Awaitable, Callable, Literal, overload

from .models import EventMessage
from .types import (
    BallHitPayload,
    ClockUpdatedSecondsPayload,
    CountdownBeginPayload,
    CrossbarHitPayload,
    GoalReplayEndPayload,
    GoalReplayStartPayload,
    GoalReplayWillEndPayload,
    GoalScoredPayload,
    MatchCreatedPayload,
    MatchDestroyedPayload,
    MatchEndedPayload,
    MatchInitializedPayload,
    MatchPausedPayload,
    MatchUnpausedPayload,
    PodiumStartPayload,
    ReplayCreatedPayload,
    RoundStartedPayload,
    StatfeedEventPayload,
    TypedEventMessage,
    UpdateStatePayload,
)

Handler = Callable[[EventMessage], Awaitable[None] | None]
_AnyCallable = Callable[..., Any]
_SimpleHandler = Callable[[], Awaitable[None] | None]
_ErrorHandler = Callable[[str, Exception], Awaitable[None] | None]


class StatsClient:
    """High-level event client for Rocket League Stats API."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 49123,
        reconnect: bool = True,
        reconnect_delay: float = 0.5,
        max_reconnect_delay: float = 30.0,
        max_reconnect_attempts: int | None = 5,
        include_raw: bool = False,
        queue_size: int = 2048,
        overflow: Literal["block", "drop", "raise"] = "block",
        connect_timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.include_raw = include_raw
        self.connect_timeout = connect_timeout
        self.overflow = overflow

        self._queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=queue_size)
        self._handlers_by_event: dict[str, list[_AnyCallable]] = defaultdict(list)
        self._handlers_any: list[_AnyCallable] = []
        self._on_connect_handlers: list[_SimpleHandler] = []
        self._on_disconnect_handlers: list[_SimpleHandler] = []
        self._error_handlers: list[_ErrorHandler] = []
        self._logger = logging.getLogger("rlstatsapi")

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stopping = False
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """
        Returns True if the client is currently connected to the Stats API.
        """
        return self._connected

    async def __aenter__(self) -> StatsClient:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        if self._reader_task and not self._reader_task.done():
            self._logger.debug("connect() ignored: reader already running")
            return

        self._stopping = False
        self._reader_task = asyncio.create_task(self._run(), name="rlstatsapi-reader")
        self._logger.debug("reader task started")

    async def disconnect(self) -> None:
        """
        Disconnects from the Stats API and stops the reader task.
        """
        self._stopping = True
        self._logger.debug("disconnect requested")

        if self._writer is not None:
            with contextlib.suppress(Exception):
                self._writer.close()
                await self._writer.wait_closed()
            self._writer = None
            self._reader = None

        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
            self._reader_task = None
        self._logger.debug("disconnected")

    def on_connect(self, handler: _SimpleHandler) -> None:
        """Register a callback fired after TCP connection is established."""
        self._on_connect_handlers.append(handler)

    def on_disconnect(self, handler: _SimpleHandler) -> None:
        """Register a callback fired when the active TCP session is closed."""
        self._on_disconnect_handlers.append(handler)

    def on_handler_error(self, handler: _ErrorHandler) -> None:
        """Register a callback for exceptions raised inside event handlers."""
        self._error_handlers.append(handler)

    @overload
    def on(
        self,
        event_name: Literal["UpdateState"],
        handler: Callable[
            [TypedEventMessage[UpdateStatePayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["UpdateState"]) -> Callable[
        [Callable[[TypedEventMessage[UpdateStatePayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[UpdateStatePayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["BallHit"],
        handler: Callable[[TypedEventMessage[BallHitPayload]], Awaitable[None] | None],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["BallHit"]) -> Callable[
        [Callable[[TypedEventMessage[BallHitPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[BallHitPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["ClockUpdatedSeconds"],
        handler: Callable[
            [TypedEventMessage[ClockUpdatedSecondsPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["ClockUpdatedSeconds"]) -> Callable[
        [
            Callable[
                [TypedEventMessage[ClockUpdatedSecondsPayload]], Awaitable[None] | None
            ]
        ],
        Callable[
            [TypedEventMessage[ClockUpdatedSecondsPayload]], Awaitable[None] | None
        ],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["CountdownBegin"],
        handler: Callable[
            [TypedEventMessage[CountdownBeginPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["CountdownBegin"]) -> Callable[
        [Callable[[TypedEventMessage[CountdownBeginPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[CountdownBeginPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["CrossbarHit"],
        handler: Callable[
            [TypedEventMessage[CrossbarHitPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["CrossbarHit"]) -> Callable[
        [Callable[[TypedEventMessage[CrossbarHitPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[CrossbarHitPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["GoalReplayEnd"],
        handler: Callable[
            [TypedEventMessage[GoalReplayEndPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["GoalReplayEnd"]) -> Callable[
        [Callable[[TypedEventMessage[GoalReplayEndPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[GoalReplayEndPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["GoalReplayStart"],
        handler: Callable[
            [TypedEventMessage[GoalReplayStartPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["GoalReplayStart"]) -> Callable[
        [Callable[[TypedEventMessage[GoalReplayStartPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[GoalReplayStartPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["GoalReplayWillEnd"],
        handler: Callable[
            [TypedEventMessage[GoalReplayWillEndPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["GoalReplayWillEnd"]) -> Callable[
        [
            Callable[
                [TypedEventMessage[GoalReplayWillEndPayload]], Awaitable[None] | None
            ]
        ],
        Callable[[TypedEventMessage[GoalReplayWillEndPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["GoalScored"],
        handler: Callable[
            [TypedEventMessage[GoalScoredPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["GoalScored"]) -> Callable[
        [Callable[[TypedEventMessage[GoalScoredPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[GoalScoredPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchCreated"],
        handler: Callable[
            [TypedEventMessage[MatchCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchCreated"]) -> Callable[
        [Callable[[TypedEventMessage[MatchCreatedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[MatchCreatedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchInitialized"],
        handler: Callable[
            [TypedEventMessage[MatchInitializedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchInitialized"]) -> Callable[
        [
            Callable[
                [TypedEventMessage[MatchInitializedPayload]], Awaitable[None] | None
            ]
        ],
        Callable[[TypedEventMessage[MatchInitializedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchDestroyed"],
        handler: Callable[
            [TypedEventMessage[MatchDestroyedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchDestroyed"]) -> Callable[
        [Callable[[TypedEventMessage[MatchDestroyedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[MatchDestroyedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchEnded"],
        handler: Callable[
            [TypedEventMessage[MatchEndedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchEnded"]) -> Callable[
        [Callable[[TypedEventMessage[MatchEndedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[MatchEndedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchPaused"],
        handler: Callable[
            [TypedEventMessage[MatchPausedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchPaused"]) -> Callable[
        [Callable[[TypedEventMessage[MatchPausedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[MatchPausedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["MatchUnpaused"],
        handler: Callable[
            [TypedEventMessage[MatchUnpausedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["MatchUnpaused"]) -> Callable[
        [Callable[[TypedEventMessage[MatchUnpausedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[MatchUnpausedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["PodiumStart"],
        handler: Callable[
            [TypedEventMessage[PodiumStartPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["PodiumStart"]) -> Callable[
        [Callable[[TypedEventMessage[PodiumStartPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[PodiumStartPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["ReplayCreated"],
        handler: Callable[
            [TypedEventMessage[ReplayCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["ReplayCreated"]) -> Callable[
        [Callable[[TypedEventMessage[ReplayCreatedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[ReplayCreatedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["RoundStarted"],
        handler: Callable[
            [TypedEventMessage[RoundStartedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["RoundStarted"]) -> Callable[
        [Callable[[TypedEventMessage[RoundStartedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[RoundStartedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["StatfeedEvent"],
        handler: Callable[
            [TypedEventMessage[StatfeedEventPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["StatfeedEvent"]) -> Callable[
        [Callable[[TypedEventMessage[StatfeedEventPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[StatfeedEventPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(self, event_name: str, handler: Handler) -> None: ...
    @overload
    def on(self, event_name: str) -> Callable[[Handler], Handler]: ...

    def on(self, event_name: str, handler: _AnyCallable | None = None) -> Any:
        """Register a handler for an event or return a decorator form of registration."""
        if handler is None:

            def decorator(h: _AnyCallable) -> _AnyCallable:
                self._handlers_by_event[event_name].append(h)
                return h

            return decorator
        self._handlers_by_event[event_name].append(handler)
        return None

    def on_any(self, handler: Handler) -> None:
        """Register a handler that runs for every incoming event."""
        self._handlers_any.append(handler)

    def off(self, event_name: str, handler: _AnyCallable) -> None:
        """Unregister one handler for a specific event if present."""
        handlers = self._handlers_by_event.get(event_name)
        if handlers:
            with contextlib.suppress(ValueError):
                handlers.remove(handler)

    def off_any(self, handler: _AnyCallable) -> None:
        """Unregister a global handler registered with on_any."""
        with contextlib.suppress(ValueError):
            self._handlers_any.remove(handler)

    def once(self, event_name: str, handler: _AnyCallable) -> None:
        """Register a handler that runs once and removes itself automatically."""
        async def wrapper(msg: EventMessage) -> None:
            self.off(event_name, wrapper)
            result = handler(msg)
            if inspect.isawaitable(result):
                await result

        self._handlers_by_event[event_name].append(wrapper)

    def on_update_state(
        self,
        handler: Callable[
            [TypedEventMessage[UpdateStatePayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering UpdateState handlers."""
        self._handlers_by_event["UpdateState"].append(handler)

    def on_ball_hit(
        self,
        handler: Callable[[TypedEventMessage[BallHitPayload]], Awaitable[None] | None],
    ) -> None:
        """Typed helper for registering BallHit handlers."""
        self._handlers_by_event["BallHit"].append(handler)

    def on_clock_updated_seconds(
        self,
        handler: Callable[
            [TypedEventMessage[ClockUpdatedSecondsPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering ClockUpdatedSeconds handlers."""
        self._handlers_by_event["ClockUpdatedSeconds"].append(handler)

    def on_countdown_begin(
        self,
        handler: Callable[
            [TypedEventMessage[CountdownBeginPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering CountdownBegin handlers."""
        self._handlers_by_event["CountdownBegin"].append(handler)

    def on_crossbar_hit(
        self,
        handler: Callable[
            [TypedEventMessage[CrossbarHitPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering CrossbarHit handlers."""
        self._handlers_by_event["CrossbarHit"].append(handler)

    def on_goal_replay_end(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayEndPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering GoalReplayEnd handlers."""
        self._handlers_by_event["GoalReplayEnd"].append(handler)

    def on_goal_replay_start(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayStartPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering GoalReplayStart handlers."""
        self._handlers_by_event["GoalReplayStart"].append(handler)

    def on_goal_replay_will_end(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayWillEndPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering GoalReplayWillEnd handlers."""
        self._handlers_by_event["GoalReplayWillEnd"].append(handler)

    def on_goal_scored(
        self,
        handler: Callable[
            [TypedEventMessage[GoalScoredPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering GoalScored handlers."""
        self._handlers_by_event["GoalScored"].append(handler)

    def on_match_created(
        self,
        handler: Callable[
            [TypedEventMessage[MatchCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchCreated handlers."""
        self._handlers_by_event["MatchCreated"].append(handler)

    def on_match_initialized(
        self,
        handler: Callable[
            [TypedEventMessage[MatchInitializedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchInitialized handlers."""
        self._handlers_by_event["MatchInitialized"].append(handler)

    def on_match_destroyed(
        self,
        handler: Callable[
            [TypedEventMessage[MatchDestroyedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchDestroyed handlers."""
        self._handlers_by_event["MatchDestroyed"].append(handler)

    def on_match_ended(
        self,
        handler: Callable[
            [TypedEventMessage[MatchEndedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchEnded handlers."""
        self._handlers_by_event["MatchEnded"].append(handler)

    def on_match_paused(
        self,
        handler: Callable[
            [TypedEventMessage[MatchPausedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchPaused handlers."""
        self._handlers_by_event["MatchPaused"].append(handler)

    def on_match_unpaused(
        self,
        handler: Callable[
            [TypedEventMessage[MatchUnpausedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering MatchUnpaused handlers."""
        self._handlers_by_event["MatchUnpaused"].append(handler)

    def on_podium_start(
        self,
        handler: Callable[
            [TypedEventMessage[PodiumStartPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering PodiumStart handlers."""
        self._handlers_by_event["PodiumStart"].append(handler)

    def on_replay_created(
        self,
        handler: Callable[
            [TypedEventMessage[ReplayCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering ReplayCreated handlers."""
        self._handlers_by_event["ReplayCreated"].append(handler)

    def on_round_started(
        self,
        handler: Callable[
            [TypedEventMessage[RoundStartedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering RoundStarted handlers."""
        self._handlers_by_event["RoundStarted"].append(handler)

    def on_statfeed_event(
        self,
        handler: Callable[
            [TypedEventMessage[StatfeedEventPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Typed helper for registering StatfeedEvent handlers."""
        self._handlers_by_event["StatfeedEvent"].append(handler)

    async def events(self) -> AsyncIterator[EventMessage]:
        """Async iterator that yields incoming events from the Stats API."""
        while True:
            yield await self._queue.get()

    async def _run(self) -> None:
        """Main loop to manage connection and reading from the Stats API."""
        attempt = 0
        while not self._stopping:
            try:
                self._logger.debug("connecting to tcp://%s:%d", self.host, self.port)
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(host=self.host, port=self.port),
                    timeout=self.connect_timeout,
                )
                self._connected = True
                attempt = 0
                self._logger.debug("tcp socket connected")
                await self._fire_simple(self._on_connect_handlers)
                await self._read_loop(self._reader)
            except asyncio.CancelledError:
                self._logger.debug("reader task cancelled")
                raise
            except Exception as exc:
                self._logger.debug("connection/read error: %s", exc)
                if not self.reconnect or self._stopping:
                    self._logger.debug(
                        "stopping reader (reconnect disabled or stopping)"
                    )
                    return
                attempt += 1
                if (
                    self.max_reconnect_attempts is not None
                    and attempt > self.max_reconnect_attempts
                ):
                    self._logger.debug(
                        "max reconnect attempts (%d) reached",
                        self.max_reconnect_attempts,
                    )
                    return
                delay = min(
                    self.reconnect_delay * (2 ** (attempt - 1)),
                    self.max_reconnect_delay,
                ) * random.uniform(0.75, 1.25)
                self._logger.debug("reconnecting in %.2fs (attempt %d)", delay, attempt)
                await asyncio.sleep(delay)
            finally:
                if self._connected:
                    self._connected = False
                    await self._fire_simple(self._on_disconnect_handlers)
                if self._writer is not None:
                    with contextlib.suppress(Exception):
                        self._writer.close()
                        await self._writer.wait_closed()
                    self._writer = None
                    self._reader = None
                    self._logger.debug("tcp socket closed")

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        """
        Reads data from the Stats API, decodes JSON messages, and dispatches events to handlers.
        """
        decoder = json.JSONDecoder()
        buffer = ""
        while not self._stopping:
            chunk = await reader.read(4096)
            if not chunk:
                raise ConnectionAbortedError("Socket closed by peer")
            buffer += chunk.decode("utf-8", errors="ignore")

            while True:
                lstripped = buffer.lstrip()
                if not lstripped:
                    buffer = ""
                    break
                if lstripped is not buffer:
                    buffer = lstripped

                try:
                    decoded, end_idx = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break

                raw = buffer[:end_idx]
                buffer = buffer[end_idx:]

                message = _parse_message_obj(
                    decoded, raw=raw, include_raw=self.include_raw
                )
                if message is None:
                    self._logger.debug("ignored invalid message (json/envelope)")
                    continue

                if self.overflow == "block":
                    await self._queue.put(message)
                elif self.overflow == "drop":
                    try:
                        self._queue.put_nowait(message)
                    except asyncio.QueueFull:
                        self._logger.warning(
                            "queue full, dropping %s event", message.event
                        )
                else:  # "raise" queuefull propagates and kills the connection
                    self._queue.put_nowait(message)

                await self._dispatch(message)

    async def _dispatch(self, message: EventMessage) -> None:
        """
        Dispatches to handlers for `message.event` and global handlers.
        """
        handlers = list(self._handlers_any) + list(
            self._handlers_by_event.get(message.event, [])
        )
        for handler in handlers:
            try:
                result = handler(message)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                if self._error_handlers:
                    for error_handler in list(self._error_handlers):
                        with contextlib.suppress(Exception):
                            r = error_handler(message.event, exc)
                            if inspect.isawaitable(r):
                                await r
                else:
                    self._logger.error("handler error for %s: %s", message.event, exc)

    async def _fire_simple(self, handlers: list[_SimpleHandler]) -> None:
        """Run connection lifecycle callbacks and await async ones when needed."""
        for handler in list(handlers):
            with contextlib.suppress(Exception):
                result = handler()
                if inspect.isawaitable(result):
                    await result


def _parse_message_obj(
    decoded: Any, *, raw: str, include_raw: bool
) -> EventMessage | None:
    """Normalize one decoded object into an EventMessage envelope."""
    if not isinstance(decoded, dict):
        return None
    event = decoded.get("Event")
    data = decoded.get("Data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    if not isinstance(event, str) or not isinstance(data, dict):
        return None
    return EventMessage(event=event, data=data, raw=raw if include_raw else None)

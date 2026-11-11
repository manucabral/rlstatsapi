"""Async TCP client for Rocket League's live Stats API exporter."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import random
import re
from collections import defaultdict
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Literal,
    Mapping,
    overload,
)

from .commands import (
    Perspective,
    build_command,
    change_pov,
    encode_command,
    load_replay,
    seek_replay,
    set_game_speed,
    set_hud_visibility,
    set_match_paused,
)
from .models import ClientMetrics, EventMessage, MatchStateSnapshot
from .state import MatchStateTracker
from .types import (
    BallHitPayload,
    BoostPickupPayload,
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
    PlayerJoinedPayload,
    PlayerLeftPayload,
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
_ErrorHandler = Callable[
    [EventMessage, Exception, _AnyCallable], Awaitable[None] | None
]

_READ_CHUNK_SIZE = 65536
_MAX_JSON_FIELD_BYTES = 1 << 20  # 1 MiB
_MAX_BUFFER_BYTES = 4 << 20  # 4 MiB
_WHITESPACE_RE = re.compile(r"\s*")
# ``}`` followed by ``{"`` never appears inside one JSON document: between
# values a comma is required, and inside a string the quote is escaped.
_FRAME_BOUNDARY_RE = re.compile(rb'\}\s*\{"')
_OPEN_BRACE = 0x7B
_CLOSE_BRACE = 0x7D
try:  # optional accelerator: pip install rlstatsapi[fast]
    import orjson as _orjson

    _JSON_LOADS: Callable[[Any], Any] = _orjson.loads  # pylint: disable=no-member
    JSON_BACKEND = "orjson"
except ImportError:  # pragma: no cover - depends on the environment
    _JSON_LOADS = json.loads
    JSON_BACKEND = "json"
_JSON_DECODE_ERROR = json.JSONDecodeError
_VALID_OVERFLOW_MODES = frozenset({"block", "drop", "raise"})


class ConnectionState(Enum):
    """Connection lifecycle state for ``StatsClient``.

    Attributes:
        DISCONNECTED: No active TCP session is open.
        CONNECTING: TCP handshake is in progress.
        CONNECTED: TCP session is established and reading events.
        FAILED: Reconnect attempts were exhausted.
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


def _validate_client_options(
    *,
    port: int,
    reconnect_delay: float,
    max_reconnect_delay: float,
    max_reconnect_attempts: int | None,
    queue_size: int,
    overflow: str,
    connect_timeout: float,
    handler_timeout: float | None,
) -> None:
    """Validate ``StatsClient`` constructor parameters."""
    if isinstance(port, bool) or port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    if reconnect_delay <= 0:
        raise ValueError("reconnect_delay must be positive")
    if max_reconnect_delay <= 0 or max_reconnect_delay < reconnect_delay:
        raise ValueError("max_reconnect_delay must be >= reconnect_delay")
    if max_reconnect_attempts is not None and (
        isinstance(max_reconnect_attempts, bool) or max_reconnect_attempts < 0
    ):
        raise ValueError("max_reconnect_attempts must be >= 0 or None")
    if isinstance(queue_size, bool) or queue_size < 1:
        raise ValueError("queue_size must be at least 1")
    if overflow not in _VALID_OVERFLOW_MODES:
        raise ValueError("overflow must be 'block', 'drop', or 'raise'")
    if connect_timeout <= 0:
        raise ValueError("connect_timeout must be positive")
    if handler_timeout is not None and handler_timeout <= 0:
        raise ValueError("handler_timeout must be positive or None")


class StatsClient:
    """Async event client for the local Rocket League Stats API TCP stream."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 49123,
        reconnect: bool = True,
        reconnect_delay: float = 0.5,
        max_reconnect_delay: float = 30.0,
        max_reconnect_attempts: int | None = None,
        include_raw: bool = False,
        queue_size: int = 2048,
        overflow: Literal["block", "drop", "raise"] = "block",
        connect_timeout: float = 5.0,
        drain_on_disconnect: bool = False,
        handler_timeout: float | None = None,
        track_state: bool = True,
    ) -> None:
        """Initialize the client configuration without opening a socket.

        Args:
            host: Stats API host address.
            port: Stats API TCP port in the range 1..65535.
            reconnect: Whether to reconnect automatically when the socket closes.
            reconnect_delay: Initial backoff delay in seconds before reconnecting.
            max_reconnect_delay: Maximum backoff delay in seconds between attempts.
            max_reconnect_attempts: Maximum reconnect attempts before entering
                ``ConnectionState.FAILED``. ``None`` retries indefinitely.
            include_raw: Attach the raw JSON string to ``EventMessage.raw``.
            queue_size: Maximum number of events buffered in the internal queue.
            overflow: Queue-full policy: ``"block"`` waits when an ``events()``
                consumer is active (or evicts the oldest item when no iterator is
                attached), ``"drop"`` discards incoming queue items, and
                ``"raise"`` raises ``asyncio.QueueFull``.
            connect_timeout: Seconds to wait for the TCP handshake.
            drain_on_disconnect: Clear queued events when ``disconnect()`` runs.
            handler_timeout: Maximum seconds an awaitable handler may run before
                being cancelled. ``None`` disables the timeout.
            track_state: Update ``client.state`` on incoming events.

        Raises:
            ValueError: If any numeric bound or ``overflow`` mode is invalid.
        """
        _validate_client_options(
            port=port,
            reconnect_delay=reconnect_delay,
            max_reconnect_delay=max_reconnect_delay,
            max_reconnect_attempts=max_reconnect_attempts,
            queue_size=queue_size,
            overflow=overflow,
            connect_timeout=connect_timeout,
            handler_timeout=handler_timeout,
        )

        self.host = host
        self.port = port
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.include_raw = include_raw
        self.connect_timeout = connect_timeout
        self.overflow = overflow
        self.drain_on_disconnect = drain_on_disconnect
        self.handler_timeout = handler_timeout
        self.track_state = track_state

        self._queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=queue_size)
        self._event_consumers = 0
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
        self._connection_state = ConnectionState.DISCONNECTED
        self._permanently_failed = False
        self._last_error: Exception | None = None
        self._metrics = ClientMetrics()
        self._state_tracker = MatchStateTracker()

    @property
    def connection_state(self) -> ConnectionState:
        """Current connection lifecycle state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """``True`` when the TCP connection is established."""
        return self._connection_state == ConnectionState.CONNECTED

    @property
    def metrics(self) -> ClientMetrics:
        """Counters for throughput, drops, errors, and reconnects."""
        return self._metrics

    @property
    def state(self) -> MatchStateSnapshot:
        """Latest match snapshot derived from incoming events."""
        return self._state_tracker.snapshot

    @property
    def last_error(self) -> Exception | None:
        """Latest connection or stream error recorded by the reader task."""
        return self._last_error

    @property
    def permanently_failed(self) -> bool:
        """``True`` when ``max_reconnect_attempts`` was exhausted."""
        return self._permanently_failed

    async def __aenter__(self) -> StatsClient:
        """Start the background reader task upon entering the context manager.

        Returns:
            StatsClient: This client instance.
        """
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Stop the reader task and close the socket on context exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Start the background reader task if it is not already running."""
        if self._reader_task and not self._reader_task.done():
            self._logger.debug("connect() ignored: reader already running")
            return

        self._stopping = False
        self._permanently_failed = False
        self._last_error = None
        self._reader_task = asyncio.create_task(self._run(), name="rlstatsapi-reader")
        self._logger.debug("reader task started")

    async def disconnect(self, timeout: float = 5.0) -> None:
        """Close the active socket and stop the background reader task.

        Args:
            timeout: Maximum seconds to wait for the reader task to finish.
        """
        self._stopping = True
        self._logger.debug("disconnect requested")

        close_timeout = min(timeout, 1.0) if timeout > 0 else 0.1
        await self._close_writer(timeout=close_timeout)

        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(self._reader_task, timeout=timeout)
            self._reader_task = None

        if self._connection_state != ConnectionState.FAILED:
            self._connection_state = ConnectionState.DISCONNECTED

        if self.drain_on_disconnect:
            self.clear_queue()
        self._logger.debug("disconnected")

    def on_connect(self, handler: _SimpleHandler) -> None:
        """Register a callback invoked after the TCP connection is established."""
        self._on_connect_handlers.append(handler)

    def off_connect(self, handler: _SimpleHandler) -> None:
        """Unregister a callback previously added with ``on_connect``."""
        with contextlib.suppress(ValueError):
            self._on_connect_handlers.remove(handler)

    def on_disconnect(self, handler: _SimpleHandler) -> None:
        """Register a callback invoked when an established TCP session closes."""
        self._on_disconnect_handlers.append(handler)

    def off_disconnect(self, handler: _SimpleHandler) -> None:
        """Unregister a callback previously added with ``on_disconnect``."""
        with contextlib.suppress(ValueError):
            self._on_disconnect_handlers.remove(handler)

    def on_handler_error(self, handler: _ErrorHandler) -> None:
        """Register a callback invoked when an event handler raises an exception."""
        self._error_handlers.append(handler)

    def off_handler_error(self, handler: _ErrorHandler) -> None:
        """Unregister a callback previously added with ``on_handler_error``."""
        with contextlib.suppress(ValueError):
            self._error_handlers.remove(handler)

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
    def on(
        self,
        event_name: Literal["BoostPickup"],
        handler: Callable[
            [TypedEventMessage[BoostPickupPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["BoostPickup"]) -> Callable[
        [Callable[[TypedEventMessage[BoostPickupPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[BoostPickupPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["PlayerJoined"],
        handler: Callable[
            [TypedEventMessage[PlayerJoinedPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["PlayerJoined"]) -> Callable[
        [Callable[[TypedEventMessage[PlayerJoinedPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[PlayerJoinedPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(
        self,
        event_name: Literal["PlayerLeft"],
        handler: Callable[
            [TypedEventMessage[PlayerLeftPayload]], Awaitable[None] | None
        ],
    ) -> None: ...
    @overload
    def on(self, event_name: Literal["PlayerLeft"]) -> Callable[
        [Callable[[TypedEventMessage[PlayerLeftPayload]], Awaitable[None] | None]],
        Callable[[TypedEventMessage[PlayerLeftPayload]], Awaitable[None] | None],
    ]: ...

    @overload
    def on(self, event_name: str, handler: Handler) -> None: ...
    @overload
    def on(self, event_name: str) -> Callable[[Handler], Handler]: ...

    def on(self, event_name: str, handler: _AnyCallable | None = None) -> Any:
        """Register an event handler directly or return a decorator.

        Args:
            event_name: Rocket League event name (such as ``"GoalScored"``).
            handler: Callback to register. When omitted, returns a decorator
                that registers the decorated function and returns it unchanged.

        Returns:
            Callable | None: The decorator function when ``handler`` is ``None``,
            otherwise ``None``.
        """
        if handler is None:

            def decorator(h: _AnyCallable) -> _AnyCallable:
                self._handlers_by_event[event_name].append(h)
                return h

            return decorator
        self._handlers_by_event[event_name].append(handler)
        return None

    def on_any(self, handler: Handler) -> None:
        """Register a global handler invoked for every incoming event."""
        self._handlers_any.append(handler)

    def on_many(self, event_names: Iterable[str], handler: Handler) -> None:
        """Register the same handler for multiple event names."""
        for event_name in event_names:
            self._handlers_by_event[event_name].append(handler)

    def off(self, event_name: str, handler: _AnyCallable) -> None:
        """Unregister a handler for a specific event if present."""
        handlers = self._handlers_by_event.get(event_name)
        if handlers:
            with contextlib.suppress(ValueError):
                handlers.remove(handler)
            if not handlers:
                self._handlers_by_event.pop(event_name, None)

    def off_any(self, handler: _AnyCallable) -> None:
        """Unregister a global handler previously added with ``on_any``."""
        with contextlib.suppress(ValueError):
            self._handlers_any.remove(handler)

    def clear_queue(self) -> None:
        """Discard all pending events currently buffered in the internal queue."""
        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def once(self, event_name: str, handler: _AnyCallable) -> None:
        """Register a handler that executes on the next matching event and removes itself."""

        async def wrapper(msg: EventMessage) -> None:
            self.off(event_name, wrapper)
            result = handler(msg)
            if result is not None and inspect.isawaitable(result):
                await result

        self._handlers_by_event[event_name].append(wrapper)

    def on_update_state(
        self,
        handler: Callable[
            [TypedEventMessage[UpdateStatePayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``UpdateState`` events."""
        self._handlers_by_event["UpdateState"].append(handler)

    def on_ball_hit(
        self,
        handler: Callable[[TypedEventMessage[BallHitPayload]], Awaitable[None] | None],
    ) -> None:
        """Register a typed handler for ``BallHit`` events."""
        self._handlers_by_event["BallHit"].append(handler)

    def on_clock_updated_seconds(
        self,
        handler: Callable[
            [TypedEventMessage[ClockUpdatedSecondsPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``ClockUpdatedSeconds`` events."""
        self._handlers_by_event["ClockUpdatedSeconds"].append(handler)

    def on_countdown_begin(
        self,
        handler: Callable[
            [TypedEventMessage[CountdownBeginPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``CountdownBegin`` events."""
        self._handlers_by_event["CountdownBegin"].append(handler)

    def on_crossbar_hit(
        self,
        handler: Callable[
            [TypedEventMessage[CrossbarHitPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``CrossbarHit`` events."""
        self._handlers_by_event["CrossbarHit"].append(handler)

    def on_goal_replay_end(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayEndPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``GoalReplayEnd`` events."""
        self._handlers_by_event["GoalReplayEnd"].append(handler)

    def on_goal_replay_start(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayStartPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``GoalReplayStart`` events."""
        self._handlers_by_event["GoalReplayStart"].append(handler)

    def on_goal_replay_will_end(
        self,
        handler: Callable[
            [TypedEventMessage[GoalReplayWillEndPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``GoalReplayWillEnd`` events."""
        self._handlers_by_event["GoalReplayWillEnd"].append(handler)

    def on_goal_scored(
        self,
        handler: Callable[
            [TypedEventMessage[GoalScoredPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``GoalScored`` events."""
        self._handlers_by_event["GoalScored"].append(handler)

    def on_match_created(
        self,
        handler: Callable[
            [TypedEventMessage[MatchCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchCreated`` events."""
        self._handlers_by_event["MatchCreated"].append(handler)

    def on_match_initialized(
        self,
        handler: Callable[
            [TypedEventMessage[MatchInitializedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchInitialized`` events."""
        self._handlers_by_event["MatchInitialized"].append(handler)

    def on_match_destroyed(
        self,
        handler: Callable[
            [TypedEventMessage[MatchDestroyedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchDestroyed`` events."""
        self._handlers_by_event["MatchDestroyed"].append(handler)

    def on_match_ended(
        self,
        handler: Callable[
            [TypedEventMessage[MatchEndedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchEnded`` events."""
        self._handlers_by_event["MatchEnded"].append(handler)

    def on_match_paused(
        self,
        handler: Callable[
            [TypedEventMessage[MatchPausedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchPaused`` events."""
        self._handlers_by_event["MatchPaused"].append(handler)

    def on_match_unpaused(
        self,
        handler: Callable[
            [TypedEventMessage[MatchUnpausedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``MatchUnpaused`` events."""
        self._handlers_by_event["MatchUnpaused"].append(handler)

    def on_podium_start(
        self,
        handler: Callable[
            [TypedEventMessage[PodiumStartPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``PodiumStart`` events."""
        self._handlers_by_event["PodiumStart"].append(handler)

    def on_replay_created(
        self,
        handler: Callable[
            [TypedEventMessage[ReplayCreatedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``ReplayCreated`` events."""
        self._handlers_by_event["ReplayCreated"].append(handler)

    def on_round_started(
        self,
        handler: Callable[
            [TypedEventMessage[RoundStartedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``RoundStarted`` events."""
        self._handlers_by_event["RoundStarted"].append(handler)

    def on_statfeed_event(
        self,
        handler: Callable[
            [TypedEventMessage[StatfeedEventPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``StatfeedEvent`` events."""
        self._handlers_by_event["StatfeedEvent"].append(handler)

    def on_boost_pickup(
        self,
        handler: Callable[
            [TypedEventMessage[BoostPickupPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``BoostPickup`` events."""
        self._handlers_by_event["BoostPickup"].append(handler)

    def on_player_joined(
        self,
        handler: Callable[
            [TypedEventMessage[PlayerJoinedPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``PlayerJoined`` events."""
        self._handlers_by_event["PlayerJoined"].append(handler)

    def on_player_left(
        self,
        handler: Callable[
            [TypedEventMessage[PlayerLeftPayload]], Awaitable[None] | None
        ],
    ) -> None:
        """Register a typed handler for ``PlayerLeft`` events."""
        self._handlers_by_event["PlayerLeft"].append(handler)

    async def events(self, *event_names: str) -> AsyncIterator[EventMessage]:
        """Yield incoming events from the internal queue, optionally filtered by name.

        Args:
            *event_names: Optional event names to filter by.

        Yields:
            EventMessage: Next matching event from the stream.
        """
        filters = frozenset(event_names)
        self._event_consumers += 1
        try:
            while True:
                message = await self._queue.get()
                if not filters or message.event in filters:
                    yield message
        finally:
            self._event_consumers -= 1

    async def wait_for(
        self,
        event_name: str,
        *,
        timeout: float | None = None,
    ) -> EventMessage:
        """Wait for the next occurrence of ``event_name`` and return its message.

        Args:
            event_name: Event name to wait for (for example ``"GoalScored"``).
            timeout: Maximum seconds to wait before raising ``asyncio.TimeoutError``.

        Returns:
            EventMessage: The first matching event received after registration.

        Raises:
            asyncio.TimeoutError: If ``timeout`` elapses before the event arrives.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[EventMessage] = loop.create_future()

        def _handler(msg: EventMessage) -> None:
            if not future.done():
                future.set_result(msg)

        self._handlers_by_event[event_name].append(_handler)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self.off(event_name, _handler)

    async def send_command(
        self,
        command: Mapping[str, Any] | str,
        data: Mapping[str, Any] | None = None,
    ) -> None:
        """Validate a command and write it to the game over the stats socket.

        The game does not acknowledge commands. Watch the event stream to see
        the effect (for example ``MatchPaused`` after ``SetMatchPaused``).

        Args:
            command: Envelope built by ``rlstatsapi.commands`` or a command name.
            data: Wire-format variables when ``command`` is a name.

        Raises:
            InvalidCommandError: If the game would reject the command.
            ConnectionError: If the client is not connected.
        """
        payload = encode_command(
            build_command(command, data) if isinstance(command, str) else command
        )
        writer = self._writer
        if writer is None or self._connection_state != ConnectionState.CONNECTED:
            raise ConnectionError("StatsClient is not connected")
        writer.write(payload)
        await writer.drain()

    async def change_pov(
        self,
        focus: int | str | None = None,
        perspective: Perspective | None = None,
    ) -> None:
        """Send ``ChangePOV``: focus ``"Ball"`` or a player shortcut, and/or a camera mode."""
        await self.send_command(change_pov(focus, perspective))

    async def load_replay(
        self, file_name: str | None = None, path: str | None = None
    ) -> None:
        """Send ``LoadReplay`` by replay file name or file path."""
        await self.send_command(load_replay(file_name, path))

    async def seek_replay(
        self, frame: int | None = None, time_seconds: float | None = None
    ) -> None:
        """Send ``SeekReplay`` to a frame or a time in seconds."""
        await self.send_command(seek_replay(frame, time_seconds))

    async def set_game_speed(self, speed: float) -> None:
        """Send ``SetGameSpeed``. ``1.0`` is normal replay speed."""
        await self.send_command(set_game_speed(speed))

    async def set_hud_visibility(self, visible: bool) -> None:
        """Send ``SetHUDVisibility`` to show or hide the in-game HUD."""
        await self.send_command(set_hud_visibility(visible))

    async def set_match_paused(self, paused: bool) -> None:
        """Send ``SetMatchPaused`` to pause or resume the match or replay."""
        await self.send_command(set_match_paused(paused))

    async def _close_writer(self, timeout: float = 1.0) -> None:
        """Close the active ``StreamWriter`` and bound ``wait_closed`` by ``timeout``."""
        writer = self._writer
        self._writer = None
        self._reader = None
        if writer is None:
            return
        with contextlib.suppress(OSError, asyncio.TimeoutError, asyncio.CancelledError):
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=timeout)

    async def _run(self) -> None:
        """Manage the TCP connection lifecycle, reconnect backoff, and read loop."""
        attempt = 0
        while not self._stopping:
            try:
                self._logger.debug("connecting to tcp://%s:%d", self.host, self.port)
                self._connection_state = ConnectionState.CONNECTING
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(host=self.host, port=self.port),
                    timeout=self.connect_timeout,
                )
                self._connection_state = ConnectionState.CONNECTED
                attempt = 0
                self._logger.debug("tcp socket connected")
                await self._fire_simple(self._on_connect_handlers)
                await self._read_loop(self._reader)
            except asyncio.CancelledError:
                self._logger.debug("reader task cancelled")
                raise
            except Exception as exc:
                self._last_error = exc
                self._metrics.connection_failures += 1
                self._logger.debug("connection/read error: %s", exc)
                if not self.reconnect or self._stopping:
                    self._logger.debug(
                        "stopping reader (reconnect disabled or stopping)"
                    )
                    return
                attempt += 1
                self._metrics.reconnect_count += 1
                if (
                    self.max_reconnect_attempts is not None
                    and attempt > self.max_reconnect_attempts
                ):
                    self._permanently_failed = True
                    self._connection_state = ConnectionState.FAILED
                    self._logger.debug(
                        "max reconnect attempts (%d) reached",
                        self.max_reconnect_attempts,
                    )
                    return
                await self._cleanup_session()
                delay = min(
                    self.reconnect_delay * (2 ** (attempt - 1)),
                    self.max_reconnect_delay,
                ) * random.uniform(0.75, 1.25)
                self._logger.debug("reconnecting in %.2fs (attempt %d)", delay, attempt)
                await asyncio.sleep(delay)
            finally:
                await self._cleanup_session()

    async def _cleanup_session(self) -> None:
        """Reset connection state, fire disconnect handlers if needed, and close writer."""
        was_connected = self._connection_state == ConnectionState.CONNECTED
        if self._connection_state != ConnectionState.FAILED:
            self._connection_state = ConnectionState.DISCONNECTED
        if was_connected:
            await self._fire_simple(self._on_disconnect_handlers)
        if self._writer is not None:
            await self._close_writer()
            self._logger.debug("tcp socket closed")

    def _enqueue_nowait(self, message: EventMessage) -> bool:
        """Queue ``message`` without awaiting. Return ``False`` if the caller must block."""
        queue = self._queue
        overflow = self.overflow
        if overflow == "block":
            if queue.full():
                if self._event_consumers > 0:
                    return False
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(message)
        elif overflow == "drop":
            if queue.full():
                self._metrics.dropped_events += 1
                self._logger.warning("queue full, dropping %s event", message.event)
                return True
            queue.put_nowait(message)
        else:
            queue.put_nowait(message)
        self._metrics.queued_events += 1
        return True

    async def _enqueue_message(self, message: EventMessage) -> None:
        """Push ``message`` into the internal queue according to ``self.overflow``."""
        if not self._enqueue_nowait(message):
            await self._queue.put(message)
            self._metrics.queued_events += 1

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        """Read chunks from the TCP stream, decode JSON frames, and dispatch events."""
        read = reader.read
        consume = self._consume
        pending = b""
        while not self._stopping:
            chunk = await read(_READ_CHUNK_SIZE)
            if not chunk:
                raise ConnectionAbortedError("Socket closed by peer")
            pending = await consume(pending + chunk if pending else chunk)

    def _accept(self, decoded: Any, frame: bytes | str) -> EventMessage | None:
        """Build the message for one decoded frame and update metrics and state."""
        if type(decoded) is not dict:
            self._logger.debug("ignored invalid message (json/envelope)")
            return None
        event = decoded.get("Event")
        data = decoded.get("Data")
        if type(data) is str and len(data) <= _MAX_JSON_FIELD_BYTES:
            try:
                data = _JSON_LOADS(data)
            except ValueError:
                data = None
        if type(event) is not str or type(data) is not dict:
            self._logger.debug("ignored invalid message (json/envelope)")
            return None

        raw: str | None = None
        if self.include_raw:
            raw = frame if type(frame) is str else frame.decode("utf-8", "replace")  # type: ignore[union-attr]
        message = EventMessage(event, data, raw)
        self._metrics.received_events += 1
        if self.track_state:
            self._state_tracker.ingest(message)
        return message

    def _needs_await(self, message: EventMessage) -> bool:
        """Queue ``message`` if nothing has to be awaited; otherwise return ``True``."""
        if self._handlers_any or self._handlers_by_event.get(message.event):
            return True
        return not self._enqueue_nowait(message)

    async def _deliver(self, message: EventMessage) -> None:
        """Run handlers for ``message`` and then queue it."""
        await self._dispatch(message)
        await self._enqueue_message(message)

    async def _consume(self, data: bytes) -> bytes:  # pylint: disable=too-many-locals
        """Decode every complete JSON message in ``data`` and return the leftover bytes.

        This is the hot path. A read usually holds exactly one message, so the
        whole chunk is parsed first. Otherwise it is split at message
        boundaries, and anything unusual goes through ``_consume_slow``.
        """
        loads = _JSON_LOADS
        accept = self._accept
        needs_await = self._needs_await

        # Only a chunk ending in ``}`` or whitespace can be one whole message.
        tail = data[-1]
        if tail == _CLOSE_BRACE or tail <= 0x20:
            try:
                decoded = loads(data)
            except ValueError:
                pass
            else:
                message = accept(decoded, data)
                if message is not None and needs_await(message):
                    await self._deliver(message)
                return b""

        # Frame ``data`` at each boundary; the last frame runs to the end.
        starts = [0]
        ends = []
        for match in _FRAME_BOUNDARY_RE.finditer(data):
            ends.append(match.start() + 1)
            starts.append(match.end() - 2)
        ends.append(len(data))
        last = len(ends) - 1
        remainder = b""
        for index, start in enumerate(starts):
            frame = data[start : ends[index]] if last else data
            if (
                index == last
                and frame[0] == _OPEN_BRACE
                and frame.rstrip()[-1] != _CLOSE_BRACE
            ):
                remainder = frame  # incomplete message, wait for more bytes
                break
            try:
                decoded = loads(frame)
            except ValueError:
                leftover = await self._consume_slow(frame)
                if index == last:
                    remainder = leftover
                continue
            message = accept(decoded, frame)
            if message is not None and needs_await(message):
                await self._deliver(message)

        if len(remainder) > _MAX_BUFFER_BYTES:
            raise ValueError(
                f"Stream buffer exceeded {_MAX_BUFFER_BYTES} bytes without a complete JSON object"
            )
        return remainder

    async def _consume_slow(self, data: bytes) -> bytes:
        """Tolerant decoder for data the fast path rejected.

        Handles leading garbage, invalid UTF-8 (replaced with U+FFFD) and
        messages split in the middle of a multibyte character.
        """
        head, tail = _split_incomplete_utf8(data)
        try:
            text = head.decode("utf-8")
        except UnicodeDecodeError:
            text = head.decode("utf-8", "replace")
            self._logger.warning("received invalid UTF-8 bytes; replaced with U+FFFD")

        raw_decode = json.JSONDecoder().raw_decode
        text_len = len(text)
        pos = 0
        while pos < text_len:
            if text[pos] != "{":
                match = _WHITESPACE_RE.match(text, pos)
                if match is not None:
                    pos = match.end()
                if pos >= text_len:
                    break
                if text[pos] != "{":
                    pos = text.find("{", pos)
                    if pos == -1:
                        pos = text_len
                        break
            try:
                decoded, end_idx = raw_decode(text, pos)
            except _JSON_DECODE_ERROR:
                break
            message = self._accept(decoded, text[pos:end_idx])
            pos = end_idx
            if message is not None and self._needs_await(message):
                await self._deliver(message)

        return (text[pos:].encode("utf-8") if pos < text_len else b"") + tail

    async def _dispatch(self, message: EventMessage) -> None:
        """Dispatch ``message`` to global handlers and event-specific handlers."""
        any_handlers = self._handlers_any
        event_handlers = self._handlers_by_event.get(message.event)
        if not any_handlers and not event_handlers:
            return

        handlers: tuple[_AnyCallable, ...] = (
            (*any_handlers, *event_handlers)
            if (any_handlers and event_handlers)
            else tuple(any_handlers or event_handlers or ())
        )

        timeout = self.handler_timeout
        for handler in handlers:
            try:
                result = handler(message)
                if result is not None and inspect.isawaitable(result):
                    if timeout is not None:
                        await asyncio.wait_for(result, timeout=timeout)
                    else:
                        await result
            except Exception as exc:
                await self._handle_dispatch_error(message, exc, handler)

    async def _handle_dispatch_error(
        self, message: EventMessage, exc: Exception, handler: _AnyCallable
    ) -> None:
        """Record a handler error and notify registered error callbacks."""
        self._metrics.handler_errors += 1
        if not self._error_handlers:
            self._logger.error("handler error for %s: %s", message.event, exc)
            return

        for error_handler in tuple(self._error_handlers):
            try:
                err_result = error_handler(message, exc, handler)
                if err_result is not None and inspect.isawaitable(err_result):
                    await err_result
            except Exception as err_exc:
                self._logger.error("error handler itself raised: %s", err_exc)

    async def _fire_simple(self, handlers: list[_SimpleHandler]) -> None:
        """Invoke connection lifecycle callbacks and await coroutine results."""
        for handler in tuple(handlers):
            try:
                result = handler()
                if result is not None and inspect.isawaitable(result):
                    await result
            except Exception as exc:
                self._logger.error("lifecycle handler error: %s", exc)


def _split_incomplete_utf8(data: bytes) -> tuple[bytes, bytes]:
    """Split off a multibyte UTF-8 sequence cut short at the end of ``data``."""
    for back in range(1, min(3, len(data)) + 1):
        byte = data[-back]
        if byte & 0xC0 == 0x80:  # continuation byte, keep looking for the lead
            continue
        if byte >= 0xC0:
            needed = 2 if byte < 0xE0 else 3 if byte < 0xF0 else 4
            if needed > back:
                return data[:-back], data[-back:]
        break
    return data, b""


def _parse_message_obj(
    decoded: Any, *, raw: str, include_raw: bool
) -> EventMessage | None:
    """Convert a decoded JSON dict into an ``EventMessage`` envelope.

    Args:
        decoded: Parsed JSON value from the TCP stream.
        raw: Raw JSON string slice when ``include_raw`` is enabled.
        include_raw: Whether to retain ``raw`` on the returned ``EventMessage``.

    Returns:
        EventMessage | None: Normalized event message, or ``None`` if the
        envelope or payload structure is invalid.
    """
    if not isinstance(decoded, dict):
        return None
    event = decoded.get("Event")
    if not isinstance(event, str):
        return None
    data = decoded.get("Data")
    if isinstance(data, str):
        if len(data) > _MAX_JSON_FIELD_BYTES:
            return None
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    return EventMessage(event=event, data=data, raw=raw if include_raw else None)

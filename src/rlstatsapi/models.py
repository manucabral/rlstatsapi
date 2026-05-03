"""Runtime envelopes used by the streaming client.

These are lightweight transport models (not validators) used while events move
through internal queues and user callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .types import EventName, TypedEventMessage, cast_event_data


@dataclass(slots=True)
class EventMessage:
    """Normalized Rocket League Stats API message envelope."""

    event: str
    data: dict[str, Any]
    raw: str | None = None

    def as_type(self, event_name: EventName) -> TypedEventMessage[Any]:
        """
        Return this message with event-specific payload typing for editors/type-checkers.
        """
        return TypedEventMessage(
            event=event_name,
            data=cast_event_data(event_name, self.data),
        )


@dataclass(slots=True)
class ClientMetrics:
    """Mutable counters that summarize client throughput and reconnect behavior."""

    received_events: int = 0
    queued_events: int = 0
    dropped_events: int = 0
    reconnect_count: int = 0
    handler_errors: int = 0
    connection_failures: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def reset(self) -> None:
        """Reset all counters and update started_at to now."""
        self.received_events = 0
        self.queued_events = 0
        self.dropped_events = 0
        self.reconnect_count = 0
        self.handler_errors = 0
        self.connection_failures = 0
        self.started_at = datetime.now()


@dataclass(slots=True)
class PlayerSnapshot:
    """Per-player state extracted from the latest UpdateState event."""

    name: str
    shortcut: int
    team_num: int
    score: int = 0
    goals: int = 0
    assists: int = 0
    saves: int = 0
    shots: int = 0
    boost: int = 0
    speed: float = 0.0
    is_demolished: bool = False


@dataclass(slots=True)
class MatchStateSnapshot:
    """Summary of the latest match state seen from incoming events."""

    match_guid: str | None = None
    blue_score: int | None = None
    orange_score: int | None = None
    time_seconds: int | None = None
    overtime: bool = False
    arena: str | None = None
    replay_active: bool = False
    has_winner: bool = False
    winner: str | None = None
    last_event: str | None = None
    last_scorer: str | None = None
    last_goal_speed: float | None = None
    players: list[PlayerSnapshot] = field(default_factory=list)
    target_player: PlayerSnapshot | None = None
    event_counts: dict[str, int] = field(default_factory=dict)

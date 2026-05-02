"""Runtime envelopes used by the streaming client.

These are lightweight transport models (not validators) used while events move
through internal queues and user callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    event_counts: dict[str, int] = field(default_factory=dict)

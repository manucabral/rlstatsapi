"""Runtime data models for event envelopes, metrics, and match snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .types import EventName, TypedEventMessage, cast_event_data


@dataclass(slots=True)
class EventMessage:
    """Normalized Rocket League Stats API message envelope.

    Attributes:
        event: Rocket League event name (such as ``"GoalScored"``).
        data: Decoded JSON payload dictionary for the event.
        raw: Raw JSON string from the TCP stream when ``include_raw=True``.
    """

    event: str
    data: dict[str, Any]
    raw: str | None = None

    def as_type(self, event_name: EventName) -> TypedEventMessage[Any]:
        """Return a ``TypedEventMessage`` with payload typing narrowed to ``event_name``.

        Args:
            event_name: Known Rocket League event literal.

        Returns:
            TypedEventMessage[Any]: Typed wrapper carrying the same payload and raw frame.
        """
        return TypedEventMessage(
            event=event_name,
            data=cast_event_data(event_name, self.data),
            raw=self.raw,
        )


@dataclass(slots=True)
class ClientMetrics:
    """Counters for client throughput, queue pressure, and reconnects.

    Attributes:
        received_events: Total valid events parsed from the TCP stream.
        queued_events: Total events pushed into the internal queue.
        dropped_events: Events discarded due to ``overflow="drop"`` when full.
        reconnect_count: Number of reconnect attempts scheduled.
        handler_errors: Exceptions raised by registered event handlers.
        connection_failures: Connection or read errors encountered by the reader task.
        started_at: Timestamp when the metrics object was created or last reset.
    """

    received_events: int = 0
    queued_events: int = 0
    dropped_events: int = 0
    reconnect_count: int = 0
    handler_errors: int = 0
    connection_failures: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def reset(self) -> None:
        """Reset all counters to zero and refresh ``started_at`` to the current time."""
        self.received_events = 0
        self.queued_events = 0
        self.dropped_events = 0
        self.reconnect_count = 0
        self.handler_errors = 0
        self.connection_failures = 0
        self.started_at = datetime.now()


@dataclass(slots=True)
class PlayerSnapshot:
    """Per-player state extracted from an ``UpdateState`` event.

    Attributes:
        name: Display name of the player.
        shortcut: Match-local player index used by ``Game.Target``.
        team_num: Team index (``0`` for Blue, ``1`` for Orange).
        score: Match points accumulated by the player.
        goals: Goals scored.
        assists: Assists recorded.
        saves: Saves recorded.
        shots: Shots on goal.
        boost: Current boost amount (0..100).
        speed: Current car speed.
        is_demolished: ``True`` while the player is demolished.
    """

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
    """Rolling summary of the active match updated from incoming events.

    Attributes:
        match_guid: Unique match identifier when provided by the exporter.
        blue_score: Current score for Team 0 (Blue).
        orange_score: Current score for Team 1 (Orange).
        time_seconds: Remaining or elapsed clock seconds reported by the game.
        overtime: ``True`` when the match is in overtime.
        arena: Internal map/arena identifier.
        playlist_id: Playlist ID of the current match from ``UpdateState``.
        replay_active: ``True`` while a goal replay or history replay is playing.
        has_winner: ``True`` once a winner has been decided.
        winner: Winning team name when reported by ``UpdateState``.
        winner_team_num: ``WinnerTeamNum`` from ``MatchEnded`` (``-1`` on no contest).
        no_contest: ``True`` when ``MatchEnded`` reported no winner.
        last_event: Name of the most recently processed event.
        last_scorer: Name of the player who scored the most recent goal.
        last_goal_speed: Speed of the most recent goal.
        players: Player snapshots from the latest ``UpdateState`` event.
        target_player: Spectated or local player resolved via ``Game.Target.Shortcut``.
        event_counts: Per-event count map for the current match session.
    """

    match_guid: str | None = None
    blue_score: int | None = None
    orange_score: int | None = None
    time_seconds: int | None = None
    overtime: bool = False
    arena: str | None = None
    playlist_id: int | None = None
    replay_active: bool = False
    has_winner: bool = False
    winner: str | None = None
    winner_team_num: int | None = None
    no_contest: bool = False
    last_event: str | None = None
    last_scorer: str | None = None
    last_goal_speed: float | None = None
    players: list[PlayerSnapshot] = field(default_factory=list)
    target_player: PlayerSnapshot | None = None
    event_counts: dict[str, int] = field(default_factory=dict)

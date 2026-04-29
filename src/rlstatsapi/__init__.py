"""
Public package surface for rlstatsapi.

Re-exports the client, envelope model, known event constants, and typed payload
helpers so consumers can import from `rlstatsapi` directly.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import StatsClient
from .events import KNOWN_EVENTS
from .models import EventMessage
from .types import (
    BallHitPayload,
    ClockUpdatedSecondsPayload,
    CountdownBeginPayload,
    CrossbarHitPayload,
    EventName,
    GoalReplayEndPayload,
    GoalReplayStartPayload,
    GoalReplayWillEndPayload,
    GoalScoredPayload,
    KnownEventMessage,
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
    cast_event_data,
)

try:
    __version__: str = _pkg_version("rlstatsapi")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "__version__",
    "StatsClient",
    "EventMessage",
    "KNOWN_EVENTS",
    "EventName",
    "TypedEventMessage",
    "KnownEventMessage",
    "UpdateStatePayload",
    "BallHitPayload",
    "ClockUpdatedSecondsPayload",
    "CountdownBeginPayload",
    "CrossbarHitPayload",
    "GoalReplayEndPayload",
    "GoalReplayStartPayload",
    "GoalReplayWillEndPayload",
    "GoalScoredPayload",
    "MatchCreatedPayload",
    "MatchInitializedPayload",
    "MatchDestroyedPayload",
    "MatchEndedPayload",
    "MatchPausedPayload",
    "MatchUnpausedPayload",
    "PodiumStartPayload",
    "ReplayCreatedPayload",
    "RoundStartedPayload",
    "StatfeedEventPayload",
    "cast_event_data",
]

"""
Public package surface for rlstatsapi.

Re-exports the client, envelope model, known event constants, and typed payload
helpers so consumers can import from `rlstatsapi` directly.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import ConnectionState, StatsClient
from .config import (
    DEFAULT_PACKET_SEND_RATE,
    DEFAULT_STATS_API_FILENAME,
    DEFAULT_STATS_API_PORT,
    StatsAPIConfigStatus,
    candidate_stats_api_paths,
    configure_stats_api,
    find_stats_api_config,
    get_stats_api_status,
    set_stats_api_enabled,
    set_stats_api_port,
)
from .events import KNOWN_EVENTS
from .models import ClientMetrics, EventMessage, MatchStateSnapshot, PlayerSnapshot
from .state import MatchStateTracker
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
    "ConnectionState",
    "StatsAPIConfigStatus",
    "EventMessage",
    "ClientMetrics",
    "MatchStateSnapshot",
    "PlayerSnapshot",
    "MatchStateTracker",
    "KNOWN_EVENTS",
    "DEFAULT_PACKET_SEND_RATE",
    "DEFAULT_STATS_API_FILENAME",
    "DEFAULT_STATS_API_PORT",
    "candidate_stats_api_paths",
    "find_stats_api_config",
    "get_stats_api_status",
    "set_stats_api_enabled",
    "set_stats_api_port",
    "configure_stats_api",
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

"""Public package interface for ``rlstatsapi``."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from . import commands
from .client import JSON_BACKEND, ConnectionState, StatsClient
from .commands import (
    COMMAND_NAMES,
    PERSPECTIVES,
    Command,
    CommandName,
    InvalidCommandError,
    Perspective,
    build_command,
    encode_command,
)
from .config import (
    DEFAULT_PACKET_SEND_RATE,
    DEFAULT_STATS_API_FALLBACK_FILENAME,
    DEFAULT_STATS_API_FILENAME,
    DEFAULT_STATS_API_PORT,
    DEFAULT_STATS_API_WEB_PORT,
    StatsAPIConfigStatus,
    candidate_stats_api_paths,
    configure_stats_api,
    find_stats_api_config,
    get_stats_api_status,
    set_stats_api_enabled,
    set_stats_api_port,
    set_stats_api_web_port,
)
from .events import KNOWN_EVENTS
from .models import ClientMetrics, EventMessage, MatchStateSnapshot, PlayerSnapshot
from .state import MatchStateTracker
from .types import (
    BallHitPayload,
    BoostPickupPayload,
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
    PlayerJoinedPayload,
    PlayerLeftPayload,
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
    "JSON_BACKEND",
    "commands",
    "Command",
    "CommandName",
    "Perspective",
    "COMMAND_NAMES",
    "PERSPECTIVES",
    "InvalidCommandError",
    "build_command",
    "encode_command",
    "DEFAULT_PACKET_SEND_RATE",
    "DEFAULT_STATS_API_FILENAME",
    "DEFAULT_STATS_API_PORT",
    "DEFAULT_STATS_API_WEB_PORT",
    "DEFAULT_STATS_API_FALLBACK_FILENAME",
    "candidate_stats_api_paths",
    "find_stats_api_config",
    "get_stats_api_status",
    "set_stats_api_enabled",
    "set_stats_api_port",
    "set_stats_api_web_port",
    "configure_stats_api",
    "EventName",
    "TypedEventMessage",
    "KnownEventMessage",
    "UpdateStatePayload",
    "BallHitPayload",
    "BoostPickupPayload",
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
    "PlayerJoinedPayload",
    "PlayerLeftPayload",
    "PodiumStartPayload",
    "ReplayCreatedPayload",
    "RoundStartedPayload",
    "StatfeedEventPayload",
    "cast_event_data",
]

"""
Static typing layer for documented Rocket League event payloads.

TypedDicts here mirror the official event schema and are designed for IDE
autocomplete and type-checking, without adding runtime parsing overhead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Literal,
    Mapping,
    TypeAlias,
    TypeVar,
    TypedDict,
    cast,
    overload,
)

EventName: TypeAlias = Literal[
    "UpdateState",
    "BallHit",
    "ClockUpdatedSeconds",
    "CountdownBegin",
    "CrossbarHit",
    "GoalReplayEnd",
    "GoalReplayStart",
    "GoalReplayWillEnd",
    "GoalScored",
    "MatchCreated",
    "MatchInitialized",
    "MatchDestroyed",
    "MatchEnded",
    "MatchPaused",
    "MatchUnpaused",
    "PodiumStart",
    "ReplayCreated",
    "RoundStarted",
    "StatfeedEvent",
]


class Vector3(TypedDict):
    X: float
    Y: float
    Z: float


class PlayerRef(TypedDict):
    Name: str
    Shortcut: int
    TeamNum: int


class TeamState(TypedDict):
    Name: str
    TeamNum: int
    Score: int
    ColorPrimary: str
    ColorSecondary: str


class BallState(TypedDict):
    Speed: float
    TeamNum: int


class PlayerAttacker(TypedDict):
    Name: str
    Shortcut: int
    TeamNum: int


class TargetRef(TypedDict):
    Name: str
    Shortcut: int
    TeamNum: int


class UpdateStatePlayer(TypedDict, total=False):
    Name: str
    PrimaryId: str
    Shortcut: int
    TeamNum: int
    Score: int
    Goals: int
    Shots: int
    Assists: int
    Saves: int
    Touches: int
    CarTouches: int
    Demos: int
    bHasCar: bool
    Speed: float
    Boost: int
    bBoosting: bool
    bOnGround: bool
    bOnWall: bool
    bPowersliding: bool
    bDemolished: bool
    Attacker: PlayerAttacker
    bSupersonic: bool


class UpdateStateGame(TypedDict, total=False):
    Teams: list[TeamState]
    TimeSeconds: int
    bOvertime: bool
    Frame: int
    Elapsed: float
    Ball: BallState
    bReplay: bool
    bHasWinner: bool
    Winner: str
    Arena: str
    bHasTarget: bool
    Target: TargetRef


class UpdateStatePayload(TypedDict, total=False):
    MatchGuid: str
    Players: list[UpdateStatePlayer]
    Game: UpdateStateGame


class BallHitBall(TypedDict):
    PreHitSpeed: float
    PostHitSpeed: float
    Location: Vector3


class BallHitPayload(TypedDict, total=False):
    MatchGuid: str
    Players: list[PlayerRef]
    Ball: BallHitBall


class ClockUpdatedSecondsPayload(TypedDict, total=False):
    MatchGuid: str
    TimeSeconds: int
    bOvertime: bool


class CountdownBeginPayload(TypedDict, total=False):
    MatchGuid: str


class BallLastTouch(TypedDict):
    Player: PlayerRef
    Speed: float


class CrossbarHitPayload(TypedDict, total=False):
    MatchGuid: str
    BallLocation: Vector3
    BallSpeed: float
    ImpactForce: float
    BallLastTouch: BallLastTouch


class GoalReplayEndPayload(TypedDict, total=False):
    MatchGuid: str


class GoalReplayStartPayload(TypedDict, total=False):
    MatchGuid: str


class GoalReplayWillEndPayload(TypedDict, total=False):
    MatchGuid: str


class GoalScoredPayload(TypedDict, total=False):
    MatchGuid: str
    GoalSpeed: float
    GoalTime: float
    ImpactLocation: Vector3
    Scorer: PlayerRef
    Assister: PlayerRef
    BallLastTouch: BallLastTouch


class MatchCreatedPayload(TypedDict, total=False):
    MatchGuid: str


class MatchInitializedPayload(TypedDict, total=False):
    MatchGuid: str


class MatchDestroyedPayload(TypedDict, total=False):
    MatchGuid: str


class MatchEndedPayload(TypedDict, total=False):
    MatchGuid: str
    WinnerTeamNum: int


class MatchPausedPayload(TypedDict, total=False):
    MatchGuid: str


class MatchUnpausedPayload(TypedDict, total=False):
    MatchGuid: str


class PodiumStartPayload(TypedDict, total=False):
    MatchGuid: str


class ReplayCreatedPayload(TypedDict, total=False):
    MatchGuid: str


class RoundStartedPayload(TypedDict, total=False):
    MatchGuid: str


class StatfeedEventPayload(TypedDict, total=False):
    MatchGuid: str
    EventName: str
    Type: str
    MainTarget: PlayerRef
    SecondaryTarget: PlayerRef


KnownEventPayload: TypeAlias = (
    UpdateStatePayload
    | BallHitPayload
    | ClockUpdatedSecondsPayload
    | CountdownBeginPayload
    | CrossbarHitPayload
    | GoalReplayEndPayload
    | GoalReplayStartPayload
    | GoalReplayWillEndPayload
    | GoalScoredPayload
    | MatchCreatedPayload
    | MatchInitializedPayload
    | MatchDestroyedPayload
    | MatchEndedPayload
    | MatchPausedPayload
    | MatchUnpausedPayload
    | PodiumStartPayload
    | ReplayCreatedPayload
    | RoundStartedPayload
    | StatfeedEventPayload
)

KnownEventPayloadMap: TypeAlias = dict[EventName, KnownEventPayload]

TData = TypeVar("TData", bound=Mapping[str, Any])


@dataclass(slots=True)
class TypedEventMessage(Generic[TData]):
    """Typed event envelope used by helpers and typed convenience callbacks."""

    event: str
    data: TData
    raw: str | None = None


KnownEventMessage: TypeAlias = TypedEventMessage[KnownEventPayload]


@overload
def cast_event_data(
    event_name: Literal["UpdateState"], data: Mapping[str, Any]
) -> UpdateStatePayload: ...


@overload
def cast_event_data(
    event_name: Literal["BallHit"], data: Mapping[str, Any]
) -> BallHitPayload: ...


@overload
def cast_event_data(
    event_name: Literal["ClockUpdatedSeconds"], data: Mapping[str, Any]
) -> ClockUpdatedSecondsPayload: ...


@overload
def cast_event_data(
    event_name: Literal["CountdownBegin"], data: Mapping[str, Any]
) -> CountdownBeginPayload: ...


@overload
def cast_event_data(
    event_name: Literal["CrossbarHit"], data: Mapping[str, Any]
) -> CrossbarHitPayload: ...


@overload
def cast_event_data(
    event_name: Literal["GoalReplayEnd"], data: Mapping[str, Any]
) -> GoalReplayEndPayload: ...


@overload
def cast_event_data(
    event_name: Literal["GoalReplayStart"], data: Mapping[str, Any]
) -> GoalReplayStartPayload: ...


@overload
def cast_event_data(
    event_name: Literal["GoalReplayWillEnd"], data: Mapping[str, Any]
) -> GoalReplayWillEndPayload: ...


@overload
def cast_event_data(
    event_name: Literal["GoalScored"], data: Mapping[str, Any]
) -> GoalScoredPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchCreated"], data: Mapping[str, Any]
) -> MatchCreatedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchInitialized"], data: Mapping[str, Any]
) -> MatchInitializedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchDestroyed"], data: Mapping[str, Any]
) -> MatchDestroyedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchEnded"], data: Mapping[str, Any]
) -> MatchEndedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchPaused"], data: Mapping[str, Any]
) -> MatchPausedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["MatchUnpaused"], data: Mapping[str, Any]
) -> MatchUnpausedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["PodiumStart"], data: Mapping[str, Any]
) -> PodiumStartPayload: ...


@overload
def cast_event_data(
    event_name: Literal["ReplayCreated"], data: Mapping[str, Any]
) -> ReplayCreatedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["RoundStarted"], data: Mapping[str, Any]
) -> RoundStartedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["StatfeedEvent"], data: Mapping[str, Any]
) -> StatfeedEventPayload: ...


@overload
def cast_event_data(event_name: str, data: Mapping[str, Any]) -> Mapping[str, Any]: ...


def cast_event_data(event_name: str, data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Type-only helper to narrow `data` based on event name."""

    _ = event_name
    return cast(Mapping[str, Any], data)

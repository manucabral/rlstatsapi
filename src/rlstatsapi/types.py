"""Static typing definitions for documented Rocket League Stats API payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Literal,
    Mapping,
    TypeAlias,
    TypedDict,
    TypeVar,
    cast,
    overload,
)

EventName: TypeAlias = Literal[
    "UpdateState",
    "BallHit",
    "BoostPickup",
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
    "PlayerJoined",
    "PlayerLeft",
    "PodiumStart",
    "ReplayCreated",
    "RoundStarted",
    "StatfeedEvent",
]


class Vector3(TypedDict):
    """3D coordinate vector in world space."""

    X: float
    Y: float
    Z: float


class PlayerRef(TypedDict):
    """Compact player reference used in event payloads."""

    Name: str
    Shortcut: int
    TeamNum: int


class TeamState(TypedDict):
    """Team score and color metadata inside ``UpdateState``."""

    Name: str
    TeamNum: int
    Score: int
    ColorPrimary: str
    ColorSecondary: str


class BallState(TypedDict):
    """Ball speed and last-touch team inside ``UpdateState``."""

    Speed: float
    TeamNum: int


class PlayerAttacker(TypedDict):
    """Attacker reference attached when a player is demolished."""

    Name: str
    Shortcut: int
    TeamNum: int


class TargetRef(TypedDict):
    """Current camera target reference inside ``UpdateState``."""

    Name: str
    Shortcut: int
    TeamNum: int


class UpdateStatePlayer(TypedDict, total=False):
    """Per-player dictionary entry inside ``UpdateState.Players``."""

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
    Loadout: list[str]
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
    PickupClass: str


class UpdateStateGame(TypedDict, total=False):
    """Game-state dictionary inside ``UpdateState.Game``."""

    Teams: list[TeamState]
    PlaylistId: int
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
    """Payload schema for ``UpdateState``."""

    MatchGuid: str
    Players: list[UpdateStatePlayer]
    Game: UpdateStateGame


class BallHitBall(TypedDict):
    """Ball speed and location fields inside ``BallHit``."""

    PreHitSpeed: float
    PostHitSpeed: float
    Location: Vector3


class BallHitPayload(TypedDict, total=False):
    """Payload schema for ``BallHit``."""

    MatchGuid: str
    Players: list[PlayerRef]
    Ball: BallHitBall


class BoostPickupPayload(TypedDict, total=False):
    """Payload schema for ``BoostPickup`` (spectator only)."""

    MatchGuid: str
    Player: PlayerRef
    Location: Vector3
    BoostAmount: float
    BoostType: str
    bReplay: bool


class ClockUpdatedSecondsPayload(TypedDict, total=False):
    """Payload schema for ``ClockUpdatedSeconds``."""

    MatchGuid: str
    TimeSeconds: int
    bOvertime: bool


class CountdownBeginPayload(TypedDict, total=False):
    """Payload schema for ``CountdownBegin``."""

    MatchGuid: str


class BallLastTouch(TypedDict):
    """Player and speed of the most recent ball touch."""

    Player: PlayerRef
    Speed: float


class CrossbarHitPayload(TypedDict, total=False):
    """Payload schema for ``CrossbarHit``."""

    MatchGuid: str
    BallLocation: Vector3
    BallSpeed: float
    ImpactForce: float
    BallLastTouch: BallLastTouch


class GoalReplayEndPayload(TypedDict, total=False):
    """Payload schema for ``GoalReplayEnd``."""

    MatchGuid: str


class GoalReplayStartPayload(TypedDict, total=False):
    """Payload schema for ``GoalReplayStart``."""

    MatchGuid: str


class GoalReplayWillEndPayload(TypedDict, total=False):
    """Payload schema for ``GoalReplayWillEnd``."""

    MatchGuid: str


class GoalScoredPayload(TypedDict, total=False):
    """Payload schema for ``GoalScored``."""

    MatchGuid: str
    GoalSpeed: float
    GoalTime: float
    ImpactLocation: Vector3
    Scorer: PlayerRef
    Assister: PlayerRef
    BallLastTouch: BallLastTouch


class MatchCreatedPayload(TypedDict, total=False):
    """Payload schema for ``MatchCreated``."""

    MatchGuid: str


class MatchInitializedPayload(TypedDict, total=False):
    """Payload schema for ``MatchInitialized``."""

    MatchGuid: str


class MatchDestroyedPayload(TypedDict, total=False):
    """Payload schema for ``MatchDestroyed``."""

    MatchGuid: str


class MatchEndedPayload(TypedDict, total=False):
    """Payload schema for ``MatchEnded``.

    ``WinnerTeamNum`` is ``-1`` when the match ends in no contest.
    """

    MatchGuid: str
    WinnerTeamNum: int


class MatchPausedPayload(TypedDict, total=False):
    """Payload schema for ``MatchPaused``."""

    MatchGuid: str


class MatchUnpausedPayload(TypedDict, total=False):
    """Payload schema for ``MatchUnpaused``."""

    MatchGuid: str


class PlayerJoinedPayload(TypedDict, total=False):
    """Payload schema for ``PlayerJoined``."""

    MatchGuid: str
    PlayerName: str
    PrimaryId: str


class PlayerLeftPayload(TypedDict, total=False):
    """Payload schema for ``PlayerLeft``."""

    MatchGuid: str
    PlayerName: str
    PrimaryId: str


class PodiumStartPayload(TypedDict, total=False):
    """Payload schema for ``PodiumStart``."""

    MatchGuid: str


class ReplayCreatedPayload(TypedDict, total=False):
    """Payload schema for ``ReplayCreated``."""

    MatchGuid: str
    FileName: str
    Date: str


class RoundStartedPayload(TypedDict, total=False):
    """Payload schema for ``RoundStarted``."""

    MatchGuid: str


class StatfeedEventPayload(TypedDict, total=False):
    """Payload schema for ``StatfeedEvent``."""

    MatchGuid: str
    EventName: str
    Type: str
    MainTarget: PlayerRef
    SecondaryTarget: PlayerRef


KnownEventPayload: TypeAlias = (
    UpdateStatePayload
    | BallHitPayload
    | BoostPickupPayload
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
    | PlayerJoinedPayload
    | PlayerLeftPayload
    | PodiumStartPayload
    | ReplayCreatedPayload
    | RoundStartedPayload
    | StatfeedEventPayload
)

KnownEventPayloadMap: TypeAlias = dict[EventName, KnownEventPayload]

TData = TypeVar("TData", bound=Mapping[str, Any])


@dataclass(slots=True)
class TypedEventMessage(Generic[TData]):
    """Event envelope parameterized by its specific payload ``TypedDict``.

    Attributes:
        event: Event name string.
        data: Typed payload mapping for the event.
        raw: Optional raw JSON string from the stream.
    """

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
    event_name: Literal["BoostPickup"], data: Mapping[str, Any]
) -> BoostPickupPayload: ...


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
    event_name: Literal["PlayerJoined"], data: Mapping[str, Any]
) -> PlayerJoinedPayload: ...


@overload
def cast_event_data(
    event_name: Literal["PlayerLeft"], data: Mapping[str, Any]
) -> PlayerLeftPayload: ...


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
    """Narrow ``data`` to the ``TypedDict`` matching ``event_name`` without runtime cost.

    Args:
        event_name: Rocket League event name.
        data: Decoded payload mapping from ``EventMessage.data``.

    Returns:
        Mapping[str, Any]: The unmodified ``data`` mapping with narrowed static type.
    """
    _ = event_name
    return cast(Mapping[str, Any], data)

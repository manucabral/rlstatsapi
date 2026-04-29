# Event Reference

This page lists each documented event and the main fields you can expect in `msg.data`.

## UpdateState

**Payload type:** `UpdateStatePayload`

Main keys:
- `MatchGuid: str` (online/LAN)
- `Players: list[UpdateStatePlayer]`
- `Game: UpdateStateGame`

`Game` commonly includes:
- `Teams`, `TimeSeconds`, `bOvertime`, `Ball`
- `bReplay`, `bHasWinner`, `Winner`, `Arena`
- `bHasTarget`, `Target`

## BallHit

**Payload type:** `BallHitPayload`

Main keys:
- `MatchGuid: str`
- `Players: list[PlayerRef]`
- `Ball: { PreHitSpeed, PostHitSpeed, Location }`

## ClockUpdatedSeconds

**Payload type:** `ClockUpdatedSecondsPayload`

Main keys:
- `MatchGuid: str`
- `TimeSeconds: int`
- `bOvertime: bool`

## CountdownBegin

**Payload type:** `CountdownBeginPayload`

Main keys:
- `MatchGuid: str`

## CrossbarHit

**Payload type:** `CrossbarHitPayload`

Main keys:
- `MatchGuid: str`
- `BallLocation: Vector3`
- `BallSpeed: float`
- `ImpactForce: float`
- `BallLastTouch: { Player, Speed }`

## GoalReplayEnd

**Payload type:** `GoalReplayEndPayload`

Main keys:
- `MatchGuid: str`

## GoalReplayStart

**Payload type:** `GoalReplayStartPayload`

Main keys:
- `MatchGuid: str`

## GoalReplayWillEnd

**Payload type:** `GoalReplayWillEndPayload`

Main keys:
- `MatchGuid: str`

## GoalScored

**Payload type:** `GoalScoredPayload`

Main keys:
- `MatchGuid: str`
- `GoalSpeed: float`
- `GoalTime: float`
- `ImpactLocation: Vector3`
- `Scorer: PlayerRef`
- `Assister: PlayerRef` (conditional)
- `BallLastTouch: { Player, Speed }`

## MatchCreated

**Payload type:** `MatchCreatedPayload`

Main keys:
- `MatchGuid: str`

## MatchInitialized

**Payload type:** `MatchInitializedPayload`

Main keys:
- `MatchGuid: str`

## MatchDestroyed

**Payload type:** `MatchDestroyedPayload`

Main keys:
- `MatchGuid: str`

## MatchEnded

**Payload type:** `MatchEndedPayload`

Main keys:
- `MatchGuid: str`
- `WinnerTeamNum: int`

## MatchPaused

**Payload type:** `MatchPausedPayload`

Main keys:
- `MatchGuid: str`

## MatchUnpaused

**Payload type:** `MatchUnpausedPayload`

Main keys:
- `MatchGuid: str`

## PodiumStart

**Payload type:** `PodiumStartPayload`

Main keys:
- `MatchGuid: str`

## ReplayCreated

**Payload type:** `ReplayCreatedPayload`

Main keys:
- `MatchGuid: str`

## RoundStarted

**Payload type:** `RoundStartedPayload`

Main keys:
- `MatchGuid: str`

## StatfeedEvent

**Payload type:** `StatfeedEventPayload`

Main keys:
- `MatchGuid: str`
- `EventName: str`
- `Type: str`
- `MainTarget: PlayerRef`
- `SecondaryTarget: PlayerRef` (conditional)

## Common nested types

- `Vector3`: `X`, `Y`, `Z`
- `PlayerRef`: `Name`, `Shortcut`, `TeamNum`
- `TeamState`: `Name`, `TeamNum`, `Score`, `ColorPrimary`, `ColorSecondary`

## Practical usage

Use `cast_event_data(...)` to get strong autocomplete for event-specific fields:

```python
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    print(data.get("Scorer", {}).get("Name"))
```

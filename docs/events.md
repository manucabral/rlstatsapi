# Event Reference

Each event arrives as an `EventMessage` with two fields:

- `event` — the event name string
- `data` — a dict with the payload fields shown below

Use [`cast_event_data`](api.md) to get typed autocomplete for a specific event.

---

## UpdateState

Fired repeatedly while a match is live. Contains full game + player snapshot.

```json
{
  "event": "UpdateState",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "Players": [
      {
        "Name": "Psyonix",
        "PrimaryId": "76561198000000000",
        "Shortcut": 0,
        "TeamNum": 0,
        "Score": 100,
        "Goals": 1,
        "Shots": 2,
        "Assists": 0,
        "Saves": 1,
        "Touches": 12,
        "CarTouches": 10,
        "Demos": 0,
        "Loadout": ["body_grain", "Skin_bartees", "Wheel_SoccerBall", "Boost_AlphaReward", "None", "None"],
        "bHasCar": true,
        "Speed": 1400.0,
        "Boost": 72,
        "bBoosting": false,
        "bOnGround": true,
        "bOnWall": false,
        "bPowersliding": false,
        "bDemolished": false,
        "bSupersonic": false,
        "PickupClass": "SpecialPickup_GrapplingHook_TA"
      }
    ],
    "Game": {
      "Teams": [
        {
          "Name": "Blue",
          "TeamNum": 0,
          "Score": 1,
          "ColorPrimary": "#0000FF",
          "ColorSecondary": "#FFFFFF"
        },
        {
          "Name": "Orange",
          "TeamNum": 1,
          "Score": 0,
          "ColorPrimary": "#FF8800",
          "ColorSecondary": "#000000"
        }
      ],
      "PlaylistId": 11,
      "TimeSeconds": 204,
      "bOvertime": false,
      "Frame": 6120,
      "Elapsed": 102.0,
      "Ball": {
        "Speed": 800.0,
        "TeamNum": 255
      },
      "bReplay": false,
      "bHasWinner": false,
      "Winner": "",
      "Arena": "Stadium_P",
      "bHasTarget": false
    }
  }
}
```

Fields added in v2.72:

| Field | Type | Notes |
|---|---|---|
| `Players[].Loadout` | `list[str]` | Equipped item asset names by product slot. Empty slots are `"None"` |
| `Players[].PickupClass` | `str` | Rumble power-up the player holds. Spectator only, absent outside Rumble |
| `Game.PlaylistId` | `int` | Playlist of the current match |

---

## BallHit

Fired when a player hits the ball.

```json
{
  "event": "BallHit",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "Players": [
      {
        "Name": "Psyonix",
        "Shortcut": 0,
        "TeamNum": 0
      }
    ],
    "Ball": {
      "PreHitSpeed": 0.0,
      "PostHitSpeed": 1200.5,
      "Location": {
        "X": 120.0,
        "Y": -200.0,
        "Z": 95.0
      }
    }
  }
}
```

---

## BoostPickup

Fired when a car collects a boost pad or pill. Spectator only.

```json
{
  "event": "BoostPickup",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "Player": { "Name": "PlayerA", "Shortcut": 1, "TeamNum": 0 },
    "Location": { "X": -3072, "Y": 0, "Z": 73 },
    "BoostAmount": 100,
    "BoostType": "BoostType_Pill",
    "bReplay": false
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `Player` | `PlayerRef` | Player who collected the boost |
| `Location` | `Vector3` | World position of the pickup |
| `BoostAmount` | `float` | Boost granted |
| `BoostType` | `str` | `BoostType_Pad` (small) or `BoostType_Pill` (full) |
| `bReplay` | `bool` | `true` if it happened during replay playback |

---

## ClockUpdatedSeconds

Fired each second while the match clock is running.

```json
{
  "event": "ClockUpdatedSeconds",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "TimeSeconds": 187,
    "bOvertime": false
  }
}
```

---

## CountdownBegin

Fired when the pre-kickoff countdown starts.

```json
{
  "event": "CountdownBegin",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## CrossbarHit

Fired when the ball hits the crossbar.

```json
{
  "event": "CrossbarHit",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "BallLocation": {
      "X": 0.0,
      "Y": -5120.0,
      "Z": 642.775
    },
    "BallSpeed": 2100.3,
    "ImpactForce": 0.85,
    "BallLastTouch": {
      "Player": {
        "Name": "Psyonix",
        "Shortcut": 0,
        "TeamNum": 0
      },
      "Speed": 1980.0
    }
  }
}
```

---

## GoalScored

Fired when a goal is scored.

```json
{
  "event": "GoalScored",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "GoalSpeed": 2280.5,
    "GoalTime": 155.3,
    "ImpactLocation": {
      "X": -42.0,
      "Y": -5120.0,
      "Z": 200.0
    },
    "Scorer": {
      "Name": "Psyonix",
      "Shortcut": 0,
      "TeamNum": 0
    },
    "Assister": {
      "Name": "Ghosting",
      "Shortcut": 1,
      "TeamNum": 0
    },
    "BallLastTouch": {
      "Player": {
        "Name": "Psyonix",
        "Shortcut": 0,
        "TeamNum": 0
      },
      "Speed": 2280.5
    }
  }
}
```

> `Assister` is absent when no assist was awarded.

---

## GoalReplayStart

Fired when the goal replay begins.

```json
{
  "event": "GoalReplayStart",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## GoalReplayWillEnd

Fired shortly before the goal replay ends.

```json
{
  "event": "GoalReplayWillEnd",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## GoalReplayEnd

Fired when the goal replay ends.

```json
{
  "event": "GoalReplayEnd",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## MatchCreated

Fired when a match session is created (before initialization).

```json
{
  "event": "MatchCreated",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## MatchInitialized

Fired when the match finishes loading and is ready to start.

```json
{
  "event": "MatchInitialized",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## MatchDestroyed

Fired when the match session is torn down.

```json
{
  "event": "MatchDestroyed",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## MatchEnded

Fired when a match finishes. Includes the winning team.

```json
{
  "event": "MatchEnded",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "WinnerTeamNum": 0
  }
}
```

Since v2.76 a no-contest match reports `"WinnerTeamNum": -1`. `client.state.no_contest` is then `True` and `has_winner` stays `False`.

---

## MatchPaused

Fired when the match is paused.

```json
{
  "event": "MatchPaused",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## MatchUnpaused

Fired when the match resumes after a pause.

```json
{
  "event": "MatchUnpaused",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## PlayerJoined

Fired when a player is added to the current match.

```json
{
  "event": "PlayerJoined",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "PlayerName": "PlayerA",
    "PrimaryId": "Steam|123|0"
  }
}
```

---

## PlayerLeft

Fired when a player is removed from the current match.

```json
{
  "event": "PlayerLeft",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "PlayerName": "PlayerA",
    "PrimaryId": "Steam|123|0"
  }
}
```

---

## PodiumStart

Fired when the post-match podium sequence begins.

```json
{
  "event": "PodiumStart",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## ReplayCreated

Fired when a replay loaded from Match History starts. Goal replays do not fire it.

```json
{
  "event": "ReplayCreated",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "FileName": "Stadium_P_2026-06-05_18-42",
    "Date": "2026-06-05 18:42:13"
  }
}
```

`FileName` can be passed to the [`LoadReplay`](commands.md) command.

---

## RoundStarted

Fired when a new round begins (after kickoff countdown).

```json
{
  "event": "RoundStarted",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

---

## StatfeedEvent

Fired for statfeed notifications (Epic Save, Aerial Goal, Hat Trick, etc.).

```json
{
  "event": "StatfeedEvent",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6",
    "EventName": "EpicSave",
    "Type": "Save",
    "MainTarget": {
      "Name": "Psyonix",
      "Shortcut": 0,
      "TeamNum": 0
    },
    "SecondaryTarget": {
      "Name": "Ghosting",
      "Shortcut": 1,
      "TeamNum": 1
    }
  }
}
```

> `SecondaryTarget` is absent when the stat has no secondary player.

---

## Common types

### Vector3

```json
{ "X": 0.0, "Y": 0.0, "Z": 0.0 }
```

### PlayerRef

```json
{ "Name": "Psyonix", "Shortcut": 0, "TeamNum": 0 }
```

### TeamState

```json
{
  "Name": "Blue",
  "TeamNum": 0,
  "Score": 1,
  "ColorPrimary": "#0000FF",
  "ColorSecondary": "#FFFFFF"
}
```

### BallLastTouch

```json
{
  "Player": { "Name": "Psyonix", "Shortcut": 0, "TeamNum": 0 },
  "Speed": 1980.0
}
```

---

## Usage

```python
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    print(f"{scorer.get('Name')} scored!")
```

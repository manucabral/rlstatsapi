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
        "bHasCar": true,
        "Speed": 1400.0,
        "Boost": 72,
        "bBoosting": false,
        "bOnGround": true,
        "bOnWall": false,
        "bPowersliding": false,
        "bDemolished": false,
        "bSupersonic": false
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

Fired when an in-match replay starts (e.g. goal replay saved as replay).

```json
{
  "event": "ReplayCreated",
  "data": {
    "MatchGuid": "A1B2C3D4E5F6"
  }
}
```

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

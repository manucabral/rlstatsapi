# Commands

Since Rocket League v2.72 the game accepts commands on the same socket it uses
to send events. `StatsClient` can send all six documented commands.

```python
import asyncio
from rlstatsapi import StatsClient


async def main() -> None:
    async with StatsClient() as client:
        await client.wait_for("UpdateState")
        await client.set_hud_visibility(False)
        await client.change_pov(focus="Ball", perspective="Fly")


asyncio.run(main())
```

The game does not reply to commands, and it drops malformed ones without an
error. For that reason every command is validated before it is written, and an
invalid one raises `InvalidCommandError` (a `ValueError`). To confirm a command
worked, watch the event stream: `SetMatchPaused` is followed by `MatchPaused`
or `MatchUnpaused`, and `LoadReplay` by `ReplayCreated`.

Sending while disconnected raises `ConnectionError`.

## Reference

| Method | Command | Where it works |
| --- | --- | --- |
| `change_pov(focus=None, perspective=None)` | `ChangePOV` | Spectator, replay |
| `load_replay(file_name=None, path=None)` | `LoadReplay` | Anywhere |
| `seek_replay(frame=None, time_seconds=None)` | `SeekReplay` | Replay |
| `set_game_speed(speed)` | `SetGameSpeed` | Replay |
| `set_hud_visibility(visible)` | `SetHUDVisibility` | Anywhere |
| `set_match_paused(paused)` | `SetMatchPaused` | Match or replay |

### change_pov

At least one argument is required.

- `focus`: `"Ball"`, or a player's spectator shortcut as an `int` or a digit
  string. The shortcut is the `Shortcut` field of each player in `UpdateState`.
- `perspective`: `"Fly"`, `"SoftAttach"`, `"HardAttach"`, `"PlayerView"`,
  `"AutoCam"` or `"Camera_Director"`. When you focus a player and give no
  perspective, the game uses `PlayerView`.

### load_replay

Pass `file_name` or `path`. If both are set the game uses `file_name`. The
`ReplayCreated` event carries a `FileName` you can pass back here.

### seek_replay

Pass `frame` or `time_seconds`. If both are set the game uses `frame`.

### set_game_speed

`1.0` is normal speed, `0.5` half, `2.0` double. Must be 0 or greater.

## Raw envelopes

The wire format is `{"Command": "<name>", "Data": {...}}`. You can send it
directly, by name or as a dict. Both forms go through the same validation.

```python
await client.send_command("SetGameSpeed", {"Speed": 0.5})
await client.send_command({"Command": "SetMatchPaused", "Data": {"bPaused": True}})
```

The builders in `rlstatsapi.commands` return the envelope without sending it:

```python
from rlstatsapi import commands, encode_command

envelope = commands.seek_replay(time_seconds=120.5)
payload = encode_command(envelope)  # b'{"Command":"SeekReplay","Data":{"TimeSeconds":120.5}}'
```

## From the CLI

```bash
rlstatsapi send SetHUDVisibility '{"bVisible": false}'
rlstatsapi send ChangePOV '{"Focus": "1", "Perspective": "PlayerView"}'
```

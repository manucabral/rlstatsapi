# Rocket League Stats API
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![PyPI version](https://img.shields.io/pypi/v/rlstatsapi.svg)](https://pypi.org/project/rlstatsapi/) [![Pylint](https://github.com/manucabral/RocketLeagueStatsAPI/actions/workflows/pylint.yml/badge.svg)](https://github.com/manucabral/RocketLeagueStatsAPI/actions/workflows/pylint.yml)
![Downloads](https://img.shields.io/pypi/dm/rlstatsapi)


`rlstatsapi` is a simple and fast Python client for reading live Rocket League Stats API events over a local TCP socket.

[Click here for full documentation](https://manucabral.github.io/RocketLeagueStatsAPI/)


## Install

From PyPI:

```bash
pip install rlstatsapi
```

From GitHub (latest `main`):

```bash
pip install git+https://github.com/manucabral/RocketLeagueStatsAPI.git
```

## Rocket League setup

Before launching Rocket League, edit:

`<Install Dir>\TAGame\Config\DefaultStatsAPI.ini`

Use at least:

- `PacketSendRate=30` (any value `> 0` enables the exporter)
- `Port=49123`

Restart the game after changing the file.

## Quick start

```python
import asyncio
from rlstatsapi import StatsClient

async def main() -> None:
    async with StatsClient() as client:
        client.on_any(lambda msg: print(msg.event, msg.data))
        await asyncio.Event().wait()

asyncio.run(main())
```

## Demos
<img width="800" height="411" alt="allevents" src="https://github.com/manucabral/RocketLeagueStatsAPI/blob/main/docs/videos/allevents.gif" />
<img width="800" height="411" alt="ui" src="https://github.com/manucabral/RocketLeagueStatsAPI/blob/main/docs/videos/ui.gif" />


## Typed event handlers

Every known event has a typed convenience method. No manual casting needed.

```python
import asyncio
from rlstatsapi import StatsClient, TypedEventMessage, GoalScoredPayload

async def on_goal(msg: TypedEventMessage[GoalScoredPayload]) -> None:
    scorer = msg.data.get("Scorer", {})
    speed = msg.data.get("GoalSpeed", 0.0)
    print(f"Goal by {scorer.get('Name')} at {speed:.0f} km/h")

async def main() -> None:
    async with StatsClient() as client:
        client.on_goal_scored(on_goal)
        await asyncio.Event().wait()

asyncio.run(main())
```

The decorator form of `on()` is also supported:

```python
@client.on("GoalScored")
async def on_goal(msg: TypedEventMessage[GoalScoredPayload]) -> None:
    ...
```

## Connection events

```python
client.on_connect(lambda: print("Connected"))
client.on_disconnect(lambda: print("Disconnected"))
```

## Error handling

```python
def on_error(event_name: str, exc: Exception) -> None:
    print(f"Handler error for {event_name}: {exc}")

client.on_handler_error(on_error)
```

Without a registered error handler, exceptions log at `ERROR` level automatically.

## Handler deregistration

```python
client.off("GoalScored", my_handler)
client.off_any(my_handler)

# Fire once then auto-remove
client.once("MatchCreated", lambda msg: print("Match started"))
```

## Logging

Use the standard `logging` module, no library-specific flags needed:

```python
import logging
logging.getLogger("rlstatsapi").setLevel(logging.DEBUG)
```

## `StatsClient` parameters

| Parameter | Default | Description |
|---|---|---|
| `host` | `"127.0.0.1"` | TCP host |
| `port` | `49123` | TCP port |
| `reconnect` | `True` | Auto-reconnect on drop |
| `reconnect_delay` | `0.5` | Initial reconnect delay (s) |
| `max_reconnect_delay` | `30.0` | Backoff cap (s) |
| `max_reconnect_attempts` | `None` | Max retries (`None` = infinite) |
| `connect_timeout` | `5.0` | TCP connect timeout (s) |
| `include_raw` | `False` | Include raw JSON string in `EventMessage.raw` |
| `queue_size` | `2048` | Internal event queue size |
| `overflow` | `"block"` | Queue-full policy: `"block"` / `"drop"` / `"raise"` |


## `is_connected`

```python
print(client.is_connected)  # True once TCP is established
```

## Public API

**Registration:**
`on(event_name, handler)` · `on_any(handler)` · `on_<event>(handler)` · `on_connect(handler)` · `on_disconnect(handler)` · `on_handler_error(handler)`

**Deregistration:**
`off(event_name, handler)` · `off_any(handler)` · `once(event_name, handler)`

**Lifecycle:**
`connect()` · `disconnect()` · `async with StatsClient()`

**Async iteration:**
`events()` async iterator yielding `EventMessage`

**Types:**
`EventName` · `TypedEventMessage[T]` · `KnownEventMessage` · per-event payload types (`GoalScoredPayload`, `UpdateStatePayload`, …)

## Notes

- Works for regular matches. Some fields like `MatchGuid` are only present in online/LAN contexts.
- In current builds this endpoint may behave as a plain TCP JSON stream instead of a WebSocket upgrade. This library handles the TCP stream format.


## Disclaimer

This project is an independent, community-made library and is **not affiliated with, endorsed by, or sponsored by Psyonix or Epic Games**.

Rocket League and related trademarks are the property of their respective owners.  
Use this library at your own risk and in compliance with Rocket League’s terms and policies.


## Contributors
Individuals who support the project through code, feedback, testing, documentation, or maintenance.

<a href="https://github.com/manucabral/RocketLeagueStatsAPI/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=manucabral/RocketLeagueStatsAPI" />
</a>

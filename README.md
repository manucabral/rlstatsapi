# RL Stats API

`rlstatsapi` is a simple and fast Python client for reading live Rocket League Stats API events over a local TCP socket.

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
import logging
from rlstatsapi import StatsClient

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    client = StatsClient(log_enabled=True)
    client.on_any(lambda msg: print(msg.event, msg.data))

    await client.connect()
    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


asyncio.run(main())
```

## Public API

- `StatsClient(host="127.0.0.1", port=49123, reconnect=True, reconnect_delay=0.5, include_raw=False, queue_size=2048, connect_timeout=5.0, log_enabled=False)`
- `connect()` / `disconnect()`
- `on(event_name, handler)`
- `on_any(handler)`
- `events()`
- typed helpers: `EventName`, `TypedEventMessage[...]`, `cast_event_data(...)`

## Typed event example (Pylance-friendly)

```python
import asyncio
from rlstatsapi import StatsClient
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


async def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    print("Goal by:", scorer.get("Name"))


async def main() -> None:
    client = StatsClient()
    client.on("GoalScored", on_goal)
    await client.connect()
    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


asyncio.run(main())
```

## Notes

- Works for regular matches. Some fields like `MatchGuid` are only present in online/LAN contexts.
- In current builds this endpoint may behave as plain TCP JSON stream instead of websocket upgrade. This library handles the TCP stream format.

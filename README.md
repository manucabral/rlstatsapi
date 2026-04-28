# RL Stats API
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![PyPI version](https://img.shields.io/pypi/v/rlstatsapi.svg)](https://pypi.org/project/rlstatsapi/) [![Pylint](https://github.com/manucabral/RocketLeagueStatsAPI/actions/workflows/pylint.yml/badge.svg)](https://github.com/manucabral/RocketLeagueStatsAPI/actions/workflows/pylint.yml)



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

## Example Event (Goals)

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


## Public API

- `StatsClient(...)`
- `connect()` / `disconnect()`
- `on(event_name, handler)`
- `on_any(handler)`
- `events()`
- typed helpers: `EventName`, `TypedEventMessage[...]`, `cast_event_data(...)`


## Notes

- Works for regular matches. Some fields like `MatchGuid` are only present in online/LAN contexts.
- In current builds this endpoint may behave as plain TCP JSON stream instead of websocket upgrade. This library handles the TCP stream format.

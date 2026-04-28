# rlstatsapi

Simple and fast Python client to read Rocket League Stats API events.

## Install

```bash
pip install -e .
```

## Configure Rocket League

Before starting the game, edit:

`<Install Dir>\TAGame\Config\DefaultStatsAPI.ini`

Minimum required values:

- `PacketSendRate=60` (any value > 0)
- `Port=49123`

Then restart Rocket League.

## Quick usage

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

- `StatsClient(...)`
- `connect()`
- `disconnect()`
- `on(event_name, handler)`
- `on_any(handler)`
- `events()`

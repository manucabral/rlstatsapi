# RL Stats API

`rlstatsapi` is a simple and fast Python client for reading live Rocket League Stats API websocket events.

## Install

From PyPI:

```bash
pip install rlstatsapi
```

From GitHub (latest `main`):

```bash
pip install git+https://github.com/nania/RocketLeagueStatsAPI.git
```

## Rocket League setup

Before launching Rocket League, edit:

`<Install Dir>\TAGame\Config\DefaultStatsAPI.ini`

Use at least:

- `PacketSendRate=60` (any value `> 0` enables the socket)
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

## Notes

- Works for regular matches, some fields like `MatchGuid` are only present in online/LAN contexts.
- If you see connection refused, Rocket League is not exposing the socket yet (check config and restart).

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


## Simple Example

https://github.com/user-attachments/assets/0a732000-37dd-48c4-b5f7-cc691abb4e92



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

- Works for regular matches. Some fields like `MatchGuid` are only present in online/LAN contexts.
- In current builds this endpoint may behave as plain TCP JSON stream instead of websocket upgrade. This library handles the TCP stream format.

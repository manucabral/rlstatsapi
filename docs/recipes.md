# Recipes

## Log goals only

```python
import asyncio
from rlstatsapi import StatsClient
from rlstatsapi.types import GoalScoredPayload, cast_event_data


def on_goal(msg) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    print("Goal by:", scorer.get("Name"))


async def main() -> None:
    async with StatsClient() as client:
        client.on("GoalScored", on_goal)
        await asyncio.Event().wait()
```

## Detect match start and end

```python
import asyncio
from rlstatsapi import StatsClient


async def main() -> None:
    async with StatsClient() as client:
        client.on_many(
            ["MatchCreated", "RoundStarted", "MatchEnded", "MatchDestroyed"],
            lambda msg: print(msg.event),
        )
        await asyncio.Event().wait()
```

## Write all changed payloads to a file

```bash
python examples/all_events_to_txt.py
```

Keeps a per-event snapshot and only writes when the payload changes.

## Keep your client port in sync with the config file

```python
from rlstatsapi import StatsClient, configure_stats_api

status = configure_stats_api(enabled=True, port=49123, packet_send_rate=30)
client = StatsClient(port=status.port or 49123)
```

Restart Rocket League after changing the config file.

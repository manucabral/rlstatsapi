# Quickstart

## Basic listener

```python
import asyncio
from rlstatsapi import StatsClient


async def main() -> None:
    async with StatsClient() as client:
        client.on_any(lambda msg: print(msg.event, msg.data))
        await asyncio.Event().wait()


asyncio.run(main())
```

This prints incoming events from the local Rocket League exporter.

## Typed payload pattern (Pylance-friendly)

```python
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    print(scorer.get("Name"))
```

Why this pattern:

- `StatsClient.on(...)` handlers receive `EventMessage`
- `cast_event_data(...)` narrows to the event-specific payload type
- no runtime validation overhead

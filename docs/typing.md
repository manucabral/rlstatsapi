# Typing

`rlstatsapi` provides typed payload models for known events.

## Pylance-friendly pattern

```python
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    print(scorer.get("Name"))
```

## Why this pattern

- `StatsClient.on(...)` handlers receive `EventMessage`.
- `cast_event_data(...)` narrows the payload type for IDE autocomplete.
- No runtime validation overhead is added.

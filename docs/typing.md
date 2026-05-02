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

## Alternative helper on the message itself

```python
from rlstatsapi.models import EventMessage


def on_goal(msg: EventMessage) -> None:
    typed = msg.as_type("GoalScored")
    print(typed.data.get("Scorer", {}).get("Name"))
```

## Why this pattern

- `StatsClient.on(...)` handlers receive `EventMessage`.
- `cast_event_data(...)` narrows the payload type for IDE autocomplete.
- `msg.as_type(...)` wraps the same cast in a shorter form when you prefer it.
- No runtime validation overhead is added.

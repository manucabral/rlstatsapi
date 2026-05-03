# Examples

Available scripts in `examples/`:

- `all_events_to_txt.py`: log all events and persist changed payloads to a text file.
- `event_names_only.py`: print event names as they arrive.
- `clock_updates.py`: listen to `ClockUpdatedSeconds` and print the game clock.
- `goal_scored_typed.py`: typed `GoalScored` handler with scorer name and speed.
- `configure_and_connect.py`: configure the exporter and connect with the same port.
- `match_lifecycle.py`: track the full match lifecycle from creation to destruction.
- `decorator_handlers.py`: register handlers using the decorator form of `client.on()`.
- `statfeed_events.py`: print `StatfeedEvent` highlights - saves, shots, demos, etc.
- `live_scoreboard.py`: print a live scoreboard using the `client.state` snapshot.

Run from repository root:

```bash
python examples/event_names_only.py
```

For more practical snippets, see [Recipes](recipes.md).

# Examples

- `event_names_only.py` - prints every event name as it arrives.
- `all_events_to_txt.py` - logs all changed payloads to `events_log.txt`.
- `configure_and_connect.py` - writes `TAStatsAPI.ini` then connects.
- `live_scoreboard.py` - live score and clock via `client.state`.
- `clock_updates.py` - match clock with overtime flag.
- `goal_scored_typed.py` - scorer, assist and speed on every goal.
- `match_lifecycle.py` - full match flow from creation to destruction.
- `statfeed_events.py` - highlights (saves, demos, shots) with icons.
- `decorator_handlers.py` - registering handlers with `@client.on(...)`.

```bash
python examples/<file>.py
```

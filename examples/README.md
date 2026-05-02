# Examples

- `all_events_to_txt.py`: logs all events and writes changed payloads to `events_log.txt`.
- `goal_scored_typed.py`: typed example for `GoalScored` using `cast_event_data`.
- `event_names_only.py`: prints only event names.
- `clock_updates.py`: listens only to `ClockUpdatedSeconds` using `cast_event_data`.
- `configure_and_connect.py`: updates `TAStatsAPI.ini` and connects with the same port.

Run any example from root:

```bash
python examples/<file>.py
```

For CLI-based checks, you can also run:

```bash
rlstatsapi status
rlstatsapi listen --event GoalScored
```

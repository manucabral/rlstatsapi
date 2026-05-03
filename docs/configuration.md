# Configuration

Automatic setup from Python:

```python
from rlstatsapi import configure_stats_api

configure_stats_api(enabled=True, port=49123, packet_send_rate=30)
```

Or from the CLI:

```bash
rlstatsapi enable --port 49123 --rate 30
rlstatsapi disable
rlstatsapi status
```

Or manually by editing:

`Documents\My Games\Rocket League\TAGame\Config\TAStatsAPI.ini`

Recommended minimum:

```ini
[TAGame.MatchStatsExporter_TA]
Port=49123
PacketSendRate=30
```

Notes:

- `PacketSendRate > 0` enables exporting.
- Restart Rocket League after changing the config file in either method.
- Config discovery is currently Windows-first.
- Use the same `host` and `port` in `StatsClient`.

# Configuration

You can enable Stats API automatically:

```python
from rlstatsapi import configure_stats_api

configure_stats_api(enabled=True, port=49123, packet_send_rate=30)
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
- Use the same `host` and `port` in `StatsClient`.

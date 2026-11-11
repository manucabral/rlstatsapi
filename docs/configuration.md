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
WebPort=49124
PacketSendRate=30
```

| Key | Default | Meaning |
| --- | --- | --- |
| `PacketSendRate` | `0` | `UpdateState` messages per second, up to 120. `0` disables the API. |
| `Port` | `49123` | TCP port. This is the one `StatsClient` connects to. |
| `WebPort` | `49124` | WebSocket port. `0` disables it. Must differ from `Port`. |

To change the WebSocket port from Python:

```python
from rlstatsapi import set_stats_api_web_port

set_stats_api_web_port(0)  # disable the WebSocket listener
```

Notes:

- `PacketSendRate > 0` enables exporting.
- Restart Rocket League after changing the config file in either method.
- Config discovery is currently Windows-first.
- The game reads `TAStatsAPI.ini` and falls back to `DefaultStatsAPI.ini`. Discovery follows the same order.
- The helpers refuse to write equal `Port` and `WebPort` values.
- Use the same `host` and `port` in `StatsClient`.

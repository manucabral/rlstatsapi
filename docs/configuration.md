# Configuration

Before launching Rocket League, edit:

`<Install Dir>\\TAGame\\Config\\DefaultStatsAPI.ini`

Recommended minimum:

```ini
[TAGame.MatchStatsExporter_TA]
Port=49123
PacketSendRate=30
```

Notes:

- `PacketSendRate > 0` enables exporting.
- Restart Rocket League after changing the file.
- Use the same `host` and `port` in `StatsClient`.

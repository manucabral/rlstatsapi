# RPC Bridge

Discord Rich Presence bridge for Rocket League Stats API events.

## Requirements

- Discord desktop app running
- Rocket League with Stats API enabled
- `DISCORD_CLIENT_ID` from your Discord application

## Run

```bash
python -m rpc.run --discord-client-id YOUR_CLIENT_ID
```

Or with env var:

```bash
set DISCORD_CLIENT_ID=YOUR_CLIENT_ID
python -m rpc.run
```

## Optional flags

- `--host` (default `127.0.0.1`)
- `--port` (default `49123`)
- `--throttle-seconds` (default `1.0`)
- `--debug`
- `--rpc-debug`

## What it shows

- Match phase (countdown, in match, replay, paused, ended)
- Scoreline (Blue vs Orange)
- Match clock / overtime
- Arena name
- Goal highlights (`Goal by <player>`)

# Changelog

All notable changes to this project will be documented in this file.

## 0.1.8

Tracks the Stats API changes from Rocket League v2.72 (2026-08-04) and v2.76 (2026-09-22).

### Added
- Game commands: `StatsClient.send_command()` plus `change_pov()`, `load_replay()`, `seek_replay()`, `set_game_speed()`, `set_hud_visibility()` and `set_match_paused()`. Commands are validated locally and raise `InvalidCommandError`, because the game drops malformed ones silently
- `rlstatsapi.commands` module with envelope builders, `build_command()`, `encode_command()`, `COMMAND_NAMES` and `PERSPECTIVES`
- `rlstatsapi send <Command> '<json>'` CLI subcommand
- Events `BoostPickup`, `PlayerJoined` and `PlayerLeft`, with payload types, `on(...)` overloads and `on_boost_pickup()`, `on_player_joined()`, `on_player_left()`
- Payload fields `Loadout` and `PickupClass` (players), `PlaylistId` (game), `FileName` and `Date` (`ReplayCreated`)
- `MatchStateSnapshot.playlist_id`, `winner_team_num` and `no_contest`. Since v2.76 `MatchEnded` reports `WinnerTeamNum = -1` for a no-contest match
- `WebPort` support: `StatsAPIConfigStatus.web_port`, `set_stats_api_web_port()`, `configure_stats_api(web_port=...)`, `rlstatsapi enable --web-port` and `DEFAULT_STATS_API_WEB_PORT`
- Optional `orjson` backend: `pip install rlstatsapi[fast]`. `rlstatsapi.JSON_BACKEND` tells which one is in use

### Changed
- `MatchStateTracker` applies `UpdateState` lazily, when `client.state` is read or another event arrives. A `MatchStateSnapshot` reference kept from an earlier read is no longer refreshed on every tick; read `client.state` again
- `MatchEnded` with `WinnerTeamNum = -1` leaves `has_winner` as `False`
- Config helpers raise `ValueError` when `Port` and `WebPort` would be equal, which the game does not accept
- Config discovery also finds `DefaultStatsAPI.ini` when `TAStatsAPI.ini` does not exist, in the order the game uses
- `PacketSendRate` written as a float (`60.0`) is now parsed

### Improved
- Stream decoding works on bytes and frames messages without a second parse. Measured on `UpdateState` with six players, one message per read: 43 to 15 microseconds per event with `orjson`, 43 to 30 with the standard library
- Messages split across TCP reads no longer trigger a failed parse per read: 82 to 27 microseconds per event with `orjson`, 82 to 49 without
- An invalid message in the middle of the stream is skipped instead of stalling the reader until the buffer limit

### Notes
- Since v2.76 `GoalScored` also fires during replay playback and has no replay flag. Check `client.state.replay_active`
- `BoostPickup` is only sent while spectating

## 0.1.7

### Added
- `StatsClient(track_state=True)` option to toggle automatic `MatchStateSnapshot` tracking
- `StatsClient.off_connect(handler)`, `off_disconnect(handler)`, and `off_handler_error(handler)` unregistration methods
- Constructor argument validation for `port`, `reconnect_delay`, `max_reconnect_delay`, `max_reconnect_attempts`, `queue_size`, `overflow`, `connect_timeout`, and `handler_timeout`

### Fixed
- Queue deadlock when operating in callback-only mode without consuming `events()`
- Memory and handler leak in `wait_for()` when cancelled before the expected event arrives
- `handler_timeout` bypass for coroutines registered with `@client.on(...)` or `client.once(...)`
- UTF-8 multibyte boundary corruption across TCP stream chunks using `codecs.getincrementaldecoder`
- `ConnectionState` remaining in `CONNECTING` after initial connection failure with `reconnect=False`
- False warning when parsing `[TAGame.MatchStatsExporter_TA]` section headers in `TAStatsAPI.ini`
- Duplicate keys in `TAStatsAPI.ini` when saving settings
- `EventMessage.as_type()` dropping the `raw` transport string
- `MatchStateTracker` missing updates for `ClockUpdatedSeconds`, `GoalReplayStart`, and `GoalReplayEnd`, and losing `event_counts` on `MatchDestroyed`
- Example handler signature in `examples/all_events_to_txt.py` and assist text formatting in `examples/goal_scored_typed.py`

### Improved
- TCP JSON stream decoding performance using cursor-based `raw_decode`, reducing decoding memory peak by ~18x
- Standardized all module, class, and method docstrings to Google style
- Increased unit test suite coverage from 32 to 36 tests

## 0.1.6

### Added
- `StatsClient.wait_for(event_name, timeout=None)` - await the next occurrence of an event
- `PlayerSnapshot` dataclass with per-player stats (name, team, score, goals, assists, saves, shots, boost, speed, is_demolished)
- `MatchStateSnapshot.players` - list of all players from the latest `UpdateState`
- `MatchStateSnapshot.target_player` - the local/spectated player, resolved by `Game.Target.Shortcut`
- `ClientMetrics.reset()` - reset all counters and refresh `started_at`
- `ClientMetrics.started_at` - datetime the client (or last reset) was initialized
- `ConnectionState` enum with `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `FAILED`
- `StatsClient.connection_state` property exposing granular connection lifecycle state
- `StatsClient(handler_timeout=...)` - cancels slow async handlers after N seconds
- `disconnect(timeout=5.0)` - graceful shutdown with configurable wait timeout
- `ConnectionState` and `PlayerSnapshot` exported from the top-level `rlstatsapi` package

### Changed
- `on_handler_error` callback signature changed from `(event_name: str, exc)` to `(msg: EventMessage, exc, handler)` for full context

### Improved
- Docs: `examples.md` updated to list all 9 example scripts
- Docs: `configuration.md` now shows `disable` and `status` CLI commands
- Docs: `recipes.md` removed reference to non-existent `test.py`

## 0.1.5

### Added
- CLI entrypoint with `status`, `enable`, `disable`, and `listen` commands
- Event filtering with `StatsClient.events("...")`
- `StatsClient.on_many(...)` for registering one handler across several events
- `EventMessage.as_type(...)` for shorter typed narrowing
- Lightweight match state tracking and client metrics
- Recipes and compatibility docs
- Release workflow for lint, tests, build, and PyPI publish on tags

### Improved
- README shortened and focused on setup plus quick start
- Config docs now call out Windows-first discovery behavior
- Tests are now split more clearly between unit and integration coverage

## 0.1.4

`rlstatsapi` 0.1.4 adds built-in support for managing Rocket League Stats API configuration from Python.

### Added
- Built-in Rocket League Stats API config management
- Automatic discovery of `TAStatsAPI.ini` in common Windows user locations
- `StatsAPIConfigStatus`
- `find_stats_api_config`
- `get_stats_api_status`
- `set_stats_api_enabled`
- `set_stats_api_port`
- `configure_stats_api`

### Improved
- README and docs now show both automatic and manual setup
- Clear note that Rocket League must be restarted after config changes in either method
- Cleaner packaging metadata and release build output

## 0.1.3

### Added
- MkDocs + Material documentation site
- Auto-generated API reference
- Expanded examples and docs pages

### Improved
- README cleanup and docs linking
- Better typed event documentation

## 0.1.2

### Added
- Event payload typing with `TypedDict`
- `cast_event_data(...)` helper
- Typed examples
- `examples/` directory

### Improved
- Better Pylance-friendly typing flow
- Real client smoke test structure

## 0.1.1

### Changed
- Switched transport handling to plain TCP JSON stream
- Removed unused websocket implementation
- Simplified README and package structure cleanup

## 0.1.0

### Added
- Initial `rlstatsapi` release
- Async `StatsClient`
- Event handlers with `on`, `on_any`, and `events()`
- Logging support
- Rocket League live event ingestion

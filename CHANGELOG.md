# Changelog

All notable changes to this project will be documented in this file.

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

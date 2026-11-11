# Compatibility Notes

## Transport behavior

Since v2.72 the game opens two listeners: a plain TCP socket on `Port`
(default 49123) and a WebSocket on `WebPort` (default 49124). `rlstatsapi` uses
the TCP socket, which needs no extra dependency.

This means:

- the client connects with a normal TCP socket
- commands are written to that same socket
- messages are decoded from a continuous JSON stream
- `Data` can arrive either as a JSON object or as an escaped JSON string

## Platform scope

`rlstatsapi` itself is cross-platform Python code, but config discovery is
currently **Windows-first**.

Automatic config helpers look for `TAStatsAPI.ini` in common user locations such
as:

- `Documents\My Games\Rocket League\TAGame\Config`
- `OneDrive\Documents\My Games\Rocket League\TAGame\Config`
- localized `Documentos` variants

If your setup lives somewhere else, pass an explicit `path=...` to the config
helpers.

## Match data caveats

- `MatchGuid` is typically present only for online or LAN matches.
- Some player fields are spectator-only and may be absent.
- `PacketSendRate` must be greater than `0` to enable exporting.
- `BoostPickup` and `PickupClass` are spectator-only.
- `GoalScored` also fires during replay playback since v2.76.
- `MatchEnded.WinnerTeamNum` is `-1` when the match ends in no contest.

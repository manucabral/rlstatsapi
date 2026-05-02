# Compatibility Notes

## Transport behavior

The original Rocket League documentation describes this feature as a websocket.

In practice, current Rocket League builds can expose the Stats API as a plain
TCP socket that streams consecutive JSON messages. `rlstatsapi` is built around
that observed behavior.

This means:

- the client connects with a normal TCP socket
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

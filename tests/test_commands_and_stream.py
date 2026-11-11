"""Tests for commands, stream framing, new events, and WebPort config."""

# pylint: disable=protected-access

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from rlstatsapi import (
    COMMAND_NAMES,
    KNOWN_EVENTS,
    InvalidCommandError,
    StatsClient,
    build_command,
    commands,
    configure_stats_api,
    encode_command,
    get_stats_api_status,
    set_stats_api_port,
    set_stats_api_web_port,
)
from rlstatsapi import client as client_module
from rlstatsapi import config
from rlstatsapi.models import EventMessage
from rlstatsapi.state import MatchStateTracker


class _ChunkReader:  # pylint: disable=too-few-public-methods
    """Minimal ``StreamReader`` stand-in that returns preset chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)

    async def read(self, _size: int) -> bytes:
        return next(self._chunks, b"")


async def _feed(
    chunks: list[bytes], **options: Any
) -> tuple[StatsClient, list[EventMessage]]:
    client = StatsClient(reconnect=False, **options)
    seen: list[EventMessage] = []
    client.on_any(seen.append)
    with pytest.raises(ConnectionAbortedError):
        await client._read_loop(_ChunkReader(chunks))  # type: ignore[arg-type]
    return client, seen


def _msg(event: str, **data: Any) -> bytes:
    return json.dumps({"Event": event, "Data": data}).encode()


# --- commands


def test_command_builders_produce_documented_wire_format() -> None:
    assert commands.change_pov(focus=1, perspective="PlayerView") == {
        "Command": "ChangePOV",
        "Data": {"Focus": "1", "Perspective": "PlayerView"},
    }
    assert commands.change_pov(focus="Ball")["Data"] == {"Focus": "Ball"}
    assert commands.load_replay(file_name="Stadium_P_2026")["Data"] == {
        "FileName": "Stadium_P_2026"
    }
    assert commands.seek_replay(time_seconds=120.5)["Data"] == {"TimeSeconds": 120.5}
    assert commands.seek_replay(frame=30)["Data"] == {"Frame": 30}
    assert commands.set_game_speed(0.5)["Data"] == {"Speed": 0.5}
    assert commands.set_hud_visibility(False)["Data"] == {"bVisible": False}
    assert commands.set_match_paused(True)["Data"] == {"bPaused": True}
    assert encode_command(commands.set_match_paused(True)) == (
        b'{"Command":"SetMatchPaused","Data":{"bPaused":true}}'
    )
    assert len(COMMAND_NAMES) == 6


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("ChangePOV", {}),
        ("ChangePOV", {"Focus": "PlayerA"}),
        ("ChangePOV", {"Focus": "-1"}),
        ("ChangePOV", {"Perspective": "Director"}),
        ("LoadReplay", {}),
        ("LoadReplay", {"FileName": ""}),
        ("SeekReplay", {}),
        ("SeekReplay", {"Frame": -1}),
        ("SeekReplay", {"Frame": 1.5}),
        ("SeekReplay", {"TimeSeconds": float("nan")}),
        ("SetGameSpeed", {}),
        ("SetGameSpeed", {"Speed": -0.1}),
        ("SetGameSpeed", {"Speed": float("inf")}),
        ("SetGameSpeed", {"Speed": True}),
        ("SetHUDVisibility", {"bVisible": 1}),
        ("SetMatchPaused", {}),
        ("Explode", {}),
    ],
)
def test_invalid_commands_are_rejected_locally(name: str, data: dict[str, Any]) -> None:
    with pytest.raises(InvalidCommandError) as info:
        build_command(name, data)
    assert info.value.command == name
    assert isinstance(info.value, ValueError)


def test_encode_command_requires_command_name() -> None:
    with pytest.raises(InvalidCommandError):
        encode_command({"Data": {}})


@pytest.mark.asyncio
async def test_send_command_writes_json_to_the_socket() -> None:
    received = asyncio.get_running_loop().create_future()

    async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        received.set_result(await reader.read(4096))
        writer.close()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    client = StatsClient(port=port, reconnect=False)
    connected = asyncio.Event()
    client.on_connect(connected.set)
    try:
        with pytest.raises(ConnectionError):
            await client.set_match_paused(True)
        await client.connect()
        await asyncio.wait_for(connected.wait(), timeout=2.0)
        with pytest.raises(InvalidCommandError):
            await client.send_command("SetGameSpeed", {"Speed": -1})
        await client.change_pov(focus=2, perspective="HardAttach")
        payload = await asyncio.wait_for(received, timeout=2.0)
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()

    assert json.loads(payload) == {
        "Command": "ChangePOV",
        "Data": {"Focus": "2", "Perspective": "HardAttach"},
    }


# --- stream framing


@pytest.mark.asyncio
async def test_framing_handles_concatenated_split_and_separated_messages() -> None:
    a = _msg("GoalScored", Scorer={"Name": 'A}{"x', "Shortcut": 1, "TeamNum": 0})
    b = _msg("MatchEnded", WinnerTeamNum=0)
    c = _msg("RoundStarted")
    stream = a + b + b"\r\n" + c + b"  \n" + a
    for size in (1, 2, 3, 7, 50, len(stream)):
        chunks = [stream[i : i + size] for i in range(0, len(stream), size)]
        client, seen = await _feed(chunks)
        assert [m.event for m in seen] == [
            "GoalScored",
            "MatchEnded",
            "RoundStarted",
            "GoalScored",
        ], size
        assert seen[0].data["Scorer"]["Name"] == 'A}{"x'
        assert client.metrics.received_events == 4


@pytest.mark.asyncio
async def test_framing_decodes_string_data_and_keeps_raw() -> None:
    wire = json.dumps({"Event": "MatchEnded", "Data": json.dumps({"WinnerTeamNum": 1})})
    _client, seen = await _feed([wire.encode() * 2], include_raw=True)
    assert [m.data for m in seen] == [{"WinnerTeamNum": 1}] * 2
    assert seen[0].raw == wire


@pytest.mark.asyncio
async def test_framing_skips_garbage_and_invalid_envelopes() -> None:
    good = _msg("RoundStarted")
    stream = (
        b"junk " + good + b'{"Event":5,"Data":{}}' + b"[1,2]" + good + b'{"Data":{}}'
    )
    client, seen = await _feed([stream])
    assert [m.event for m in seen] == ["RoundStarted", "RoundStarted"]
    assert client.metrics.received_events == 2


@pytest.mark.asyncio
async def test_framing_replaces_invalid_utf8_and_keeps_going() -> None:
    bad = b'{"Event":"PlayerJoined","Data":{"PlayerName":"a\xffb"}}'
    _client, seen = await _feed([bad + _msg("RoundStarted")])
    assert seen[0].data["PlayerName"] == "a�b"
    assert seen[1].event == "RoundStarted"


@pytest.mark.asyncio
async def test_framing_matches_stdlib_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "_JSON_LOADS", json.loads)
    name = "Jugadór ñ 日本"
    stream = _msg("PlayerJoined", PlayerName=name) + _msg("PlayerLeft", PlayerName=name)
    stream = (
        json.dumps(
            json.loads(stream[: stream.index(b'}{"') + 1]), ensure_ascii=False
        ).encode()
        + stream
    )
    for size in (1, 5, len(stream)):
        chunks = [stream[i : i + size] for i in range(0, len(stream), size)]
        _client, seen = await _feed(chunks)
        assert [m.data["PlayerName"] for m in seen] == [name] * 3


@pytest.mark.asyncio
async def test_oversized_incomplete_message_raises() -> None:
    client = StatsClient(reconnect=False)
    chunk = b'{"Event":"X","Data":{"k":"' + b"a" * (client_module._MAX_BUFFER_BYTES + 1)
    with pytest.raises(ValueError):
        await client._read_loop(_ChunkReader([chunk]))  # type: ignore[arg-type]


# --- new events, fields and state


def test_new_events_are_known_and_have_typed_helpers() -> None:
    assert {"BoostPickup", "PlayerJoined", "PlayerLeft"} <= KNOWN_EVENTS
    assert len(KNOWN_EVENTS) == 22
    client = StatsClient(reconnect=False)
    for name in ("on_boost_pickup", "on_player_joined", "on_player_left"):
        getattr(client, name)(lambda _m: None)
    assert len(client._handlers_by_event) == 3


def test_state_tracks_playlist_and_no_contest() -> None:
    tracker = MatchStateTracker()
    tracker.update(
        EventMessage("UpdateState", {"MatchGuid": "m1", "Game": {"PlaylistId": 11}})
    )
    assert tracker.snapshot.playlist_id == 11
    assert tracker.snapshot.match_guid == "m1"

    tracker.update(EventMessage("MatchEnded", {"WinnerTeamNum": -1}))
    assert tracker.snapshot.no_contest is True
    assert tracker.snapshot.has_winner is False
    assert tracker.snapshot.winner_team_num == -1

    tracker.update(EventMessage("MatchEnded", {"WinnerTeamNum": 1}))
    assert tracker.snapshot.no_contest is False
    assert tracker.snapshot.has_winner is True


def test_lazy_update_state_keeps_event_order() -> None:
    tracker = MatchStateTracker()
    player = {"Name": "A", "Shortcut": 1, "TeamNum": 0, "Boost": 33, "Speed": 10}
    tracker.ingest(
        EventMessage("UpdateState", {"Players": [player], "Game": {"TimeSeconds": 200}})
    )
    tracker.ingest(EventMessage("ClockUpdatedSeconds", {"TimeSeconds": 199}))
    snapshot = tracker.snapshot
    assert snapshot.time_seconds == 199
    assert snapshot.players[0].boost == 33
    assert snapshot.players[0].speed == 10.0
    assert snapshot.event_counts == {"UpdateState": 1, "ClockUpdatedSeconds": 1}

    tracker.ingest(EventMessage("UpdateState", {"Game": {"TimeSeconds": 150}}))
    tracker.ingest(EventMessage("MatchDestroyed", {}))
    assert tracker.snapshot.time_seconds is None


# --- config


def _ini(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "TAStatsAPI.ini"
    path.write_text("[TAGame.MatchStatsExporter_TA]\n" + body, encoding="utf-8")
    return path


def test_status_reads_web_port_and_float_send_rate(tmp_path: Path) -> None:
    path = _ini(tmp_path, "Port=49123\nWebPort=49124\nPacketSendRate=60.0\n")
    status = get_stats_api_status(path)
    assert (status.port, status.web_port, status.packet_send_rate) == (49123, 49124, 60)
    assert status.enabled is True


def test_web_port_can_be_set_disabled_and_must_differ_from_port(tmp_path: Path) -> None:
    path = _ini(tmp_path, "Port=49123\nPacketSendRate=30\n")
    assert set_stats_api_web_port(50000, path).web_port == 50000
    assert set_stats_api_web_port(0, path).web_port == 0
    with pytest.raises(ValueError):
        set_stats_api_web_port(49123, path)
    with pytest.raises(ValueError):
        set_stats_api_web_port(70000, path)

    status = configure_stats_api(True, port=49123, path=path, web_port=49124)
    assert status.web_port == 49124
    with pytest.raises(ValueError):
        set_stats_api_port(49124, path)
    with pytest.raises(ValueError):
        configure_stats_api(True, port=49124, path=path)
    with pytest.raises(ValueError):
        configure_stats_api(True, port=5000, path=path, web_port=5000)
    assert path.read_text(encoding="utf-8").count("WebPort=") == 1


def test_port_conflicts_with_default_web_port_when_key_is_missing(
    tmp_path: Path,
) -> None:
    path = _ini(tmp_path, "Port=49123\n")
    with pytest.raises(ValueError):
        set_stats_api_port(49124, path)


def test_discovery_prefers_ta_file_over_default_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "Documents" / "My Games" / "Rocket League" / "TAGame" / "Config"
    folder.mkdir(parents=True)
    (folder / "DefaultStatsAPI.ini").write_text("Port=1\n", encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    found = config.find_stats_api_config()
    assert found is not None and found.name == "DefaultStatsAPI.ini"
    (folder / "TAStatsAPI.ini").write_text("Port=2\n", encoding="utf-8")
    found = config.find_stats_api_config()
    assert found is not None and found.name == "TAStatsAPI.ini"

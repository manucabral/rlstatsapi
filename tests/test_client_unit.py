"""Unit tests for client parsing, framing, lifecycle, handlers, and state tracking."""

# pylint: disable=protected-access

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Callable

import pytest

from rlstatsapi.client import ConnectionState, StatsClient, _parse_message_obj
from rlstatsapi.models import EventMessage, PlayerSnapshot


def test_parse_message_decodes_string_data_payload() -> None:
    message = _parse_message_obj(
        {
            "Event": "GoalScored",
            "Data": '{"Scorer":{"Name":"PlayerA","Shortcut":1,"TeamNum":0}}',
        },
        raw="{}",
        include_raw=True,
    )

    assert message is not None
    assert message.event == "GoalScored"
    assert message.data["Scorer"]["Name"] == "PlayerA"
    assert message.raw == "{}"


def test_event_message_as_type_exposes_typed_data_and_preserves_raw() -> None:
    message = EventMessage(
        event="GoalScored",
        data={"Scorer": {"Name": "PlayerA", "Shortcut": 1, "TeamNum": 0}},
        raw='{"Event":"GoalScored"}',
    )

    typed_message = message.as_type("GoalScored")

    assert typed_message.event == "GoalScored"
    assert typed_message.data["Scorer"]["Name"] == "PlayerA"
    assert typed_message.raw == '{"Event":"GoalScored"}'


@pytest.mark.asyncio
async def test_events_filter_only_yields_requested_names() -> None:
    client = StatsClient(reconnect=False)
    await client._queue.put(EventMessage(event="UpdateState", data={}))
    await client._queue.put(EventMessage(event="GoalScored", data={}))

    iterator = client.events("GoalScored")
    message = await asyncio.wait_for(iterator.__anext__(), timeout=1.0)

    assert message.event == "GoalScored"


def test_on_many_registers_same_handler_for_multiple_events() -> None:
    client = StatsClient(reconnect=False)

    def handler(_message: EventMessage) -> None:
        return None

    client.on_many(["GoalScored", "MatchEnded"], handler)

    assert handler in client._handlers_by_event["GoalScored"]
    assert handler in client._handlers_by_event["MatchEnded"]


def test_off_removes_specific_handler() -> None:
    client = StatsClient(reconnect=False)

    def handler(_: EventMessage) -> None:
        return None

    client.on("GoalScored", handler)
    client.off("GoalScored", handler)

    assert handler not in client._handlers_by_event["GoalScored"]


def test_off_any_and_lifecycle_off_remove_handlers() -> None:
    client = StatsClient(reconnect=False)

    def handler(_: EventMessage) -> None:
        return None

    def simple() -> None:
        return None

    def err_handler(
        _msg: EventMessage, _exc: Exception, _fn: Callable[..., Any]
    ) -> None:
        return None

    client.on_any(handler)
    client.off_any(handler)
    client.on_connect(simple)
    client.off_connect(simple)
    client.on_disconnect(simple)
    client.off_disconnect(simple)
    client.on_handler_error(err_handler)
    client.off_handler_error(err_handler)

    assert handler not in client._handlers_any
    assert simple not in client._on_connect_handlers
    assert simple not in client._on_disconnect_handlers
    assert err_handler not in client._error_handlers


@pytest.mark.asyncio
async def test_once_handler_fires_once_and_removes_itself() -> None:
    client = StatsClient(reconnect=False)
    calls: list[str] = []

    def handler(msg: EventMessage) -> None:
        calls.append(msg.event)

    client.once("GoalScored", handler)
    msg = EventMessage(event="GoalScored", data={})
    await client._dispatch(msg)
    await client._dispatch(msg)

    assert len(calls) == 1


def test_clear_queue_empties_all_items() -> None:
    client = StatsClient(reconnect=False)
    client._queue.put_nowait(EventMessage(event="A", data={}))
    client._queue.put_nowait(EventMessage(event="B", data={}))
    client.clear_queue()

    assert client._queue.empty()


@pytest.mark.asyncio
async def test_events_no_filter_yields_all() -> None:
    client = StatsClient(reconnect=False)
    await client._queue.put(EventMessage(event="UpdateState", data={}))
    await client._queue.put(EventMessage(event="GoalScored", data={}))

    iterator = client.events()
    msg1 = await asyncio.wait_for(iterator.__anext__(), timeout=1.0)
    msg2 = await asyncio.wait_for(iterator.__anext__(), timeout=1.0)

    assert {msg1.event, msg2.event} == {"UpdateState", "GoalScored"}


@pytest.mark.asyncio
async def test_overflow_drop_increments_dropped_metric() -> None:
    client = StatsClient(reconnect=False, queue_size=1, overflow="drop")
    await client._enqueue_message(EventMessage(event="A", data={}))
    await client._enqueue_message(EventMessage(event="B", data={}))

    assert client.metrics.queued_events == 1
    assert client.metrics.dropped_events == 1


@pytest.mark.asyncio
async def test_callback_only_mode_does_not_deadlock_when_exceeding_queue_size() -> None:
    client = StatsClient(reconnect=False, queue_size=2, overflow="block")
    received: list[int] = []

    client.on("Tick", lambda msg: received.append(msg.data["i"]))

    reader = asyncio.StreamReader()
    for i in range(10):
        payload = json.dumps({"Event": "Tick", "Data": {"i": i}}) + "\n"
        reader.feed_data(payload.encode("utf-8"))
    reader.feed_eof()

    with pytest.raises(ConnectionAbortedError):
        await asyncio.wait_for(client._read_loop(reader), timeout=1.0)

    assert received == list(range(10))
    assert client._queue.qsize() == 2


@pytest.mark.asyncio
async def test_read_loop_preserves_multibyte_utf8_across_chunks() -> None:
    client = StatsClient(reconnect=False, include_raw=True)
    names: list[str] = []
    client.on(
        "GoalScored",
        lambda msg: names.append(msg.data["Scorer"]["Name"]),
    )

    frame = json.dumps(
        {
            "Event": "GoalScored",
            "Data": {"Scorer": {"Name": "Münü_⚽_火箭", "Shortcut": 0, "TeamNum": 0}},
        },
        ensure_ascii=False,
    ).encode("utf-8")

    # Split right inside the 4-byte emoji / multibyte sequence
    emoji_index = frame.index("⚽".encode("utf-8")) + 1
    part1, part2 = frame[:emoji_index], frame[emoji_index:]

    reader = asyncio.StreamReader()
    reader.feed_data(part1)
    await asyncio.sleep(0)
    reader.feed_data(part2 + b"\n")
    reader.feed_eof()

    with pytest.raises(ConnectionAbortedError):
        await asyncio.wait_for(client._read_loop(reader), timeout=1.0)

    assert names == ["Münü_⚽_火箭"]


@pytest.mark.asyncio
async def test_on_handler_error_called_on_handler_exception() -> None:
    client = StatsClient(reconnect=False)
    errors: list[tuple[EventMessage, Exception, Callable[..., Any]]] = []

    def error_handler(
        msg: EventMessage, exc: Exception, handler: Callable[..., Any]
    ) -> None:
        errors.append((msg, exc, handler))

    client.on_handler_error(error_handler)

    def bad_handler(_: EventMessage) -> None:
        raise RuntimeError("boom")

    client.on("GoalScored", bad_handler)
    msg = EventMessage(event="GoalScored", data={})
    await client._dispatch(msg)

    assert len(errors) == 1
    assert errors[0][0] is msg
    assert isinstance(errors[0][1], RuntimeError)
    assert errors[0][2] is bad_handler


def test_init_parameter_validation() -> None:
    with pytest.raises(ValueError, match="reconnect_delay"):
        StatsClient(reconnect_delay=0)
    with pytest.raises(ValueError, match="port"):
        StatsClient(port=0)
    with pytest.raises(ValueError, match="port"):
        StatsClient(port=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="queue_size"):
        StatsClient(queue_size=0)
    with pytest.raises(ValueError, match="max_reconnect_delay"):
        StatsClient(reconnect_delay=5.0, max_reconnect_delay=1.0)
    with pytest.raises(ValueError, match="overflow"):
        StatsClient(overflow="invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="connect_timeout"):
        StatsClient(connect_timeout=0)
    with pytest.raises(ValueError, match="handler_timeout"):
        StatsClient(handler_timeout=0)


def test_state_tracker_updates_from_update_state() -> None:
    client = StatsClient(reconnect=False)
    client._state_tracker.update(
        EventMessage(
            event="UpdateState",
            data={
                "MatchGuid": "abc",
                "Game": {
                    "TimeSeconds": 120,
                    "bOvertime": False,
                    "Arena": "Stadium_P",
                    "Teams": [
                        {"TeamNum": 0, "Score": 2},
                        {"TeamNum": 1, "Score": 1},
                    ],
                },
            },
        )
    )

    assert client.state.match_guid == "abc"
    assert client.state.blue_score == 2
    assert client.state.orange_score == 1
    assert client.state.time_seconds == 120
    assert client.state.arena == "Stadium_P"


def test_state_tracker_handles_clock_replay_and_destroy_events() -> None:
    client = StatsClient(reconnect=False)
    tracker = client._state_tracker

    tracker.update(
        EventMessage(
            event="ClockUpdatedSeconds",
            data={"MatchGuid": "m1", "TimeSeconds": 45, "bOvertime": True},
        )
    )
    assert client.state.match_guid == "m1"
    assert client.state.time_seconds == 45
    assert client.state.overtime is True

    tracker.update(EventMessage(event="GoalReplayStart", data={}))
    assert client.state.replay_active is True

    tracker.update(EventMessage(event="GoalReplayEnd", data={}))
    assert client.state.replay_active is False

    tracker.update(EventMessage(event="MatchDestroyed", data={}))
    assert client.state.match_guid is None
    assert client.state.last_event == "MatchDestroyed"
    assert client.state.event_counts == {"MatchDestroyed": 1}


def test_connection_state_starts_disconnected() -> None:
    client = StatsClient(reconnect=False)
    assert client.connection_state == ConnectionState.DISCONNECTED
    assert not client.is_connected


@pytest.mark.asyncio
async def test_connection_state_resets_to_disconnected_after_failed_connect() -> None:
    client = StatsClient(
        host="127.0.0.1",
        port=1,
        reconnect=False,
        connect_timeout=0.2,
    )
    await client.connect()
    assert client._reader_task is not None
    await asyncio.wait_for(client._reader_task, timeout=2.0)

    assert client.connection_state == ConnectionState.DISCONNECTED
    assert client.last_error is not None


def test_metrics_reset_clears_counters() -> None:
    client = StatsClient(reconnect=False)
    client._metrics.received_events = 10
    client._metrics.handler_errors = 3
    before = client.metrics.started_at
    client.metrics.reset()
    assert client.metrics.received_events == 0
    assert client.metrics.handler_errors == 0
    assert client.metrics.started_at >= before


def test_metrics_started_at_is_set() -> None:
    client = StatsClient(reconnect=False)
    assert isinstance(client.metrics.started_at, datetime)


@pytest.mark.asyncio
async def test_wait_for_resolves_on_matching_event() -> None:
    client = StatsClient(reconnect=False)
    msg = EventMessage(event="GoalScored", data={"GoalSpeed": 99.0})

    async def dispatch_later() -> None:
        await asyncio.sleep(0)
        await client._dispatch(msg)

    asyncio.create_task(dispatch_later())
    result = await asyncio.wait_for(client.wait_for("GoalScored"), timeout=1.0)
    assert result is msg


@pytest.mark.asyncio
async def test_wait_for_raises_timeout_when_event_never_arrives() -> None:
    client = StatsClient(reconnect=False)
    with pytest.raises(asyncio.TimeoutError):
        await client.wait_for("GoalScored", timeout=0.05)


@pytest.mark.asyncio
async def test_wait_for_cleans_up_handler_on_timeout_and_cancellation() -> None:
    client = StatsClient(reconnect=False)
    with pytest.raises(asyncio.TimeoutError):
        await client.wait_for("GoalScored", timeout=0.05)
    assert len(client._handlers_by_event["GoalScored"]) == 0

    task = asyncio.create_task(client.wait_for("GoalScored"))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(client._handlers_by_event["GoalScored"]) == 0


@pytest.mark.asyncio
async def test_handler_timeout_cancels_slow_async_handler_and_decorator() -> None:
    client = StatsClient(reconnect=False, handler_timeout=0.03)
    finished = False

    @client.on("GoalScored")
    async def slow_handler(_: EventMessage) -> None:
        nonlocal finished
        await asyncio.sleep(10)
        finished = True

    await client._dispatch(EventMessage(event="GoalScored", data={}))
    assert not finished
    assert client.metrics.handler_errors == 1
    client.off("GoalScored", slow_handler)
    assert len(client._handlers_by_event["GoalScored"]) == 0


def test_state_tracker_populates_players() -> None:
    client = StatsClient(reconnect=False)
    client._state_tracker.update(
        EventMessage(
            event="UpdateState",
            data={
                "Players": [
                    {
                        "Name": "Alice",
                        "Shortcut": 1,
                        "TeamNum": 0,
                        "Score": 5,
                        "Boost": 80,
                    },
                    {
                        "Name": "Bob",
                        "Shortcut": 2,
                        "TeamNum": 1,
                        "Score": 3,
                        "Boost": 20,
                    },
                ],
                "Game": {},
            },
        )
    )

    players = client.state.players
    assert len(players) == 2
    alice = next(p for p in players if p.name == "Alice")
    assert isinstance(alice, PlayerSnapshot)
    assert alice.team_num == 0
    assert alice.score == 5
    assert alice.boost == 80


def test_state_tracker_resolves_target_player() -> None:
    client = StatsClient(reconnect=False)
    client._state_tracker.update(
        EventMessage(
            event="UpdateState",
            data={
                "Players": [
                    {"Name": "Alice", "Shortcut": 1, "TeamNum": 0},
                    {"Name": "Bob", "Shortcut": 2, "TeamNum": 1},
                ],
                "Game": {
                    "bHasTarget": True,
                    "Target": {"Name": "Bob", "Shortcut": 2, "TeamNum": 1},
                },
            },
        )
    )

    assert client.state.target_player is not None
    assert client.state.target_player.name == "Bob"
    assert client.state.target_player.shortcut == 2


def test_state_tracker_no_target_when_flag_false() -> None:
    client = StatsClient(reconnect=False)
    client._state_tracker.update(
        EventMessage(
            event="UpdateState",
            data={
                "Players": [{"Name": "Alice", "Shortcut": 1, "TeamNum": 0}],
                "Game": {"bHasTarget": False},
            },
        )
    )

    assert client.state.target_player is None

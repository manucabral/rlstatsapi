"""Unit coverage for client parsing, filtering, and convenience helpers."""

# pylint: disable=protected-access

from __future__ import annotations

import asyncio
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


def test_event_message_as_type_exposes_typed_data() -> None:
    message = EventMessage(
        event="GoalScored",
        data={"Scorer": {"Name": "PlayerA", "Shortcut": 1, "TeamNum": 0}},
    )

    typed_message = message.as_type("GoalScored")

    assert typed_message.event == "GoalScored"
    assert typed_message.data["Scorer"]["Name"] == "PlayerA"


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


def test_off_any_removes_global_handler() -> None:
    client = StatsClient(reconnect=False)

    def handler(_: EventMessage) -> None:
        return None

    client.on_any(handler)
    client.off_any(handler)

    assert handler not in client._handlers_any


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
    client._queue.put_nowait(EventMessage(event="A", data={}))

    try:
        client._queue.put_nowait(EventMessage(event="B", data={}))
        client._metrics.queued_events += 1
    except asyncio.QueueFull:
        client._metrics.dropped_events += 1

    assert client._metrics.dropped_events == 1


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


def test_reconnect_delay_zero_raises() -> None:
    with pytest.raises(ValueError, match="reconnect_delay"):
        StatsClient(reconnect_delay=0)


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


def test_connection_state_starts_disconnected() -> None:
    client = StatsClient(reconnect=False)
    assert client.connection_state == ConnectionState.DISCONNECTED
    assert not client.is_connected


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
async def test_wait_for_cleans_up_handler_on_timeout() -> None:
    client = StatsClient(reconnect=False)
    with pytest.raises(asyncio.TimeoutError):
        await client.wait_for("GoalScored", timeout=0.05)
    assert len(client._handlers_by_event["GoalScored"]) == 0


@pytest.mark.asyncio
async def test_handler_timeout_cancels_slow_async_handler() -> None:
    client = StatsClient(reconnect=False, handler_timeout=0.05)
    finished = False

    async def slow_handler(_: EventMessage) -> None:
        nonlocal finished
        await asyncio.sleep(10)
        finished = True

    client.on("GoalScored", slow_handler)
    await client._dispatch(EventMessage(event="GoalScored", data={}))
    assert not finished
    assert client.metrics.handler_errors == 1


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

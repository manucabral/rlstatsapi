"""Real integration test for StatsClient against a live Rocket League exporter."""

from __future__ import annotations

import asyncio
import os
import socket

import pytest

from rlstatsapi import StatsClient

RL_STATSAPI_HOST = os.getenv("RL_STATSAPI_HOST", "127.0.0.1")
RL_STATSAPI_PORT = int(os.getenv("RL_STATSAPI_PORT", "49123"))


def _tcp_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_client_receives_real_event() -> None:
    """Connects to a real RL exporter and verifies one event is received."""

    if not _tcp_open(RL_STATSAPI_HOST, RL_STATSAPI_PORT):
        pytest.skip(
            f"Rocket League exporter is not reachable at {RL_STATSAPI_HOST}:{RL_STATSAPI_PORT}"
        )

    client = StatsClient(
        host=RL_STATSAPI_HOST,
        port=RL_STATSAPI_PORT,
        reconnect=False,
        connect_timeout=2.0,
    )

    await client.connect()
    try:
        message = await asyncio.wait_for(client.events().__anext__(), timeout=3.0)
        assert isinstance(message.event, str)
        assert isinstance(message.data, dict)
        assert message.event
    finally:
        await client.disconnect()

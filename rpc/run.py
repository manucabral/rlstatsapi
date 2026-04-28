"""Run Discord Rich Presence bridge for Rocket League Stats API."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import time

from rlstatsapi import StatsClient

from .discord_ipc import ActivityType, ClientRPC
from .presence_mapper import MatchCache, PresenceState, apply_event, build_presence

LOGGER = logging.getLogger("rlstatsapi.rpc.runner")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rocket League -> Discord Rich Presence bridge")
    parser.add_argument("--discord-client-id", default=os.getenv("DISCORD_CLIENT_ID", ""))
    parser.add_argument("--host", default=os.getenv("RL_STATS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("RL_STATS_PORT", "49123")))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--rpc-debug", action="store_true")
    parser.add_argument("--throttle-seconds", type=float, default=1.0)
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    if not args.discord_client_id:
        raise SystemExit("Missing Discord client id. Use --discord-client-id or DISCORD_CLIENT_ID")

    client = StatsClient(host=args.host, port=args.port, log_enabled=args.debug)
    rpc = ClientRPC(client_id=args.discord_client_id, debug=args.rpc_debug)

    cache = MatchCache()
    last_emit_at = 0.0
    last_signature: tuple[str, str, int | None, int | None, str | None, str | None, str | None, str | None] | None = None

    stop_event = asyncio.Event()

    def _stop() -> None:
        LOGGER.info("Stop requested")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    LOGGER.info("Connecting Discord RPC...")
    try:
        rpc.connect()
    except Exception as exc:
        LOGGER.error("Discord RPC connect failed: %s", exc)

    LOGGER.info("Connecting RL stats socket at ws://%s:%s", args.host, args.port)
    await client.connect()

    try:
        while not stop_event.is_set():
            try:
                message = await asyncio.wait_for(client._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            apply_event(cache, message)
            now = time.time()

            force_emit = message.event in {
                "GoalScored",
                "MatchEnded",
                "MatchDestroyed",
                "MatchPaused",
                "MatchUnpaused",
                "CountdownBegin",
                "RoundStarted",
                "GoalReplayStart",
                "GoalReplayEnd",
            }

            if not force_emit and message.event == "UpdateState" and (now - last_emit_at) < args.throttle_seconds:
                continue

            presence = build_presence(cache)
            signature = _signature(presence)
            if signature == last_signature:
                continue

            _send_presence(rpc, presence)
            last_signature = signature
            last_emit_at = now

    finally:
        LOGGER.info("Shutting down...")
        await client.disconnect()
        try:
            rpc.clear_activity()
        except Exception:
            pass
        rpc.close()


def _send_presence(rpc: ClientRPC, presence: PresenceState) -> None:
    try:
        rpc.update(
            state=presence.state,
            details=presence.details,
            activity_type=ActivityType.PLAYING,
            start_time=presence.start_time,
            end_time=presence.end_time,
            large_image=presence.large_image,
            large_text=presence.large_text,
            small_image=presence.small_image,
            small_text=presence.small_text,
            buttons=None,
        )
    except Exception as exc:
        LOGGER.warning("Presence update failed: %s", exc)


def _signature(p: PresenceState) -> tuple[str, str, int | None, int | None, str | None, str | None, str | None, str | None]:
    return (p.details, p.state, p.start_time, p.end_time, p.large_image, p.large_text, p.small_image, p.small_text)


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if (args.debug or args.rpc_debug) else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

"""Command-line entrypoint for common rlstatsapi setup and debugging tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .client import StatsClient
from .config import (
    DEFAULT_PACKET_SEND_RATE,
    DEFAULT_STATS_API_PORT,
    configure_stats_api,
    get_stats_api_status,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI args and dispatch the requested command."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rlstatsapi")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status",
        help="Show the current TAStatsAPI.ini status.",
    )
    status_parser.add_argument(
        "--path", type=Path, help="Explicit TAStatsAPI.ini path."
    )
    status_parser.set_defaults(func=_run_status)

    enable_parser = subparsers.add_parser(
        "enable",
        help="Enable the Rocket League Stats API in TAStatsAPI.ini.",
    )
    enable_parser.add_argument(
        "--path", type=Path, help="Explicit TAStatsAPI.ini path."
    )
    enable_parser.add_argument("--port", type=int, default=DEFAULT_STATS_API_PORT)
    enable_parser.add_argument(
        "--rate",
        type=int,
        default=DEFAULT_PACKET_SEND_RATE,
        help="PacketSendRate to write when enabling the exporter.",
    )
    enable_parser.set_defaults(func=_run_enable)

    disable_parser = subparsers.add_parser(
        "disable",
        help="Disable the Rocket League Stats API in TAStatsAPI.ini.",
    )
    disable_parser.add_argument(
        "--path", type=Path, help="Explicit TAStatsAPI.ini path."
    )
    disable_parser.add_argument("--port", type=int, default=DEFAULT_STATS_API_PORT)
    disable_parser.set_defaults(func=_run_disable)

    listen_parser = subparsers.add_parser(
        "listen",
        help="Connect to the local exporter and print live events.",
    )
    listen_parser.add_argument("--host", default="127.0.0.1")
    listen_parser.add_argument("--port", type=int, default=DEFAULT_STATS_API_PORT)
    listen_parser.add_argument(
        "--event",
        action="append",
        default=[],
        help="Filter to one or more event names. Repeat the flag to add more.",
    )
    listen_parser.add_argument(
        "--raw",
        action="store_true",
        help="Include the raw transport JSON when available.",
    )
    listen_parser.set_defaults(func=_run_listen)

    return parser


def _run_status(args: argparse.Namespace) -> int:
    status = get_stats_api_status(args.path)
    print(json.dumps(asdict(status), indent=2))
    return 0


def _run_enable(args: argparse.Namespace) -> int:
    status = configure_stats_api(
        enabled=True,
        port=args.port,
        packet_send_rate=args.rate,
        path=args.path,
    )
    print(json.dumps(asdict(status), indent=2))
    print("Restart Rocket League after changing the config file.")
    return 0


def _run_disable(args: argparse.Namespace) -> int:
    status = configure_stats_api(
        enabled=False,
        port=args.port,
        packet_send_rate=DEFAULT_PACKET_SEND_RATE,
        path=args.path,
    )
    print(json.dumps(asdict(status), indent=2))
    print("Restart Rocket League after changing the config file.")
    return 0


def _run_listen(args: argparse.Namespace) -> int:
    return asyncio.run(_listen(args))


async def _listen(args: argparse.Namespace) -> int:
    async with StatsClient(
        host=args.host,
        port=args.port,
        include_raw=args.raw,
    ) as client:
        print("Listening for Rocket League events. Press Ctrl+C to stop.")
        async for message in client.events(*args.event):
            payload = {
                "event": message.event,
                "data": message.data,
            }
            if args.raw:
                payload["raw"] = message.raw
            print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

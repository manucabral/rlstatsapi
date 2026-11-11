"""Command-line interface for ``rlstatsapi`` configuration and live listening."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .client import StatsClient
from .commands import COMMAND_NAMES, InvalidCommandError, build_command
from .config import (
    DEFAULT_PACKET_SEND_RATE,
    DEFAULT_STATS_API_PORT,
    configure_stats_api,
    get_stats_api_status,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the selected subcommand.

    Args:
        argv: Optional list of CLI arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        int: Process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser and register subcommands."""
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
    enable_parser.add_argument(
        "--web-port",
        type=int,
        default=None,
        help="WebSocket port to write (0 disables it). Left untouched by default.",
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

    send_parser = subparsers.add_parser(
        "send",
        help="Send one command to the game and exit.",
    )
    send_parser.add_argument("name", choices=COMMAND_NAMES)
    send_parser.add_argument(
        "data",
        nargs="?",
        default="{}",
        help="Command variables as JSON, for example '{\"bVisible\": false}'.",
    )
    send_parser.add_argument("--host", default="127.0.0.1")
    send_parser.add_argument("--port", type=int, default=DEFAULT_STATS_API_PORT)
    send_parser.set_defaults(func=_run_send)

    return parser


def _run_status(args: argparse.Namespace) -> int:
    """Print the current ``TAStatsAPI.ini`` status as formatted JSON."""
    status = get_stats_api_status(args.path)
    print(json.dumps(asdict(status), indent=2))
    return 0


def _run_enable(args: argparse.Namespace) -> int:
    """Enable the Stats API exporter in ``TAStatsAPI.ini`` and print the result."""
    status = configure_stats_api(
        enabled=True,
        port=args.port,
        packet_send_rate=args.rate,
        path=args.path,
        web_port=args.web_port,
    )
    print(json.dumps(asdict(status), indent=2))
    print("Restart Rocket League after changing the config file.")
    return 0


def _run_disable(args: argparse.Namespace) -> int:
    """Disable the Stats API exporter in ``TAStatsAPI.ini`` and print the result."""
    status = configure_stats_api(
        enabled=False,
        port=args.port,
        packet_send_rate=DEFAULT_PACKET_SEND_RATE,
        path=args.path,
    )
    print(json.dumps(asdict(status), indent=2))
    print("Restart Rocket League after changing the config file.")
    return 0


def _run_send(args: argparse.Namespace) -> int:
    """Validate one command, send it to the game, and print what was sent."""
    try:
        command = build_command(args.name, json.loads(args.data))
    except (InvalidCommandError, json.JSONDecodeError) as exc:
        print(f"Invalid command: {exc}")
        return 2
    return asyncio.run(_send(args, command))


async def _send(args: argparse.Namespace, command: dict[str, object]) -> int:
    """Open a short-lived connection and write ``command`` to the socket."""
    client = StatsClient(host=args.host, port=args.port, reconnect=False)
    connected = asyncio.Event()
    client.on_connect(connected.set)
    await client.connect()
    try:
        await asyncio.wait_for(connected.wait(), timeout=client.connect_timeout + 1)
    except asyncio.TimeoutError:
        await client.disconnect()
        print(f"Could not connect to {args.host}:{args.port}: {client.last_error}")
        return 1
    await client.send_command(command)
    await client.disconnect()
    print(json.dumps(command))
    return 0


def _run_listen(args: argparse.Namespace) -> int:
    """Run the async ``_listen`` coroutine from the synchronous CLI handler."""
    return asyncio.run(_listen(args))


async def _listen(args: argparse.Namespace) -> int:
    """Connect to the local Stats API and print incoming events until interrupted."""
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

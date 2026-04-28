import argparse
import asyncio
import json
import logging
import time
from typing import Any

from rlstatsapi import StatsClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rocket League Stats API event logger")
    parser.add_argument("--host", default="127.0.0.1", help="Stats API host")
    parser.add_argument("--port", type=int, default=49123, help="Stats API port")
    parser.add_argument(
        "--throttle-update-state",
        type=float,
        default=1.0,
        help="Minimum seconds between UpdateState logs",
    )
    parser.add_argument(
        "--event",
        action="append",
        default=[],
        help="Only log these event names (repeatable)",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Print full JSON payload for each logged event",
    )
    parser.add_argument(
        "--no-client-logs",
        action="store_true",
        help="Disable StatsClient internal logs",
    )
    return parser.parse_args()


def summarize_event(event: str, data: dict[str, Any]) -> str:
    if event == "UpdateState":
        game = data.get("Game") or {}
        teams = game.get("Teams") or []

        blue = 0
        orange = 0
        for team in teams:
            team_num = team.get("TeamNum")
            score = team.get("Score", 0)
            if team_num == 0:
                blue = score
            elif team_num == 1:
                orange = score

        clock = int(game.get("TimeSeconds", 0))
        mins, secs = divmod(max(0, clock), 60)
        overtime = " OT" if game.get("bOvertime") else ""
        replay = " Replay" if game.get("bReplay") else ""
        arena = game.get("Arena", "UnknownArena")
        return f"{arena} | Blue {blue}-{orange} Orange | {mins:02d}:{secs:02d}{overtime}{replay}"

    if event == "GoalScored":
        scorer = (data.get("Scorer") or {}).get("Name", "Unknown")
        speed = data.get("GoalSpeed", "?")
        return f"Goal by {scorer} (speed={speed})"

    if event == "ClockUpdatedSeconds":
        secs = int(data.get("TimeSeconds", 0))
        mins, rem = divmod(max(0, secs), 60)
        ot = " OT" if data.get("bOvertime") else ""
        return f"Clock {mins:02d}:{rem:02d}{ot}"

    return ""


async def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    selected_events = set(args.event)
    last_update_state_log = 0.0

    client = StatsClient(
        host=args.host,
        port=args.port,
        log_enabled=not args.no_client_logs,
    )

    def log_event(msg) -> None:
        nonlocal last_update_state_log

        if selected_events and msg.event not in selected_events:
            return

        if msg.event == "UpdateState":
            now = time.time()
            if now - last_update_state_log < args.throttle_update_state:
                return
            last_update_state_log = now

        summary = summarize_event(msg.event, msg.data)
        if summary:
            logging.info("EVENT: %s | %s", msg.event, summary)
        else:
            logging.info("EVENT: %s", msg.event)

        if args.raw_json:
            logging.info("DATA: %s", json.dumps(msg.data, ensure_ascii=False))

    client.on_any(log_event)

    await client.connect()
    logging.info("Listening for Rocket League events on %s:%s", args.host, args.port)
    logging.info("Press Ctrl+C to stop")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")

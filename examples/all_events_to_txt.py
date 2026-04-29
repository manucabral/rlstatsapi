import asyncio
import json
import logging
from datetime import datetime

from rlstatsapi import StatsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("rlstatsapi").setLevel(logging.DEBUG)

OUTPUT_FILE = "events_log.txt"


async def main() -> None:
    client = StatsClient(overflow="drop")
    last_payload_by_event: dict[str, str] = {}

    client.on_connect(lambda: logging.info("Connected and writing to %s", OUTPUT_FILE))
    client.on_disconnect(lambda: logging.info("Disconnected"))

    def on_error(event_name: str, exc: Exception) -> None:
        logging.error("Handler error for %s: %s", event_name, exc)

    client.on_handler_error(on_error)

    def log_event(msg) -> None:
        payload_pretty = json.dumps(
            msg.data, ensure_ascii=False, indent=2, sort_keys=True
        )

        if last_payload_by_event.get(msg.event) == payload_pretty:
            return

        last_payload_by_event[msg.event] = payload_pretty

        timestamp = datetime.now().isoformat(timespec="seconds")
        block = (
            f"[{timestamp}] EVENT: {msg.event}\n"
            f"DATA:\n{payload_pretty}\n"
            f"{'-' * 80}\n"
        )

        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(block)

        logging.info("EVENT: %s (changed)", msg.event)

    client.on_any(log_event)

    async with client:
        logging.info("Listening to all Rocket League events. Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")

import asyncio
import json
import logging
from datetime import datetime

from rlstatsapi import StatsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

OUTPUT_FILE = "events_log2.txt"


async def main() -> None:
    logging.getLogger("rlstatsapi").setLevel(logging.DEBUG)
    client = StatsClient()
    last_payload_by_event: dict[str, str] = {}

    def log_event(msg) -> None:
        payload_pretty = json.dumps(
            msg.data, ensure_ascii=False, indent=2, sort_keys=True
        )

        previous = last_payload_by_event.get(msg.event)
        if previous == payload_pretty:
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

        logging.info("EVENT: %s (changed -> written to %s)", msg.event, OUTPUT_FILE)

    client.on_any(log_event)

    await client.connect()
    logging.info("Listening to all Rocket League events. Press Ctrl+C to stop.")
    logging.info("Writing changed payloads to %s", OUTPUT_FILE)

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")

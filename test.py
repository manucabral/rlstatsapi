import asyncio
import json
import logging

from rlstatsapi import StatsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    client = StatsClient(log_enabled=True)

    def log_event(msg) -> None:
        logging.info("EVENT: %s", msg.event)
        logging.info("DATA: %s", json.dumps(msg.data, ensure_ascii=False))

    client.on_any(log_event)

    await client.connect()
    logging.info("Listening to all Rocket League events. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")

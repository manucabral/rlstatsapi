import asyncio
import logging
from rlstatsapi import StatsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def on_goal(msg):
    scorer = msg.data.get("Scorer", {})
    logging.info("GOAL: %s", scorer.get("Name", "Unknown"))


async def main() -> None:
    client = StatsClient(log_enabled=True, reconnect=True, reconnect_delay=1.0)

    client.on_any(lambda msg: logging.info("EVENT: %s", msg.event))
    client.on("GoalScored", on_goal)

    await client.connect()
    logging.info("Listening for Rocket League events... Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")

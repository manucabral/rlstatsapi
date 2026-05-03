import asyncio
import logging

from rlstatsapi import StatsClient
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("rlstatsapi").setLevel(logging.DEBUG)


async def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    assister = data.get("Assister", {})
    speed = data.get("GoalSpeed", 0.0)

    name = scorer.get("Name", "Unknown")
    assist_name = assister.get("Name") if assister else None

    line = f"Goal by {name} ({speed:.0f} km/h)"
    if assist_name:
        line += f" assist: {assist_name}"
    print(line)


async def main() -> None:
    client = StatsClient()
    client.on_connect(lambda: print("Connected to Rocket League Stats API"))
    client.on_disconnect(lambda: print("Disconnected"))
    client.on("GoalScored", on_goal)

    async with client:
        print("Listening for GoalScored events... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

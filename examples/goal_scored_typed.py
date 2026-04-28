import asyncio

from rlstatsapi import StatsClient
from rlstatsapi.models import EventMessage
from rlstatsapi.types import GoalScoredPayload, cast_event_data


async def on_goal(msg: EventMessage) -> None:
    data: GoalScoredPayload = cast_event_data("GoalScored", msg.data)
    scorer = data.get("Scorer", {})
    name = scorer.get("Name", "Unknown")
    print(f"Goal by: {name}")


async def main() -> None:
    client = StatsClient()
    client.on("GoalScored", on_goal)

    await client.connect()
    print("Listening for GoalScored events... Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

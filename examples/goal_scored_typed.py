import asyncio

from rlstatsapi import StatsClient, TypedEventMessage, GoalScoredPayload


async def on_goal(msg: TypedEventMessage[GoalScoredPayload]) -> None:
    scorer = msg.data.get("Scorer", {})
    assister = msg.data.get("Assister", {})
    speed = msg.data.get("GoalSpeed", 0.0)

    name = scorer.get("Name", "Unknown")
    assist_name = assister.get("Name") if assister else None

    line = f"GOAL by {name} ({speed:.0f} km/h)"
    if assist_name:
        line += f"assist: {assist_name}"
    print(line)


async def main() -> None:
    client = StatsClient()
    client.on_goal_scored(on_goal)

    async with client:
        print("Listening for GoalScored events... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

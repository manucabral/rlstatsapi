"""Register event handlers using the decorator form of client.on()."""

import asyncio

from rlstatsapi import (
    StatsClient,
    TypedEventMessage,
    GoalScoredPayload,
    StatfeedEventPayload,
)

client = StatsClient()


@client.on("GoalScored")
def on_goal(msg: TypedEventMessage[GoalScoredPayload]) -> None:
    scorer = msg.data.get("Scorer", {})
    speed = msg.data.get("GoalSpeed", 0.0)
    name = scorer.get("Name", "Unknown") if isinstance(scorer, dict) else "Unknown"
    print(f"GOAL by {name} at {speed:.0f} km/h")


@client.on("StatfeedEvent")
def on_statfeed(msg: TypedEventMessage[StatfeedEventPayload]) -> None:
    event_type = msg.data.get("Type", "")
    target = msg.data.get("MainTarget", {})
    actor = target.get("Name", "?") if isinstance(target, dict) else "?"
    print(f"  {event_type}: {actor}")


@client.on("MatchEnded")
def on_match_ended(_msg: TypedEventMessage) -> None:
    print("Match ended - resetting.")


async def main() -> None:
    async with client:
        print("Listening with decorator handlers... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

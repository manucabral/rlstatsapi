"""Print StatfeedEvent highlights (saves, shots, demos, etc.) as they happen."""

import asyncio

from rlstatsapi import StatsClient, TypedEventMessage, StatfeedEventPayload

ICONS: dict[str, str] = {
    "Goal": "⚽",
    "OwnGoal": "😬",
    "Save": "🧤",
    "EpicSave": "🧤✨",
    "Shot": "🎯",
    "Assist": "🤝",
    "Demolish": "💥",
    "AerialGoal": "🚀",
    "BicycleGoal": "🚲",
}


async def main() -> None:
    client = StatsClient()

    def on_statfeed(msg: TypedEventMessage[StatfeedEventPayload]) -> None:
        event_type = msg.data.get("Type", "")
        main_target = msg.data.get("MainTarget", {})
        secondary_target = msg.data.get("SecondaryTarget", {})

        actor = main_target.get("Name", "?") if isinstance(main_target, dict) else "?"
        victim = secondary_target.get("Name") if isinstance(secondary_target, dict) else None

        icon = ICONS.get(event_type, "•")
        line = f"{icon}  {event_type}: {actor}"
        if victim:
            line += f" → {victim}"
        print(line)

    client.on_statfeed_event(on_statfeed)

    async with client:
        print("Listening for StatfeedEvent highlights... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

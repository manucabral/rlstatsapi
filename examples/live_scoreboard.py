"""Print a live scoreboard using the built-in state snapshot (UpdateState)."""

import asyncio

from rlstatsapi import StatsClient, TypedEventMessage, UpdateStatePayload


async def main() -> None:
    client = StatsClient()

    def on_update(_msg: TypedEventMessage[UpdateStatePayload]) -> None:
        """
        Use client.state for current snapshot; msg.data holds same info for this event.
        """
        s = client.state
        blue = s.blue_score if s.blue_score is not None else "-"
        orange = s.orange_score if s.orange_score is not None else "-"
        mins, secs = divmod(s.time_seconds or 0, 60)
        overtime = " OT" if s.overtime else ""
        replay = " [REPLAY]" if s.replay_active else ""
        print(
            f"Blue {blue} - {orange} Orange  |  {mins:02d}:{secs:02d}{overtime}{replay}"
        )

    client.on_update_state(on_update)

    async with client:
        print("Live scoreboard active... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

import asyncio

from rlstatsapi import StatsClient, TypedEventMessage, ClockUpdatedSecondsPayload


async def main() -> None:
    client = StatsClient()

    def on_clock(msg: TypedEventMessage[ClockUpdatedSecondsPayload]) -> None:
        secs = int(msg.data.get("TimeSeconds", 0))
        mins, rem = divmod(max(0, secs), 60)
        overtime = " OT" if msg.data.get("bOvertime") else ""
        print(f"Clock: {mins:02d}:{rem:02d}{overtime}")

    client.on_clock_updated_seconds(on_clock)

    async with client:
        print("Listening to clock updates... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

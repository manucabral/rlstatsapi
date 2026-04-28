import asyncio

from rlstatsapi import StatsClient
from rlstatsapi.types import cast_event_data


async def main() -> None:
    client = StatsClient()

    def on_clock(msg) -> None:
        data = cast_event_data("ClockUpdatedSeconds", msg.data)
        secs = int(data.get("TimeSeconds", 0))
        mins, rem = divmod(max(0, secs), 60)
        print(f"Clock: {mins:02d}:{rem:02d}")

    client.on("ClockUpdatedSeconds", on_clock)
    await client.connect()
    print("Listening to clock updates... Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

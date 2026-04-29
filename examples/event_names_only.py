import asyncio

from rlstatsapi import StatsClient


async def main() -> None:
    client = StatsClient()

    client.on_connect(lambda: print("Connected to Rocket League Stats API"))
    client.on_disconnect(lambda: print("Disconnected"))

    client.on_any(lambda msg: print(msg.event))

    async with client:
        print("Listening to event names... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

import asyncio

from rlstatsapi import StatsClient


async def main() -> None:
    client = StatsClient()

    def on_any(msg) -> None:
        print(msg.event)

    client.on_any(on_any)
    await client.connect()
    print("Listening to event names... Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

"""Enable the exporter, then connect with the matching port."""

from __future__ import annotations

import asyncio

from rlstatsapi import StatsClient, configure_stats_api, get_stats_api_status


async def main() -> None:
    """Show current config, enable the exporter, and start listening."""
    status = get_stats_api_status()
    print("Before:", status)

    updated = configure_stats_api(enabled=True, port=49123, packet_send_rate=30)
    print("After:", updated)
    print("Restart Rocket League before expecting live events.")

    async with StatsClient(port=49123) as client:
        client.on_any(lambda msg: print(msg.event, msg.data))
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

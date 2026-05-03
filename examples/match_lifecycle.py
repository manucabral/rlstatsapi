"""Track the full match lifecycle from creation to destruction."""

import asyncio

from rlstatsapi import (
    StatsClient,
    TypedEventMessage,
    MatchCreatedPayload,
    MatchInitializedPayload,
    MatchEndedPayload,
    MatchDestroyedPayload,
    MatchPausedPayload,
    MatchUnpausedPayload,
    PodiumStartPayload,
    RoundStartedPayload,
)


async def main() -> None:
    client = StatsClient()

    def on_created(msg: TypedEventMessage[MatchCreatedPayload]) -> None:
        print(f"[MatchCreated]      guid={msg.data.get('MatchGuid')}")

    def on_initialized(msg: TypedEventMessage[MatchInitializedPayload]) -> None:
        print(f"[MatchInitialized]  guid={msg.data.get('MatchGuid')}")

    def on_round_started(msg: TypedEventMessage[RoundStartedPayload]) -> None:
        print(f"[RoundStarted]      guid={msg.data.get('MatchGuid')}")

    def on_paused(msg: TypedEventMessage[MatchPausedPayload]) -> None:
        print(f"[MatchPaused]       guid={msg.data.get('MatchGuid')}")

    def on_unpaused(msg: TypedEventMessage[MatchUnpausedPayload]) -> None:
        print(f"[MatchUnpaused]     guid={msg.data.get('MatchGuid')}")

    def on_ended(msg: TypedEventMessage[MatchEndedPayload]) -> None:
        winner = msg.data.get("WinnerTeamNum")
        team = "Blue" if winner == 0 else "Orange" if winner == 1 else "Unknown"
        print(f"[MatchEnded]        winner={team}")

    def on_podium(msg: TypedEventMessage[PodiumStartPayload]) -> None:
        print(f"[PodiumStart]       guid={msg.data.get('MatchGuid')}")

    def on_destroyed(msg: TypedEventMessage[MatchDestroyedPayload]) -> None:
        print(f"[MatchDestroyed]    guid={msg.data.get('MatchGuid')}")

    client.on_match_created(on_created)
    client.on_match_initialized(on_initialized)
    client.on_round_started(on_round_started)
    client.on_match_paused(on_paused)
    client.on_match_unpaused(on_unpaused)
    client.on_match_ended(on_ended)
    client.on_podium_start(on_podium)
    client.on_match_destroyed(on_destroyed)

    async with client:
        print("Tracking match lifecycle... Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")

"""Documented Rocket League Stats API event names."""

from __future__ import annotations

KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "UpdateState",
        "BallHit",
        "BoostPickup",
        "ClockUpdatedSeconds",
        "CountdownBegin",
        "CrossbarHit",
        "GoalReplayEnd",
        "GoalReplayStart",
        "GoalReplayWillEnd",
        "GoalScored",
        "MatchCreated",
        "MatchInitialized",
        "MatchDestroyed",
        "MatchEnded",
        "MatchPaused",
        "MatchUnpaused",
        "PlayerJoined",
        "PlayerLeft",
        "PodiumStart",
        "ReplayCreated",
        "RoundStarted",
        "StatfeedEvent",
    }
)

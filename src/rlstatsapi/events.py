"""Documented Rocket League Stats API event names."""

from __future__ import annotations

KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "UpdateState",
        "BallHit",
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
        "PodiumStart",
        "ReplayCreated",
        "RoundStarted",
        "StatfeedEvent",
    }
)

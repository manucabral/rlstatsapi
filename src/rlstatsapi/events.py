"""
Known Rocket League Stats API event names.
Sources:
    https://www.rocketleague.com/en/developer/stats-api
"""

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

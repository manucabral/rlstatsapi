"""Map Rocket League events/state into Discord Rich Presence payload fields."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from rlstatsapi.models import EventMessage


@dataclass(slots=True)
class PresenceState:
    details: str
    state: str
    start_time: int | None
    end_time: int | None = None
    large_image: str | None = "rocketleague"
    large_text: str | None = "Rocket League"
    small_image: str | None = None
    small_text: str | None = None


@dataclass(slots=True)
class MatchCache:
    arena: str = "Unknown Arena"
    blue_score: int = 0
    orange_score: int = 0
    time_seconds: int = 0
    overtime: bool = False
    replay: bool = False
    paused: bool = False
    ended: bool = False
    winner: str = ""
    phase: str = "Waiting for Match"
    last_goal_by: str | None = None
    goal_highlight_until: float = 0.0
    match_started_at: int | None = None


def apply_event(cache: MatchCache, event: EventMessage) -> None:
    now = time.time()
    data = event.data

    if event.event == "UpdateState":
        game = data.get("Game") or {}
        teams = game.get("Teams") or []
        cache.arena = str(game.get("Arena") or cache.arena)
        cache.time_seconds = int(game.get("TimeSeconds") or 0)
        cache.overtime = bool(game.get("bOvertime"))
        cache.replay = bool(game.get("bReplay"))
        cache.ended = bool(game.get("bHasWinner"))
        cache.winner = str(game.get("Winner") or "")

        for team in teams:
            team_num = int(team.get("TeamNum", -1))
            score = int(team.get("Score", 0))
            if team_num == 0:
                cache.blue_score = score
            elif team_num == 1:
                cache.orange_score = score

        if cache.ended:
            cache.phase = "Match Ended"
        elif cache.paused:
            cache.phase = "Match Paused"
        elif cache.replay:
            cache.phase = "Goal Replay"
        elif cache.overtime:
            cache.phase = "Overtime"
        else:
            cache.phase = "In Match"

        if cache.match_started_at is None and cache.phase in {"In Match", "Overtime"}:
            cache.match_started_at = int(now)

    elif event.event == "CountdownBegin":
        cache.phase = "Kickoff Countdown"
    elif event.event == "RoundStarted":
        cache.phase = "In Match"
        if cache.match_started_at is None:
            cache.match_started_at = int(now)
    elif event.event == "GoalScored":
        scorer = (data.get("Scorer") or {}).get("Name")
        cache.last_goal_by = str(scorer or "Unknown")
        cache.goal_highlight_until = now + 5.0
    elif event.event == "MatchPaused":
        cache.paused = True
        cache.phase = "Match Paused"
    elif event.event == "MatchUnpaused":
        cache.paused = False
        cache.phase = "In Match"
    elif event.event == "MatchEnded":
        cache.ended = True
        winner_num = data.get("WinnerTeamNum")
        if winner_num == 0:
            cache.winner = "Blue"
        elif winner_num == 1:
            cache.winner = "Orange"
        cache.phase = "Match Ended"
    elif event.event == "MatchDestroyed":
        fresh = MatchCache()
        cache.arena = fresh.arena
        cache.blue_score = fresh.blue_score
        cache.orange_score = fresh.orange_score
        cache.time_seconds = fresh.time_seconds
        cache.overtime = fresh.overtime
        cache.replay = fresh.replay
        cache.paused = fresh.paused
        cache.ended = fresh.ended
        cache.winner = fresh.winner
        cache.phase = fresh.phase
        cache.last_goal_by = fresh.last_goal_by
        cache.goal_highlight_until = fresh.goal_highlight_until
        cache.match_started_at = fresh.match_started_at


def build_presence(cache: MatchCache) -> PresenceState:
    now = time.time()

    if cache.goal_highlight_until > now and cache.last_goal_by:
        details = f"Goal by {cache.last_goal_by}"
    else:
        details = cache.phase

    if cache.ended and cache.winner:
        state = f"Winner: {cache.winner} | {cache.blue_score}-{cache.orange_score}"
    elif cache.phase == "Kickoff Countdown":
        state = f"Arena: {cache.arena}"
    else:
        clock = "OT" if cache.overtime else _fmt_time(cache.time_seconds)
        state = f"Blue {cache.blue_score} - {cache.orange_score} Orange | {clock}"

    return PresenceState(
        details=details,
        state=state,
        start_time=cache.match_started_at,
        large_text=cache.arena or "Rocket League",
        small_image="overtime" if cache.overtime else None,
        small_text="Overtime" if cache.overtime else None,
    )


def _fmt_time(seconds: int) -> str:
    seconds = max(0, seconds)
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"

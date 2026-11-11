"""State tracker that maintains a rolling match summary from live events."""

from __future__ import annotations

from typing import Any, TypeGuard

from .models import EventMessage, MatchStateSnapshot, PlayerSnapshot


def _is_int(value: object) -> TypeGuard[int]:
    """Return ``True`` when ``value`` is an ``int`` and not a ``bool``."""
    return isinstance(value, int) and not isinstance(value, bool)


def _int_or_zero(value: object) -> int:
    """Return ``value`` when it is a non-boolean ``int``, otherwise ``0``."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _build_player_snapshot(player: dict[str, Any]) -> PlayerSnapshot | None:
    """Build a ``PlayerSnapshot`` from one ``UpdateState.Players`` entry."""
    name = player.get("Name")
    shortcut = player.get("Shortcut")
    if not isinstance(name, str) or not _is_int(shortcut):
        return None
    team_num = player.get("TeamNum")
    raw_speed = player.get("Speed")
    speed = (
        float(raw_speed)
        if isinstance(raw_speed, (int, float)) and not isinstance(raw_speed, bool)
        else 0.0
    )
    return PlayerSnapshot(
        name=name,
        shortcut=shortcut,
        team_num=team_num if _is_int(team_num) else 0,
        score=_int_or_zero(player.get("Score")),
        goals=_int_or_zero(player.get("Goals")),
        assists=_int_or_zero(player.get("Assists")),
        saves=_int_or_zero(player.get("Saves")),
        shots=_int_or_zero(player.get("Shots")),
        boost=_int_or_zero(player.get("Boost")),
        speed=speed,
        is_demolished=bool(player.get("bDemolished", False)),
    )


class MatchStateTracker:
    """Maintain a rolling summary of the active match from incoming events."""

    def __init__(self) -> None:
        """Initialize the tracker with an empty ``MatchStateSnapshot``."""
        self._snapshot = MatchStateSnapshot()

    @property
    def snapshot(self) -> MatchStateSnapshot:
        """Current mutable match snapshot updated by ``update()``."""
        return self._snapshot

    def reset(self) -> None:
        """Replace the current snapshot with a fresh ``MatchStateSnapshot``."""
        self._snapshot = MatchStateSnapshot()

    def update(self, message: EventMessage) -> MatchStateSnapshot:
        """Apply one incoming event and return the updated snapshot.

        Args:
            message: Normalized event message from the stream.

        Returns:
            MatchStateSnapshot: The updated match state snapshot.
        """
        event = message.event
        if event == "MatchDestroyed":
            self.reset()
            snapshot = self._snapshot
            snapshot.last_event = event
            snapshot.event_counts[event] = 1
            return snapshot

        snapshot = self._snapshot
        snapshot.last_event = event
        counts = snapshot.event_counts
        counts[event] = counts.get(event, 0) + 1

        data = message.data
        match_guid = data.get("MatchGuid")
        if isinstance(match_guid, str) and match_guid:
            snapshot.match_guid = match_guid

        if event == "UpdateState":
            self._apply_update_state(snapshot, data)
        elif event == "ClockUpdatedSeconds":
            self._apply_clock_updated(snapshot, data)
        elif event == "GoalScored":
            self._apply_goal_scored(snapshot, data)
        elif event == "GoalReplayStart":
            snapshot.replay_active = True
        elif event == "GoalReplayEnd":
            snapshot.replay_active = False
        elif event == "MatchEnded":
            snapshot.has_winner = True

        return snapshot

    def _apply_update_state(
        self,
        snapshot: MatchStateSnapshot,
        data: dict[str, Any],
    ) -> None:
        """Extract game, team, and player fields from an ``UpdateState`` payload."""
        game = data.get("Game")
        if not isinstance(game, dict):
            return

        self._apply_teams(snapshot, game.get("Teams"))
        self._apply_players(snapshot, data.get("Players"), game)

        time_seconds = game.get("TimeSeconds")
        if _is_int(time_seconds):
            snapshot.time_seconds = time_seconds

        snapshot.overtime = bool(game.get("bOvertime", False))
        snapshot.replay_active = bool(game.get("bReplay", False))
        snapshot.has_winner = bool(game.get("bHasWinner", False))

        arena = game.get("Arena")
        if isinstance(arena, str) and arena:
            snapshot.arena = arena

        winner = game.get("Winner")
        if isinstance(winner, str) and winner:
            snapshot.winner = winner

    def _apply_clock_updated(
        self,
        snapshot: MatchStateSnapshot,
        data: dict[str, Any],
    ) -> None:
        """Update clock seconds and overtime flag from ``ClockUpdatedSeconds``."""
        time_seconds = data.get("TimeSeconds")
        if _is_int(time_seconds):
            snapshot.time_seconds = time_seconds
        if "bOvertime" in data:
            snapshot.overtime = bool(data.get("bOvertime", False))

    def _apply_teams(self, snapshot: MatchStateSnapshot, teams: object) -> None:
        """Update blue and orange scores from the ``Teams`` list."""
        if not isinstance(teams, list):
            return

        for team in teams:
            if not isinstance(team, dict):
                continue
            team_num = team.get("TeamNum")
            score = team.get("Score")
            if not _is_int(score):
                continue
            if team_num == 0:
                snapshot.blue_score = score
            elif team_num == 1:
                snapshot.orange_score = score

    def _apply_players(
        self,
        snapshot: MatchStateSnapshot,
        players: object,
        game: dict[str, Any],
    ) -> None:
        """Rebuild the player list and resolve ``target_player``."""
        if not isinstance(players, list):
            snapshot.players = []
            snapshot.target_player = None
            return

        target_shortcut: int | None = None
        if game.get("bHasTarget"):
            target = game.get("Target")
            if isinstance(target, dict):
                raw_target = target.get("Shortcut")
                if _is_int(raw_target):
                    target_shortcut = raw_target

        result: list[PlayerSnapshot] = []
        target_player: PlayerSnapshot | None = None

        for entry in players:
            if not isinstance(entry, dict):
                continue
            player_snapshot = _build_player_snapshot(entry)
            if player_snapshot is None:
                continue
            result.append(player_snapshot)
            if target_player is None and player_snapshot.shortcut == target_shortcut:
                target_player = player_snapshot

        snapshot.players = result
        snapshot.target_player = target_player

    def _apply_goal_scored(
        self,
        snapshot: MatchStateSnapshot,
        data: dict[str, Any],
    ) -> None:
        """Update last scorer name and goal speed from a ``GoalScored`` payload."""
        scorer = data.get("Scorer")
        if isinstance(scorer, dict):
            name = scorer.get("Name")
            if isinstance(name, str) and name:
                snapshot.last_scorer = name

        goal_speed = data.get("GoalSpeed")
        if isinstance(goal_speed, (int, float)) and not isinstance(goal_speed, bool):
            snapshot.last_goal_speed = float(goal_speed)

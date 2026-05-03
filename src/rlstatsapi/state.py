"""
Lightweight helpers for tracking a match summary from the live event stream.

The goal here is convenience, not full replay-state reconstruction. The tracker
keeps the handful of fields that most HUDs, overlays, bots, and dashboards want
without forcing users to rebuild the same state cache in every script.
"""

from __future__ import annotations

from .models import EventMessage, MatchStateSnapshot, PlayerSnapshot


class MatchStateTracker:
    """Maintain a rolling summary of the latest match state seen by the client."""

    def __init__(self) -> None:
        self._snapshot = MatchStateSnapshot()

    @property
    def snapshot(self) -> MatchStateSnapshot:
        """Return the mutable snapshot object updated by incoming events."""
        return self._snapshot

    def reset(self) -> None:
        """Clear the current snapshot when a match ends or the caller wants a reset."""
        self._snapshot = MatchStateSnapshot()

    def update(self, message: EventMessage) -> MatchStateSnapshot:
        """Apply one incoming event and return the updated snapshot."""
        snapshot = self._snapshot
        snapshot.last_event = message.event
        snapshot.event_counts[message.event] = (
            snapshot.event_counts.get(message.event, 0) + 1
        )

        match_guid = message.data.get("MatchGuid")
        if isinstance(match_guid, str) and match_guid:
            snapshot.match_guid = match_guid

        if message.event == "UpdateState":
            self._apply_update_state(snapshot, message)

        elif message.event == "GoalScored":
            self._apply_goal_scored(snapshot, message)

        elif message.event == "MatchEnded":
            snapshot.has_winner = True

        elif message.event == "MatchDestroyed":
            self.reset()
            snapshot = self._snapshot

        return snapshot

    def _apply_update_state(
        self,
        snapshot: MatchStateSnapshot,
        message: EventMessage,
    ) -> None:
        """Extract game-level fields from an UpdateState payload into the snapshot."""
        game = message.data.get("Game", {})
        if not isinstance(game, dict):
            return

        self._apply_teams(snapshot, game.get("Teams", []))
        self._apply_players(snapshot, message.data.get("Players", []), game)

        time_seconds = game.get("TimeSeconds")
        if isinstance(time_seconds, int):
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

    def _apply_teams(self, snapshot: MatchStateSnapshot, teams: object) -> None:
        """Update blue/orange score from the Teams list in an UpdateState payload."""
        if not isinstance(teams, list):
            return

        for team in teams:
            if not isinstance(team, dict):
                continue
            team_num = team.get("TeamNum")
            score = team.get("Score")
            if team_num == 0 and isinstance(score, int):
                snapshot.blue_score = score
            if team_num == 1 and isinstance(score, int):
                snapshot.orange_score = score

    def _apply_players(
        self,
        snapshot: MatchStateSnapshot,
        players: object,
        game: dict,
    ) -> None:
        """Rebuild the players list and resolve target_player from UpdateState."""
        if not isinstance(players, list):
            snapshot.players = []
            snapshot.target_player = None
            return

        result: list[PlayerSnapshot] = []
        for p in players:
            if not isinstance(p, dict):
                continue
            name = p.get("Name")
            shortcut = p.get("Shortcut")
            team_num = p.get("TeamNum")
            if not isinstance(name, str) or not isinstance(shortcut, int):
                continue
            result.append(
                PlayerSnapshot(
                    name=name,
                    shortcut=shortcut,
                    team_num=team_num if isinstance(team_num, int) else 0,
                    score=p.get("Score") or 0,
                    goals=p.get("Goals") or 0,
                    assists=p.get("Assists") or 0,
                    saves=p.get("Saves") or 0,
                    shots=p.get("Shots") or 0,
                    boost=p.get("Boost") or 0,
                    speed=float(p.get("Speed") or 0.0),
                    is_demolished=bool(p.get("bDemolished", False)),
                )
            )
        snapshot.players = result

        target_player: PlayerSnapshot | None = None
        if game.get("bHasTarget"):
            target = game.get("Target")
            if isinstance(target, dict):
                target_shortcut = target.get("Shortcut")
                if isinstance(target_shortcut, int):
                    for player in result:
                        if player.shortcut == target_shortcut:
                            target_player = player
                            break
        snapshot.target_player = target_player

    def _apply_goal_scored(
        self,
        snapshot: MatchStateSnapshot,
        message: EventMessage,
    ) -> None:
        """Update last scorer name and goal speed from a GoalScored payload."""
        scorer = message.data.get("Scorer", {})
        if isinstance(scorer, dict):
            name = scorer.get("Name")
            if isinstance(name, str) and name:
                snapshot.last_scorer = name

        goal_speed = message.data.get("GoalSpeed")
        if isinstance(goal_speed, (int, float)):
            snapshot.last_goal_speed = float(goal_speed)

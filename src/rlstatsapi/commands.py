"""Builders and validation for commands the game accepts over the Stats API socket.

Rocket League drops malformed commands without replying, so every builder
validates its arguments locally and raises ``InvalidCommandError`` instead.
"""

from __future__ import annotations

import json
import math
from typing import Any, Literal, Mapping, TypeAlias, TypedDict

CommandName: TypeAlias = Literal[
    "ChangePOV",
    "LoadReplay",
    "SeekReplay",
    "SetGameSpeed",
    "SetHUDVisibility",
    "SetMatchPaused",
]

Perspective: TypeAlias = Literal[
    "Fly",
    "SoftAttach",
    "HardAttach",
    "PlayerView",
    "AutoCam",
    "Camera_Director",
]

COMMAND_NAMES: tuple[str, ...] = (
    "ChangePOV",
    "LoadReplay",
    "SeekReplay",
    "SetGameSpeed",
    "SetHUDVisibility",
    "SetMatchPaused",
)

PERSPECTIVES: tuple[str, ...] = (
    "Fly",
    "SoftAttach",
    "HardAttach",
    "PlayerView",
    "AutoCam",
    "Camera_Director",
)


class Command(TypedDict):
    """Wire envelope for a Stats API command."""

    Command: str
    Data: dict[str, Any]


class InvalidCommandError(ValueError):
    """Raised when a command would be rejected by the game.

    Attributes:
        command: Name of the offending command.
        reason: Why the command is invalid.
    """

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(f"{command or 'command'}: {reason}")
        self.command = command
        self.reason = reason


def _is_number(value: object) -> bool:
    """Return ``True`` for a finite, non-negative ``int`` or ``float`` (not ``bool``)."""
    if type(value) not in (int, float):
        return False
    return math.isfinite(value) and value >= 0  # type: ignore[arg-type,operator]


def change_pov(
    focus: int | Literal["Ball"] | str | None = None,
    perspective: Perspective | None = None,
) -> Command:
    """Build a ``ChangePOV`` command (spectator or replay only).

    Args:
        focus: ``"Ball"`` or a player's spectator shortcut (int or digit string).
        perspective: Camera mode, one of ``PERSPECTIVES``.

    Returns:
        Command: Validated command envelope.

    Raises:
        InvalidCommandError: If both arguments are missing or a value is not accepted.
    """
    data: dict[str, Any] = {}
    if focus is not None:
        text = str(focus) if type(focus) is int else focus
        if not isinstance(text, str) or not (
            text == "Ball" or (text.isascii() and text.isdigit())
        ):
            raise InvalidCommandError(
                "ChangePOV", 'Focus must be "Ball" or a spectator shortcut'
            )
        data["Focus"] = text
    if perspective is not None:
        if perspective not in PERSPECTIVES:
            raise InvalidCommandError(
                "ChangePOV", f"Perspective must be one of {', '.join(PERSPECTIVES)}"
            )
        data["Perspective"] = perspective
    if not data:
        raise InvalidCommandError(
            "ChangePOV", "at least one of Focus or Perspective is required"
        )
    return {"Command": "ChangePOV", "Data": data}


def load_replay(file_name: str | None = None, path: str | None = None) -> Command:
    """Build a ``LoadReplay`` command.

    Args:
        file_name: Replay file name. Takes precedence over ``path`` in the game.
        path: Replay file path, used when ``file_name`` is empty.

    Returns:
        Command: Validated command envelope.

    Raises:
        InvalidCommandError: If neither argument is a non-empty string.
    """
    data: dict[str, Any] = {}
    for key, value in (("FileName", file_name), ("Path", path)):
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise InvalidCommandError("LoadReplay", f"{key} must be a string")
        data[key] = value
    if not data:
        raise InvalidCommandError("LoadReplay", "one of FileName or Path is required")
    return {"Command": "LoadReplay", "Data": data}


def seek_replay(frame: int | None = None, time_seconds: float | None = None) -> Command:
    """Build a ``SeekReplay`` command (replay only).

    Args:
        frame: Target frame number. Takes precedence over ``time_seconds`` in the game.
        time_seconds: Target time in seconds.

    Returns:
        Command: Validated command envelope.

    Raises:
        InvalidCommandError: If both are missing or a value is negative or not finite.
    """
    data: dict[str, Any] = {}
    if frame is not None:
        if type(frame) is not int or frame < 0:
            raise InvalidCommandError(
                "SeekReplay", "Frame must be a non-negative integer"
            )
        data["Frame"] = frame
    if time_seconds is not None:
        if not _is_number(time_seconds):
            raise InvalidCommandError(
                "SeekReplay", "TimeSeconds must be a finite, non-negative number"
            )
        data["TimeSeconds"] = time_seconds
    if not data:
        raise InvalidCommandError(
            "SeekReplay", "one of Frame or TimeSeconds is required"
        )
    return {"Command": "SeekReplay", "Data": data}


def set_game_speed(speed: float) -> Command:
    """Build a ``SetGameSpeed`` command (replay only). ``1.0`` is normal speed.

    Raises:
        InvalidCommandError: If ``speed`` is negative or not finite.
    """
    if not _is_number(speed):
        raise InvalidCommandError(
            "SetGameSpeed", "Speed must be a finite, non-negative number"
        )
    return {"Command": "SetGameSpeed", "Data": {"Speed": speed}}


def set_hud_visibility(visible: bool) -> Command:
    """Build a ``SetHUDVisibility`` command.

    Raises:
        InvalidCommandError: If ``visible`` is not a ``bool``.
    """
    if type(visible) is not bool:
        raise InvalidCommandError("SetHUDVisibility", "bVisible must be a boolean")
    return {"Command": "SetHUDVisibility", "Data": {"bVisible": visible}}


def set_match_paused(paused: bool) -> Command:
    """Build a ``SetMatchPaused`` command for the current match or replay.

    Raises:
        InvalidCommandError: If ``paused`` is not a ``bool``.
    """
    if type(paused) is not bool:
        raise InvalidCommandError("SetMatchPaused", "bPaused must be a boolean")
    return {"Command": "SetMatchPaused", "Data": {"bPaused": paused}}


def build_command(name: str, data: Mapping[str, Any] | None = None) -> Command:
    """Validate a command given by wire name and ``Data`` mapping.

    Args:
        name: Command name, one of ``COMMAND_NAMES``.
        data: Wire-format variables (for example ``{"bVisible": False}``).

    Returns:
        Command: Validated command envelope with unknown keys removed.

    Raises:
        InvalidCommandError: If the name is unknown or the data is not accepted.
    """
    data = data or {}
    if not isinstance(data, Mapping):
        raise InvalidCommandError(str(name), "Data must be an object")
    get = data.get
    if name == "ChangePOV":
        return change_pov(get("Focus"), get("Perspective"))
    if name == "LoadReplay":
        return load_replay(get("FileName"), get("Path"))
    if name == "SeekReplay":
        return seek_replay(get("Frame"), get("TimeSeconds"))
    if name == "SetGameSpeed":
        return set_game_speed(get("Speed"))  # type: ignore[arg-type]
    if name == "SetHUDVisibility":
        return set_hud_visibility(get("bVisible"))  # type: ignore[arg-type]
    if name == "SetMatchPaused":
        return set_match_paused(get("bPaused"))  # type: ignore[arg-type]
    raise InvalidCommandError(
        str(name), f"unsupported command; expected one of {', '.join(COMMAND_NAMES)}"
    )


def encode_command(command: Mapping[str, Any]) -> bytes:
    """Validate ``command`` and return its compact UTF-8 JSON encoding.

    Args:
        command: Envelope with ``Command`` and optional ``Data`` keys.

    Returns:
        bytes: Bytes ready to write to the Stats API socket.

    Raises:
        InvalidCommandError: If the envelope or its data is not accepted.
    """
    name = command.get("Command") if isinstance(command, Mapping) else None
    if not isinstance(name, str):
        raise InvalidCommandError("", "missing Command string")
    validated = build_command(name, command.get("Data"))
    return json.dumps(validated, separators=(",", ":"), ensure_ascii=False).encode()

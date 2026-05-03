"""Helpers for reading and updating Rocket League's TAStatsAPI.ini.

This module keeps file management separate from the network client so users can
prepare the game config before starting Rocket League and then connect with
``StatsClient`` using the same port.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger("rlstatsapi.config")

DEFAULT_PACKET_SEND_RATE = 30
DEFAULT_STATS_API_PORT = 49123
DEFAULT_STATS_API_FILENAME = "TAStatsAPI.ini"
_USER_CONFIG_RELATIVE_DIR = Path("My Games") / "Rocket League" / "TAGame" / "Config"
_WARNING = (
    "TAStatsAPI.ini was not found automatically. Pass an explicit path if "
    "your Rocket League config lives in a custom location."
)


@dataclass(slots=True)
class StatsAPIConfigStatus:
    """Snapshot of the current Stats API config file state."""

    found: bool
    enabled: bool
    path: str | None
    packet_send_rate: int | None
    port: int | None
    warning: str | None = None
    discovery_scope: str = "windows-user-config"


def candidate_stats_api_paths() -> list[Path]:
    """Return likely user config locations for ``TAStatsAPI.ini`` on Windows."""
    roots: list[Path] = []
    for env_name in ("USERPROFILE", "HOME"):
        value = os.getenv(env_name)
        if value:
            root = Path(value).expanduser().resolve()
            if root.exists():
                roots.append(root)

    candidates: list[Path] = []
    for root in roots:
        candidates.append(
            root / "Documents" / _USER_CONFIG_RELATIVE_DIR / DEFAULT_STATS_API_FILENAME
        )
        candidates.append(
            root / "Documentos" / _USER_CONFIG_RELATIVE_DIR / DEFAULT_STATS_API_FILENAME
        )
        candidates.append(
            root
            / "OneDrive"
            / "Documents"
            / _USER_CONFIG_RELATIVE_DIR
            / DEFAULT_STATS_API_FILENAME
        )
        candidates.append(
            root
            / "OneDrive"
            / "Documentos"
            / _USER_CONFIG_RELATIVE_DIR
            / DEFAULT_STATS_API_FILENAME
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_stats_api_config(path: str | Path | None = None) -> Path | None:
    """Resolve an explicit config path or the first matching auto-discovered path."""
    if path is not None:
        explicit = Path(path).expanduser().resolve()
        return explicit if explicit.exists() else None

    for candidate in candidate_stats_api_paths():
        if candidate.exists():
            return candidate
    return None


def get_stats_api_status(path: str | Path | None = None) -> StatsAPIConfigStatus:
    """Read the current enabled state, send rate, and port from the config file."""
    config_path = find_stats_api_config(path)
    if config_path is None:
        return StatsAPIConfigStatus(
            found=False,
            enabled=False,
            path=str(Path(path).expanduser().resolve()) if path is not None else None,
            packet_send_rate=None,
            port=None,
            warning=_WARNING,
        )
    return _status_for_path(config_path)


def set_stats_api_enabled(
    enabled: bool,
    packet_send_rate: int = DEFAULT_PACKET_SEND_RATE,
    path: str | Path | None = None,
) -> StatsAPIConfigStatus:
    """Write ``PacketSendRate`` and preserve the current port."""
    if enabled:
        _validate_packet_send_rate(packet_send_rate)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines = _set_or_append_key(
        lines,
        "PacketSendRate",
        "0" if not enabled else str(packet_send_rate),
    )
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def set_stats_api_port(
    port: int,
    path: str | Path | None = None,
) -> StatsAPIConfigStatus:
    """Write the local TCP port used by Rocket League's stats exporter."""
    _validate_port(port)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines = _set_or_append_key(lines, "Port", str(port))
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def configure_stats_api(
    enabled: bool,
    port: int = DEFAULT_STATS_API_PORT,
    packet_send_rate: int = DEFAULT_PACKET_SEND_RATE,
    path: str | Path | None = None,
) -> StatsAPIConfigStatus:
    """Set ``PacketSendRate`` and ``Port`` together in one write operation."""
    _validate_port(port)
    if enabled:
        _validate_packet_send_rate(packet_send_rate)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines = _set_or_append_key(
        lines,
        "PacketSendRate",
        "0" if not enabled else str(packet_send_rate),
    )
    lines = _set_or_append_key(lines, "Port", str(port))
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def _require_config_path(path: str | Path | None) -> Path:
    """Return the resolved config path or raise ``FileNotFoundError`` if not found."""
    config_path = find_stats_api_config(path)
    if config_path is None:
        raise FileNotFoundError(_WARNING)
    return config_path


def _parse_int(value: str | None) -> int | None:
    """Parse a string to int, returning None on failure or missing input."""
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _read_key_values(text: str) -> dict[str, str]:
    """Parse ``key=value`` pairs from INI-style text, ignoring comments and blank lines."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if "=" not in stripped:
            _logger.warning("skipped malformed config line: %r", stripped)
            continue
        key, value = stripped.split("=", 1)
        values[key.strip().casefold()] = value.strip()
    return values


def _status_for_path(path: Path) -> StatsAPIConfigStatus:
    """Build a ``StatsAPIConfigStatus`` by reading and parsing an existing config file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return StatsAPIConfigStatus(
            found=False,
            enabled=False,
            path=str(path),
            packet_send_rate=None,
            port=None,
            warning=_WARNING,
        )
    values = _read_key_values(text)
    packet_send_rate = _parse_int(values.get("packetsendrate"))
    port = _parse_int(values.get("port"))
    return StatsAPIConfigStatus(
        found=True,
        enabled=bool(packet_send_rate and packet_send_rate > 0),
        path=str(path),
        packet_send_rate=packet_send_rate,
        port=port,
        warning=None,
    )


def _set_or_append_key(lines: list[str], key: str, value: str) -> list[str]:
    """Replace an existing ``key=value`` line in-place, or append it if not present."""
    output: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            output.append(line)
            continue
        current_key, _current_value = stripped.split("=", 1)
        if current_key.strip().casefold() == key.casefold():
            leading = line[: len(line) - len(line.lstrip())]
            output.append(f"{leading}{key}={value}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{key}={value}")
    return output


def _write_lines(path: Path, lines: list[str], original_text: str) -> None:
    """Write lines back to file, preserving the original trailing newline."""
    newline = "\n" if original_text.endswith(("\n", "\r\n")) else ""
    path.write_text("\n".join(lines) + newline, encoding="utf-8")


def _validate_packet_send_rate(packet_send_rate: int) -> None:
    """Raise ``ValueError`` if packet_send_rate is outside the valid range [1, 120]."""
    if packet_send_rate < 1 or packet_send_rate > 120:
        raise ValueError("packet_send_rate must be between 1 and 120 when enabled")


def _validate_port(port: int) -> None:
    """Raise ``ValueError`` if port is outside the valid range [1, 65535]."""
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")

"""Helpers for reading and updating Rocket League's ``TAStatsAPI.ini`` file."""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger("rlstatsapi.config")

DEFAULT_PACKET_SEND_RATE = 30
DEFAULT_STATS_API_PORT = 49123
DEFAULT_STATS_API_WEB_PORT = 49124
DEFAULT_STATS_API_FILENAME = "TAStatsAPI.ini"
DEFAULT_STATS_API_FALLBACK_FILENAME = "DefaultStatsAPI.ini"
_USER_CONFIG_RELATIVE_DIR = Path("My Games") / "Rocket League" / "TAGame" / "Config"
_WARNING = (
    "TAStatsAPI.ini was not found automatically. Pass an explicit path if "
    "your Rocket League config lives in a custom location."
)


@dataclass(slots=True)
class StatsAPIConfigStatus:
    """Snapshot of the Rocket League Stats API configuration file state.

    Attributes:
        found: Whether the target ``TAStatsAPI.ini`` file exists on disk.
        enabled: ``True`` when ``PacketSendRate`` is present and greater than 0.
        path: Resolved file path as a string, or ``None`` if not found.
        packet_send_rate: Parsed ``PacketSendRate`` value, or ``None``.
        port: Parsed ``Port`` value, or ``None``.
        web_port: Parsed ``WebPort`` (WebSocket) value, or ``None``. ``0`` means disabled.
        warning: Diagnostic message when the config file was not found.
        discovery_scope: Discovery strategy label.
    """

    found: bool
    enabled: bool
    path: str | None
    packet_send_rate: int | None
    port: int | None
    warning: str | None = None
    discovery_scope: str = "windows-user-config"
    web_port: int | None = None


def candidate_stats_api_paths() -> list[Path]:
    """Return candidate user paths for the Stats API config on Windows.

    In each folder ``TAStatsAPI.ini`` comes before ``DefaultStatsAPI.ini``,
    which is the order the game uses.

    Returns:
        list[Path]: Deduplicated list of candidate config paths.
    """
    roots: list[Path] = []
    for env_name in ("USERPROFILE", "HOME"):
        value = os.getenv(env_name)
        if value:
            root = Path(value).expanduser().resolve()
            if root.exists():
                roots.append(root)

    candidates: list[Path] = []
    for root in roots:
        for documents in (
            root / "Documents",
            root / "Documentos",
            root / "OneDrive" / "Documents",
            root / "OneDrive" / "Documentos",
        ):
            folder = documents / _USER_CONFIG_RELATIVE_DIR
            candidates.append(folder / DEFAULT_STATS_API_FILENAME)
            candidates.append(folder / DEFAULT_STATS_API_FALLBACK_FILENAME)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_stats_api_config(path: str | Path | None = None) -> Path | None:
    """Resolve an explicit config path or the first existing auto-discovered path.

    Args:
        path: Optional explicit path to ``TAStatsAPI.ini``.

    Returns:
        Path | None: Resolved path if the file exists, otherwise ``None``.
    """
    if path is not None:
        explicit = Path(path).expanduser().resolve()
        return explicit if explicit.exists() else None

    for candidate in candidate_stats_api_paths():
        if candidate.exists():
            return candidate
    return None


def get_stats_api_status(path: str | Path | None = None) -> StatsAPIConfigStatus:
    """Read the current enabled state, send rate, and port from ``TAStatsAPI.ini``.

    Args:
        path: Optional explicit path to ``TAStatsAPI.ini``.

    Returns:
        StatsAPIConfigStatus: Parsed status snapshot for the config file.
    """
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
    """Update ``PacketSendRate`` in ``TAStatsAPI.ini`` and preserve other settings.

    Args:
        enabled: ``True`` to write ``packet_send_rate``, ``False`` to write ``0``.
        packet_send_rate: Send rate between 1 and 120 when ``enabled`` is ``True``.
        path: Optional explicit path to ``TAStatsAPI.ini``.

    Returns:
        StatsAPIConfigStatus: Updated status read back from disk.

    Raises:
        ValueError: If ``enabled`` is ``True`` and ``packet_send_rate`` is outside 1..120.
        FileNotFoundError: If the config file cannot be found.
    """
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
    """Update ``Port`` in ``TAStatsAPI.ini`` and preserve other settings.

    Args:
        port: TCP port between 1 and 65535.
        path: Optional explicit path to ``TAStatsAPI.ini``.

    Returns:
        StatsAPIConfigStatus: Updated status read back from disk.

    Raises:
        ValueError: If ``port`` is outside 1..65535.
        FileNotFoundError: If the config file cannot be found.
    """
    _validate_port(port)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    _check_port_conflict(port, _current_web_port(text))
    lines = text.splitlines()
    lines = _set_or_append_key(lines, "Port", str(port))
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def set_stats_api_web_port(
    web_port: int,
    path: str | Path | None = None,
) -> StatsAPIConfigStatus:
    """Update ``WebPort`` (the WebSocket port) and preserve other settings.

    Args:
        web_port: WebSocket port between 1 and 65535, or ``0`` to disable it.
        path: Optional explicit path to ``TAStatsAPI.ini``.

    Returns:
        StatsAPIConfigStatus: Updated status read back from disk.

    Raises:
        ValueError: If ``web_port`` is out of range or equal to ``Port``.
        FileNotFoundError: If the config file cannot be found.
    """
    _validate_web_port(web_port)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    port = _parse_int(_read_key_values(text).get("port"))
    _check_port_conflict(DEFAULT_STATS_API_PORT if port is None else port, web_port)
    lines = text.splitlines()
    lines = _set_or_append_key(lines, "WebPort", str(web_port))
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def configure_stats_api(
    enabled: bool,
    port: int = DEFAULT_STATS_API_PORT,
    packet_send_rate: int = DEFAULT_PACKET_SEND_RATE,
    path: str | Path | None = None,
    web_port: int | None = None,
) -> StatsAPIConfigStatus:
    """Update ``PacketSendRate``, ``Port`` and optionally ``WebPort`` in one write.

    Args:
        enabled: ``True`` to write ``packet_send_rate``, ``False`` to write ``0``.
        port: TCP port between 1 and 65535.
        packet_send_rate: Send rate between 1 and 120 when ``enabled`` is ``True``.
        path: Optional explicit path to ``TAStatsAPI.ini``.
        web_port: WebSocket port, ``0`` to disable it, or ``None`` to leave the
            file's value untouched.

    Returns:
        StatsAPIConfigStatus: Updated status read back from disk.

    Raises:
        ValueError: If a value is out of range or ``port`` equals the WebSocket port.
        FileNotFoundError: If the config file cannot be found.
    """
    _validate_port(port)
    if web_port is not None:
        _validate_web_port(web_port)
    if enabled:
        _validate_packet_send_rate(packet_send_rate)

    config_path = _require_config_path(path)
    text = config_path.read_text(encoding="utf-8")
    _check_port_conflict(
        port, _current_web_port(text) if web_port is None else web_port
    )
    lines = text.splitlines()
    lines = _set_or_append_key(
        lines,
        "PacketSendRate",
        "0" if not enabled else str(packet_send_rate),
    )
    lines = _set_or_append_key(lines, "Port", str(port))
    if web_port is not None:
        lines = _set_or_append_key(lines, "WebPort", str(web_port))
    _write_lines(config_path, lines, text)
    return _status_for_path(config_path)


def _require_config_path(path: str | Path | None) -> Path:
    """Return the resolved config path or raise ``FileNotFoundError``."""
    config_path = find_stats_api_config(path)
    if config_path is None:
        raise FileNotFoundError(_WARNING)
    return config_path


def _parse_int(value: str | None) -> int | None:
    """Parse an integer string or return ``None`` when missing or invalid."""
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        pass
    try:  # the game documents PacketSendRate as a float ("30.0")
        number = float(value.strip())
    except ValueError:
        return None
    return int(number) if math.isfinite(number) else None


def _current_web_port(text: str) -> int:
    """Return the ``WebPort`` in ``text``, or the game default when it is missing."""
    web_port = _parse_int(_read_key_values(text).get("webport"))
    return DEFAULT_STATS_API_WEB_PORT if web_port is None else web_port


def _check_port_conflict(port: int, web_port: int) -> None:
    """Raise ``ValueError`` when the TCP and WebSocket ports are the same."""
    if web_port != 0 and port == web_port:
        raise ValueError(
            f"Port and WebPort must differ (both are {port}); the game refuses equal ports"
        )


def _read_key_values(text: str) -> dict[str, str]:
    """Parse ``key=value`` pairs from INI text, ignoring comments and section headers."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("#", ";"))
            or (stripped.startswith("[") and stripped.endswith("]"))
        ):
            continue
        if "=" not in stripped:
            _logger.warning("skipped malformed config line: %r", stripped)
            continue
        key, value = stripped.split("=", 1)
        values[key.strip().casefold()] = value.strip()
    return values


def _status_for_path(path: Path) -> StatsAPIConfigStatus:
    """Read and parse ``path`` into a ``StatsAPIConfigStatus`` instance."""
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
    web_port = _parse_int(values.get("webport"))
    return StatsAPIConfigStatus(
        found=True,
        enabled=bool(packet_send_rate and packet_send_rate > 0),
        path=str(path),
        packet_send_rate=packet_send_rate,
        port=port,
        warning=None,
        web_port=web_port,
    )


def _set_or_append_key(lines: list[str], key: str, value: str) -> list[str]:
    """Replace an existing ``key=value`` line in-place (deduplicating repeats) or append it."""
    output: list[str] = []
    replaced = False
    target_key = key.casefold()
    for line in lines:
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("#", ";"))
            or (stripped.startswith("[") and stripped.endswith("]"))
            or "=" not in stripped
        ):
            output.append(line)
            continue
        current_key, _current_value = stripped.split("=", 1)
        if current_key.strip().casefold() == target_key:
            if not replaced:
                leading = line[: len(line) - len(line.lstrip())]
                output.append(f"{leading}{key}={value}")
                replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{key}={value}")
    return output


def _write_lines(path: Path, lines: list[str], original_text: str) -> None:
    """Write ``lines`` back to ``path``, preserving any trailing newline."""
    newline = "\n" if original_text.endswith(("\n", "\r\n")) else ""
    path.write_text("\n".join(lines) + newline, encoding="utf-8")


def _validate_packet_send_rate(packet_send_rate: int) -> None:
    """Raise ``ValueError`` if ``packet_send_rate`` is outside 1..120."""
    if (
        isinstance(packet_send_rate, bool)
        or packet_send_rate < 1
        or packet_send_rate > 120
    ):
        raise ValueError("packet_send_rate must be between 1 and 120 when enabled")


def _validate_port(port: int) -> None:
    """Raise ``ValueError`` if ``port`` is outside 1..65535."""
    if isinstance(port, bool) or port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")


def _validate_web_port(web_port: int) -> None:
    """Raise ``ValueError`` if ``web_port`` is outside 0..65535."""
    if isinstance(web_port, bool) or web_port < 0 or web_port > 65535:
        raise ValueError("web_port must be between 0 and 65535 (0 disables it)")

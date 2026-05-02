"""Tests for DefaultStatsAPI.ini helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from rlstatsapi.config import (
    DEFAULT_STATS_API_PORT,
    configure_stats_api,
    find_stats_api_config,
    get_stats_api_status,
    set_stats_api_enabled,
    set_stats_api_port,
)


def _write_config(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_find_stats_api_config_explicit_path(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=30\nPort=49123\n")
    assert find_stats_api_config(config_path) == config_path.resolve()


def test_get_stats_api_status_reads_values(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=30\nPort=5000\n")

    status = get_stats_api_status(config_path)

    assert status.found is True
    assert status.enabled is True
    assert status.packet_send_rate == 30
    assert status.port == 5000


def test_get_stats_api_status_missing_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "[TAGame.MatchStatsExporter_TA]\n")

    status = get_stats_api_status(config_path)

    assert status.found is True
    assert status.enabled is False
    assert status.packet_send_rate is None
    assert status.port is None


def test_set_stats_api_enabled_true_writes_positive_rate(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "Port=49123\nPacketSendRate=0\n")

    status = set_stats_api_enabled(True, packet_send_rate=45, path=config_path)

    assert status.enabled is True
    assert status.packet_send_rate == 45
    assert "PacketSendRate=45" in config_path.read_text(encoding="utf-8")


def test_set_stats_api_enabled_false_writes_zero(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=30\nPort=49123\n")

    status = set_stats_api_enabled(False, path=config_path)

    assert status.enabled is False
    assert status.packet_send_rate == 0
    assert "PacketSendRate=0" in config_path.read_text(encoding="utf-8")


def test_set_stats_api_port_preserves_other_content(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    original = (
        "; comment\n"
        "[TAGame.MatchStatsExporter_TA]\n"
        "PacketSendRate=30\n"
        "Port=49123\n"
        "OtherSetting=keepme\n"
    )
    _write_config(config_path, original)

    status = set_stats_api_port(60000, path=config_path)
    updated = config_path.read_text(encoding="utf-8")

    assert status.port == 60000
    assert "OtherSetting=keepme" in updated
    assert "Port=60000" in updated


def test_configure_stats_api_writes_both_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=0\n")

    status = configure_stats_api(
        enabled=True,
        port=DEFAULT_STATS_API_PORT,
        packet_send_rate=60,
        path=config_path,
    )

    assert status.enabled is True
    assert status.port == DEFAULT_STATS_API_PORT
    assert status.packet_send_rate == 60


def test_invalid_packet_send_rate_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=0\nPort=49123\n")

    with pytest.raises(ValueError, match="packet_send_rate"):
        set_stats_api_enabled(True, packet_send_rate=121, path=config_path)


def test_invalid_port_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "DefaultStatsAPI.ini"
    _write_config(config_path, "PacketSendRate=30\nPort=49123\n")

    with pytest.raises(ValueError, match="port"):
        set_stats_api_port(70000, path=config_path)

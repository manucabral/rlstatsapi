from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class EventMessage:
    """Normalized Rocket League Stats API message envelope."""

    event: str
    data: dict[str, Any]
    raw: str | None = None

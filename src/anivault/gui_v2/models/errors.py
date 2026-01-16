"""Error models for GUI v2 operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OperationError:
    """Structured error payload for GUI operations."""

    code: str
    message: str
    detail: str | None = None

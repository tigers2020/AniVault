"""Progress models for GUI v2 operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OperationProgress:
    """Progress payload for long-running operations."""

    current: int
    total: int
    stage: str
    message: str | None = None

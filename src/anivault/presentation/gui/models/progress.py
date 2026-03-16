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


def format_progress_message(progress: OperationProgress) -> str:
    """Format progress for status bar: include percent when total > 0.

    When total > 0, appends (pct%). When total is 0, uses message or current/total
    as-is (e.g. "스캔 중... n개 파일").
    """
    if progress.total > 0:
        pct = round(100 * progress.current / progress.total)
        if progress.message:
            return f"{progress.message} ({pct}%)"
        return f"{progress.current}/{progress.total} ({pct}%)"
    if progress.message:
        return progress.message
    return f"{progress.current}/{progress.total}"

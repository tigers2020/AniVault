"""Ports (Protocol interfaces) for OrganizeUseCase external dependencies.

Defined here so OrganizeUseCase can depend on abstractions, not concrete
core infrastructure.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from anivault.core.models import FileOperation, ScannedFile
    from anivault.core.organizer.executor import OperationResult
    from anivault.config import Settings


@runtime_checkable
class OperationLogger(Protocol):
    """Port: persists an operation plan to a log file."""

    def save_plan(  # type: ignore[empty-body]
        self,
        plan: list[FileOperation],
        base_path: Path | None = None,
    ) -> Path | None:
        """Persist *plan* to a log file under *base_path*.

        Returns the created file Path, or None if logging was skipped/failed.
        """


@runtime_checkable
class OrganizePlanEngine(Protocol):
    """Port: pure organisation computation (plan generation & execution)."""

    def generate_plan(  # type: ignore[empty-body]
        self,
        scanned_files: list[ScannedFile],
        *,
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        """Generate a basic organisation plan."""

    def generate_enhanced_plan(  # type: ignore[empty-body]
        self,
        scanned_files: list[ScannedFile],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        """Generate an enhanced organisation plan with grouping."""

    def execute_plan(  # type: ignore[empty-body]
        self,
        plan: list[FileOperation],
        source_directory: Path,
        *,
        settings: Settings | None = None,
    ) -> list[OperationResult]:
        """Execute *plan* and return per-operation results."""


# ---------------------------------------------------------------------------
# Null / no-op implementations (safe defaults when no adapter is injected)
# ---------------------------------------------------------------------------


class NullOperationLogger:
    """No-op logger — save_plan always returns None without side effects."""

    def save_plan(
        self,
        plan: list[FileOperation],  # noqa: ARG002
        base_path: Path | None = None,  # noqa: ARG002
    ) -> Path | None:
        return None


class NullPlanEngine:
    """No-op plan engine — returns empty results without side effects.

    Used as the default when OrganizeUseCase is constructed without an
    explicit adapter.  Real operations must inject CoreOrganizePlanEngineAdapter
    via the DI container.
    """

    def generate_plan(
        self,
        scanned_files: list[ScannedFile],  # noqa: ARG002
        *,
        settings: Settings | None = None,  # noqa: ARG002
    ) -> list[FileOperation]:
        return []

    def generate_enhanced_plan(
        self,
        scanned_files: list[ScannedFile],  # noqa: ARG002
        destination: str = "Anime",  # noqa: ARG002
    ) -> list[FileOperation]:
        return []

    def execute_plan(
        self,
        plan: list[FileOperation],  # noqa: ARG002
        source_directory: Path,  # noqa: ARG002
        *,
        settings: Settings | None = None,  # noqa: ARG002
    ) -> list[OperationResult]:
        return []

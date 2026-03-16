"""Concrete core adapters for OrganizeUseCase ports.

These adapters wrap the core organizer infrastructure so that the
app layer (OrganizeUseCase) never needs to import core directly.

Only the DI container (anivault.containers) should instantiate these.
"""

from __future__ import annotations

from pathlib import Path

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, ScannedFile
from anivault.core.organizer.executor import OperationResult
from anivault.core.organizer.organize_service import (
    execute_organization_plan as _core_execute_plan,
    generate_enhanced_organization_plan as _core_generate_enhanced_plan,
    generate_organization_plan as _core_generate_plan,
)
from anivault.config import Settings


class CoreOperationLoggerAdapter:
    """Wraps OperationLogManager as the OperationLogger port.

    Args:
        base_path: Default root path for log files.
                   Falls back to Path.cwd() if None.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self._default_base = base_path or Path.cwd()

    def save_plan(
        self,
        plan: list[FileOperation],
        base_path: Path | None = None,
    ) -> Path | None:
        """Persist *plan* via OperationLogManager.

        Returns the created file Path, or None if saving failed.
        """
        try:
            mgr = OperationLogManager(base_path or self._default_base)
            return mgr.save_plan(plan)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            return None


class CoreOrganizePlanEngineAdapter:
    """Wraps core organize_service functions as the OrganizePlanEngine port."""

    def generate_plan(
        self,
        scanned_files: list[ScannedFile],
        *,
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        return _core_generate_plan(scanned_files, settings=settings)

    def generate_enhanced_plan(
        self,
        scanned_files: list[ScannedFile],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        return _core_generate_enhanced_plan(scanned_files, destination=destination)

    def execute_plan(
        self,
        plan: list[FileOperation],
        source_directory: Path,
        *,
        settings: Settings | None = None,
    ) -> list[OperationResult]:
        return _core_execute_plan(plan, source_directory, settings=settings)

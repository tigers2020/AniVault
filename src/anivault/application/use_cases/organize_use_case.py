"""Organize use case (Phase 2 — port-based internalization).

Orchestrates organization pipeline: scan → generate plan → execute plan.

Architecture notes
------------------
* ``scan()`` depends on ``run_pipeline`` directly (core import).
  This is **adapter-allowed exception A**: scan() is a pipeline entry-point,
  and the core dependency is explicitly permitted.  All other public methods
  (generate_plan*, execute_plan, save_plan_log) route through injected ports
  so that ``from anivault.core`` imports are 0 in those paths.

* Real adapters (CoreOperationLoggerAdapter, CoreOrganizePlanEngineAdapter)
  are wired exclusively by the DI container (anivault.containers).
  OrganizeUseCase never instantiates concrete core adapters itself.

* Default port values are NullOperationLogger / NullPlanEngine — no-op
  implementations that are safe for testing without DI.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from anivault.application.ports.organize import (
    NullOperationLogger,
    NullPlanEngine,
    OperationLogger,
    OrganizePlanEngine,
)
from anivault.config import Settings
from anivault.core.models import FileOperation, ScannedFile

# scan() — adapter-allowed exception A: run_pipeline import is intentional.
from anivault.core.pipeline import run_pipeline
from anivault.core.organizer.executor import OperationResult
from anivault.shared.constants import QueueConfig, WorkerConfig
from anivault.application.adapters.metadata import file_metadata_to_parsing_result
from anivault.domain.entities.metadata import FileMetadata


class OrganizeUseCase:
    """Use case for organizing anime files into structured directories.

    All plan generation and execution routes through the injected
    ``plan_engine`` port.  Logging routes through the injected ``logger``
    port.  Both default to no-op implementations; production adapters are
    supplied by the DI container.
    """

    def __init__(
        self,
        *,
        logger: OperationLogger | None = None,
        plan_engine: OrganizePlanEngine | None = None,
    ) -> None:
        self._logger: OperationLogger = logger if logger is not None else NullOperationLogger()
        self._plan_engine: OrganizePlanEngine = plan_engine if plan_engine is not None else NullPlanEngine()

    # ------------------------------------------------------------------
    # Private conversion helpers
    # ------------------------------------------------------------------

    def _scanned_file_from_metadata(self, metadata: FileMetadata) -> ScannedFile:
        """Convert a single FileMetadata to ScannedFile."""
        parsing_result = file_metadata_to_parsing_result(metadata)
        return ScannedFile(
            file_path=metadata.file_path,
            metadata=parsing_result,
        )

    def _scanned_files_from_metadata(self, files: Sequence[FileMetadata]) -> list[ScannedFile]:
        """Convert FileMetadata list to ScannedFile list."""
        return [self._scanned_file_from_metadata(m) for m in files]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        root_path: str | Path,
        extensions: list[str],
        num_workers: int | None = None,
        max_queue_size: int | None = None,
    ) -> list[ScannedFile]:
        """Scan directory and return ScannedFile list.

        adapter-allowed exception A: this method calls run_pipeline (core)
        directly because it is a pipeline entry-point used as a fallback
        when both skip_scan and skip_match are set in RunUseCase.

        Args:
            root_path: Directory to scan
            extensions: File extensions to include
            num_workers: Worker count (default: WorkerConfig.DEFAULT)
            max_queue_size: Queue size (default: QueueConfig.DEFAULT_SIZE)

        Returns:
            List of ScannedFile instances
        """
        file_results: list[FileMetadata] = run_pipeline(
            root_path=str(root_path),
            extensions=extensions,
            num_workers=num_workers or WorkerConfig.DEFAULT,
            max_queue_size=max_queue_size or QueueConfig.DEFAULT_SIZE,
        )
        return self._scanned_files_from_metadata(file_results)

    def generate_plan(
        self,
        scanned_files: list[ScannedFile],
        *,
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        """Generate organization plan.

        Args:
            scanned_files: List of scanned files
            settings: Optional settings override

        Returns:
            List of FileOperation
        """
        return self._plan_engine.generate_plan(scanned_files, settings=settings)

    def generate_enhanced_plan(
        self,
        scanned_files: list[ScannedFile],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        """Generate enhanced organization plan with grouping.

        Args:
            scanned_files: List of scanned files
            destination: Base destination directory name

        Returns:
            List of FileOperation
        """
        return self._plan_engine.generate_enhanced_plan(scanned_files, destination=destination)

    def generate_plan_from_metadata(
        self,
        files: list[FileMetadata],
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        """Generate organization plan from FileMetadata list.

        Args:
            files: List of FileMetadata (e.g. from scan/match results).
            settings: Optional settings override.

        Returns:
            List of FileOperation.
        """
        scanned = self._scanned_files_from_metadata(files)
        return self._plan_engine.generate_plan(scanned, settings=settings)

    def generate_enhanced_plan_from_metadata(
        self,
        files: list[FileMetadata],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        """Generate enhanced organization plan from FileMetadata list.

        Args:
            files: List of FileMetadata (e.g. from scan/match results).
            destination: Base destination directory name.

        Returns:
            List of FileOperation.
        """
        scanned = self._scanned_files_from_metadata(files)
        return self._plan_engine.generate_enhanced_plan(scanned, destination=destination)

    def execute_plan(
        self,
        plan: list[FileOperation],
        source_directory: Path,
        *,
        settings: Settings | None = None,
    ) -> list[OperationResult]:
        """Execute organization plan.

        Args:
            plan: Organization plan
            source_directory: Source directory path
            settings: Optional settings override

        Returns:
            List of move results
        """
        return self._plan_engine.execute_plan(plan, source_directory, settings=settings)

    def save_plan_log(
        self,
        plan: list[FileOperation],
        base_path: Path | None = None,
    ) -> str | None:
        """Persist the operation plan to a log file via the injected logger port.

        R5: Handler layer never imports OperationLogManager (anivault.core) directly.
        Phase 2: direct OperationLogManager import/instantiation removed from this
        method; routing through self._logger (OperationLogger port) instead.

        Args:
            plan:      Organization plan to save.
            base_path: Directory for the log file (defaults to CWD).

        Returns:
            Absolute path of the saved log file as a string, or None on error.
        """
        try:
            saved = self._logger.save_plan(plan, base_path)
            return str(saved) if saved is not None else None
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            return None

"""
Organize Controller Implementation

This module contains the OrganizeController class that manages file organization
operations and coordinates between the UI layer and FileOrganizer service.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QObject, QThread, Signal

from anivault.config import load_settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, ScannedFile
from anivault.core.organizer import FileOrganizer
from anivault.core.organizer.executor import OperationResult
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui.models import FileItem
from anivault.gui.workers.organize_worker import OrganizeWorker
from anivault.shared.metadata_models import FileMetadata, TMDBMatchResult

logger = logging.getLogger(__name__)


class OrganizeController(QObject):
    """
    Controller for file organization operations.

    This class manages file organization workflow, coordinates with FileOrganizer,
    and provides signals for UI communication.
    """

    # Signals for UI communication
    plan_generated: Signal = Signal(list)  # Emits list[FileOperation]
    organization_started: Signal = Signal()  # Emitted when organization starts
    file_organized: Signal = Signal(object)  # Emits OperationResult object (NO dict!)
    organization_progress: Signal = Signal(
        int, str
    )  # Emits (progress %, current filename)
    organization_finished: Signal = Signal(list)  # Emits list[OperationResult]
    organization_error: Signal = Signal(str)  # Emits error message
    organization_cancelled: Signal = Signal()  # Emitted when organization is cancelled

    def __init__(self, parent: QObject | None = None):
        """Initialize the organize controller.

        Args:
            parent: Parent QObject for Qt parent-child relationship
        """
        super().__init__(parent)

        # State
        self.is_organizing = False
        self.current_plan: list[FileOperation] = []

        # Initialize services
        # Use user's home directory for logs
        log_root_path = Path.home()
        self.log_manager = OperationLogManager(log_root_path)

        self.settings = load_settings()
        self.file_organizer = FileOrganizer(self.log_manager, self.settings)

        # Initialize parser for filename parsing
        self.parser = AnitopyParser()

        # Initialize worker thread
        self._organize_thread: QThread | None = None
        self._organize_worker: OrganizeWorker | None = None

        logger.debug("OrganizeController initialized")

    def _convert_fileitems_to_scannedfiles(
        self,
        file_items: list[FileItem] | list[ScannedFile],
    ) -> list[ScannedFile]:
        """Convert FileItem or ScannedFile list to ScannedFile list.

        Args:
            file_items: List of FileItem or ScannedFile objects

        Returns:
            List of ScannedFile objects (only successfully converted items)
        """
        scanned_files: list[ScannedFile] = []
        for item in file_items:
            if isinstance(item, FileItem):
                converted = self._convert_fileitem_to_scannedfile(item)
                if converted:
                    scanned_files.append(converted)
            else:
                scanned_files.append(item)
        return scanned_files

    def _convert_fileitem_to_scannedfile(
        self,
        file_item: FileItem,
    ) -> ScannedFile | None:
        """Convert GUI FileItem to core ScannedFile.

        Args:
            file_item: FileItem from GUI

        Returns:
            ScannedFile for core processing, or None if conversion fails
        """
        try:
            # Check if metadata exists
            if not file_item.metadata:
                logger.debug(
                    "Skipping file without metadata: %s",
                    file_item.file_path.name,
                )
                return None

            # Handle FileMetadata object (new format)
            if isinstance(file_item.metadata, FileMetadata):
                return self._convert_from_file_metadata(file_item)

            # Handle dict format (legacy - for backward compatibility)
            # Note: FileItem.metadata is typed as FileMetadata | None, but dict is accepted for backward compatibility
            if isinstance(file_item.metadata, dict):  # type: ignore[unreachable]
                return self._convert_from_dict(file_item)

            # Unknown metadata type
            logger.warning(
                "Unknown metadata type for %s: %s",
                file_item.file_path.name,
                type(file_item.metadata),
            )
            return None

        except Exception as e:  # noqa: BLE001 - GUI file conversion error fallback
            logger.warning(
                "Failed to convert FileItem to ScannedFile for %s: %s",
                file_item.file_path.name,
                e,
            )
            return None

    def _convert_from_file_metadata(
        self,
        file_item: FileItem,
    ) -> ScannedFile | None:
        """Convert FileItem with FileMetadata to ScannedFile.

        Args:
            file_item: FileItem with FileMetadata

        Returns:
            ScannedFile or None if conversion fails
        """
        # Ensure FileMetadata contains a tmdb_id attribute and it is valid
        tmdb_id = getattr(file_item.metadata, "tmdb_id", None)
        if not tmdb_id:
            logger.debug(
                "Skipping file without TMDB match: %s",
                file_item.file_path.name,
            )
            return None

        # Parse filename and create match result
        season, episode = self._parse_filename(file_item.file_path.name)
        # file_item.metadata is guaranteed to be FileMetadata at this point due to isinstance check
        assert isinstance(file_item.metadata, FileMetadata)
        match_result = self._create_match_result_from_metadata(file_item.metadata)

        # Create ParsingResult and ScannedFile
        additional_info = ParsingAdditionalInfo(match_result=match_result)
        parsing_result = ParsingResult(
            title=match_result.title,
            season=season,
            episode=episode,
            additional_info=additional_info,
        )

        return self._create_scanned_file(file_item.file_path, parsing_result)

    def _convert_from_dict(
        self,
        file_item: FileItem,
    ) -> ScannedFile | None:
        """Convert FileItem with dict metadata to ScannedFile.

        Args:
            file_item: FileItem with dict metadata

        Returns:
            ScannedFile or None if conversion fails
        """
        # Extract match_result (the TMDB matching result)
        # file_item.metadata is guaranteed to be dict at this point due to isinstance check
        # Use cast to inform mypy that metadata is dict here
        metadata_dict = cast("dict[str, Any]", file_item.metadata)
        match_result = metadata_dict.get("match_result")

        if not match_result:
            logger.debug(
                "Skipping file without TMDB match: %s",
                file_item.file_path.name,
            )
            return None

        # Parse filename and get title
        season, episode = self._parse_filename(file_item.file_path.name)
        title = match_result.title if hasattr(match_result, "title") else ""

        # Create ParsingResult and ScannedFile
        additional_info = ParsingAdditionalInfo(match_result=match_result)
        parsing_result = ParsingResult(
            title=title,
            season=season,
            episode=episode,
            additional_info=additional_info,
        )

        return self._create_scanned_file(file_item.file_path, parsing_result)

    def _parse_filename(
        self,
        filename: str,
    ) -> tuple[int | None, int | None]:
        """Parse filename to extract season and episode.

        Args:
            filename: File name to parse

        Returns:
            Tuple of (season, episode) or (None, None) if parsing fails
        """
        try:
            parsed = self.parser.parse(filename)
            return parsed.season, parsed.episode
        except Exception as e:  # noqa: BLE001 - GUI parsing error fallback
            logger.warning(
                "Failed to parse filename %s: %s",
                filename,
                e,
            )
            return None, None

    def _create_match_result_from_metadata(
        self,
        metadata: FileMetadata,
    ) -> TMDBMatchResult:
        """Create TMDBMatchResult from FileMetadata.

        Args:
            metadata: FileMetadata object

        Returns:
            TMDBMatchResult object
        """
        return TMDBMatchResult(
            id=metadata.tmdb_id or 0,
            title=metadata.title or "",
            media_type=metadata.media_type or "tv",
            year=metadata.year,
            genres=metadata.genres,
            overview=metadata.overview,
            vote_average=metadata.vote_average,
            poster_path=metadata.poster_path,
        )

    def _create_scanned_file(
        self,
        file_path: Path,
        parsing_result: ParsingResult,
    ) -> ScannedFile:
        """Create ScannedFile from file path and parsing result.

        Args:
            file_path: Path to the file
            parsing_result: ParsingResult object

        Returns:
            ScannedFile object
        """
        file_size = file_path.stat().st_size if file_path.exists() else 0
        last_modified = file_path.stat().st_mtime if file_path.exists() else 0.0

        return ScannedFile(
            file_path=file_path,
            metadata=parsing_result,
            file_size=file_size,
            last_modified=last_modified,
        )

    def organize_files(
        self,
        file_items: list[FileItem] | list[ScannedFile],
        dry_run: bool = True,
    ) -> None:
        """Start file organization process.

        Args:
            file_items: List of FileItem or ScannedFile objects to organize
            dry_run: If True, generate plan only without executing
        """
        if self.is_organizing:
            logger.warning("Organization already in progress")
            return

        if not file_items:
            logger.warning("No files to organize")
            self.organization_error.emit("정리할 파일이 없습니다.")
            return

        # Convert FileItems to ScannedFiles if needed
        scanned_files = self._convert_fileitems_to_scannedfiles(file_items)

        if not scanned_files:
            logger.warning("No valid files to organize after conversion")
            self.organization_error.emit("정리할 파일이 없습니다.")
            return

        logger.info(
            "Starting file organization for %d files (dry_run=%s)",
            len(scanned_files),
            dry_run,
        )

        try:
            # Generate organization plan
            plan = self.file_organizer.generate_plan(scanned_files)

            if not plan:
                logger.info(
                    "No files need organizing (all files already in correct locations)",
                )
                self.organization_error.emit("모든 파일이 이미 올바른 위치에 있습니다.")
                return

            logger.info("Generated organization plan with %d operations", len(plan))
            self.current_plan = plan

            # Emit plan for preview
            self.plan_generated.emit(plan)

            # If not dry_run, execute the plan
            if not dry_run:
                self._execute_organization_plan(plan)

        except Exception as e:
            logger.exception("Failed to organize files")
            self.organization_error.emit(f"파일 정리 실패: {e}")

    def _generate_and_execute_plan(
        self,
        scanned_files: list[ScannedFile],
        dry_run: bool,
    ) -> None:
        """Generate organization plan and execute if not dry_run.

        Args:
            scanned_files: List of ScannedFile objects to organize
            dry_run: If True, generate plan only without executing
        """
        # Generate organization plan
        plan = self.file_organizer.generate_plan(scanned_files)

        if not plan:
            logger.info(
                "No files need organizing (all files already in correct locations)",
            )
            self.organization_error.emit("모든 파일이 이미 올바른 위치에 있습니다.")
            return

        logger.info("Generated organization plan with %d operations", len(plan))
        self.current_plan = plan

        # Emit plan for preview
        self.plan_generated.emit(plan)

        # If not dry_run, execute the plan
        if not dry_run:
            self._execute_organization_plan(plan)

    def _execute_organization_plan(self, plan: list[FileOperation]) -> None:
        """Execute the organization plan in a background thread.

        Args:
            plan: List of FileOperation objects to execute
        """
        # Cleanup previous worker if exists
        if self._organize_thread and self._organize_thread.isRunning():
            logger.warning("Previous organization still running, stopping it first")
            self.cancel_organization()
            self._organize_thread.wait()

        # Create new thread and worker
        self._organize_thread = QThread()
        self._organize_worker = OrganizeWorker()

        # Set plan and services
        self._organize_worker.set_plan(plan)
        self._organize_worker.set_services(self.log_manager, self.file_organizer)

        # Move worker to thread
        self._organize_worker.moveToThread(self._organize_thread)

        # Connect worker signals to controller signals (relay to UI)
        self._organize_worker.organization_started.connect(self._on_worker_started)
        self._organize_worker.file_organized.connect(self.file_organized.emit)
        self._organize_worker.organization_progress.connect(
            self.organization_progress.emit,
        )
        self._organize_worker.organization_finished.connect(self._on_worker_finished)
        self._organize_worker.organization_error.connect(self.organization_error.emit)
        self._organize_worker.organization_cancelled.connect(
            self.organization_cancelled.emit,
        )

        # Connect thread signals
        self._organize_thread.started.connect(self._organize_worker.run)
        self._organize_thread.finished.connect(self._cleanup_worker)

        # Start the thread
        logger.info("Starting organization worker thread for %d operations", len(plan))
        self._organize_thread.start()

    def _on_worker_started(self) -> None:
        """Handle worker started signal."""
        self.is_organizing = True
        self.organization_started.emit()

    def _on_worker_finished(self, results: list[OperationResult]) -> None:
        """Handle worker finished signal.

        Args:
            results: List of operation results (NO Any!)
        """
        self.is_organizing = False
        self.organization_finished.emit(results)
        logger.info("File organization completed: %d files moved", len(results))

        # Stop the thread
        if self._organize_thread:
            self._organize_thread.quit()

    def _cleanup_worker(self) -> None:
        """Clean up worker and thread after completion."""
        if self._organize_worker:
            self._organize_worker.deleteLater()
            self._organize_worker = None

        if self._organize_thread:
            self._organize_thread.deleteLater()
            self._organize_thread = None

        logger.debug("OrganizeWorker cleaned up")

    def cancel_organization(self) -> None:
        """Cancel ongoing file organization."""
        if self.is_organizing and self._organize_worker:
            logger.info("Cancelling file organization")
            self._organize_worker.cancel()
            # Note: is_organizing will be set to False in _on_worker_finished

    def get_current_plan(self) -> list[FileOperation]:
        """Get the current organization plan.

        Returns:
            List of FileOperation objects
        """
        return self.current_plan

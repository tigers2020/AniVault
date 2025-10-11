"""
Organize Controller Implementation

This module contains the OrganizeController class that manages file organization
operations and coordinates between the UI layer and FileOrganizer service.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import ScannedFile
from anivault.core.organizer import FileOrganizer
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingResult
from anivault.gui.models import FileItem
from anivault.gui.workers.organize_worker import OrganizeWorker

logger = logging.getLogger(__name__)


class OrganizeController(QObject):
    """
    Controller for file organization operations.

    This class manages file organization workflow, coordinates with FileOrganizer,
    and provides signals for UI communication.
    """

    # Signals for UI communication
    plan_generated = Signal(list)  # FileOperation list
    organization_started = Signal()
    file_organized = Signal(dict)  # operation result
    organization_progress = Signal(int, str)  # (progress %, current filename)
    organization_finished = Signal(list)  # results
    organization_error = Signal(str)  # error message
    organization_cancelled = Signal()

    def __init__(self, parent: QObject | None = None):
        """Initialize the organize controller.

        Args:
            parent: Parent QObject for Qt parent-child relationship
        """
        super().__init__(parent)

        # State
        self.is_organizing = False
        self.current_plan: list[Any] = []

        # Initialize services
        # Use user's home directory for logs
        log_root_path = Path.home()
        self.log_manager = OperationLogManager(log_root_path)
        from anivault.config.settings import load_settings

        self.settings = load_settings()
        self.file_organizer = FileOrganizer(self.log_manager, self.settings)

        # Initialize parser for filename parsing
        self.parser = AnitopyParser()

        # Initialize worker thread
        self._organize_thread: QThread | None = None
        self._organize_worker: OrganizeWorker | None = None

        logger.debug("OrganizeController initialized")

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
            # FileItem.metadata is stored as dict by StateModel.set_file_metadata()
            if not file_item.metadata or not isinstance(file_item.metadata, dict):
                # No metadata - skip this file
                logger.debug(
                    "Skipping file without metadata: %s",
                    file_item.file_path.name,
                )
                return None

            # Extract match_result (the TMDB matching result)
            match_result = file_item.metadata.get("match_result")

            if not match_result:
                # No TMDB match - skip this file
                logger.debug(
                    "Skipping file without TMDB match: %s",
                    file_item.file_path.name,
                )
                return None

            # Parse filename to get season/episode info
            # (This info is not stored in FileItem.metadata)
            try:
                parsed = self.parser.parse(file_item.file_path.name)
                season = parsed.season
                episode = parsed.episode
            except Exception as e:  # noqa: BLE001 - GUI parsing error fallback
                logger.warning(
                    "Failed to parse filename %s: %s",
                    file_item.file_path.name,
                    e,
                )
                season = None
                episode = None

            # Get title from match_result (MatchResult dataclass)
            title = match_result.title

            # Create ParsingResult with match_result in other_info
            parsing_result = ParsingResult(
                title=title,
                season=season,
                episode=episode,
                other_info={"match_result": match_result},
            )

            # Create ScannedFile
            scanned_file = ScannedFile(
                file_path=file_item.file_path,
                metadata=parsing_result,
                file_size=(
                    file_item.file_path.stat().st_size
                    if file_item.file_path.exists()
                    else 0
                ),
                last_modified=(
                    file_item.file_path.stat().st_mtime
                    if file_item.file_path.exists()
                    else 0.0
                ),
            )

            return scanned_file

        except Exception as e:  # noqa: BLE001 - GUI file conversion error fallback
            logger.warning(
                "Failed to convert FileItem to ScannedFile for %s: %s",
                file_item.file_path.name,
                e,
            )
            return None

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
        scanned_files: list[ScannedFile] = []
        for item in file_items:
            if isinstance(item, FileItem):
                converted = self._convert_fileitem_to_scannedfile(item)
                if converted:
                    scanned_files.append(converted)
            else:
                scanned_files.append(item)

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

    def _execute_organization_plan(self, plan: list[Any]) -> None:
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

    def _on_worker_finished(self, results: list[Any]) -> None:
        """Handle worker finished signal.

        Args:
            results: List of moved files
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

    def get_current_plan(self) -> list[Any]:
        """Get the current organization plan.

        Returns:
            List of FileOperation objects
        """
        return self.current_plan

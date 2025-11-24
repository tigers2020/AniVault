"""
Organize Worker for AniVault GUI

This module contains the worker class that handles background file organization
operations using PySide6's QThread and signal/slot mechanism.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation
from anivault.core.organizer import FileOrganizer
from anivault.core.organizer.executor import OperationResult

logger = logging.getLogger(__name__)


class OrganizeWorker(QObject):
    """
    Worker class for file organization operations in the background.

    This class runs in a separate thread and uses signals to communicate
    with the main GUI thread for thread-safe updates during file operations.
    """

    # Signals for communication with main thread
    organization_started: Signal = Signal()  # Emitted when organization starts
    file_organized: Signal = Signal(object)  # Emits OperationResult object (NO dict!)
    organization_progress: Signal = Signal(int, str)  # Emits (progress %, current filename)
    organization_finished: Signal = Signal(list)  # Emits list[OperationResult]
    organization_error: Signal = Signal(str)  # Emits error message
    organization_cancelled: Signal = Signal()  # Emitted when cancelled

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the organize worker.

        Args:
            parent: Parent QObject for Qt parent-child relationship
        """
        super().__init__(parent)

        self._cancelled = False
        self._plan: list[FileOperation] = []
        self._log_manager: OperationLogManager | None = None
        self._file_organizer: FileOrganizer | None = None

        logger.debug("OrganizeWorker initialized")

    def set_plan(self, plan: list[FileOperation]) -> None:
        """Set the organization plan to execute.

        Args:
            plan: List of FileOperation objects
        """
        self._plan = plan
        logger.debug("Organization plan set with %d operations", len(plan))

    def set_services(
        self,
        log_manager: OperationLogManager,
        file_organizer: FileOrganizer,
    ) -> None:
        """Set the service instances to use.

        Args:
            log_manager: OperationLogManager instance
            file_organizer: FileOrganizer instance
        """
        self._log_manager = log_manager
        self._file_organizer = file_organizer
        logger.debug("Services set for OrganizeWorker")

    def run(self) -> None:
        """Execute the organization plan in background thread.

        This method is called when the worker thread starts.
        It performs file organization and emits signals for progress updates.
        """
        if not self._plan:
            logger.warning("No plan to execute")
            self.organization_error.emit("정리 계획이 없습니다.")
            return

        if not self._file_organizer or not self._log_manager:
            logger.error("Services not set")
            self.organization_error.emit("서비스가 초기화되지 않았습니다.")
            return

        self._cancelled = False
        self.organization_started.emit()

        try:
            total_operations = len(self._plan)
            operation_results = []  # list[OperationResult]
            operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            logger.info(
                "Starting file organization: %d operations (ID: %s)",
                total_operations,
                operation_id,
            )

            # Execute all operations in batch for better performance
            try:
                # Execute all operations at once
                batch_results = self._file_organizer.execute_plan(self._plan)
                operation_results.extend(batch_results)

                # Emit progress for each completed operation
                for idx, result in enumerate(batch_results):
                    # Check cancellation
                    if self._cancelled:
                        logger.info("Organization cancelled by user")
                        self.organization_cancelled.emit()
                        return

                    # Emit signal for each file
                    self.file_organized.emit(result)

                    if result.success:
                        logger.debug(
                            "Organized: %s -> %s",
                            result.source_path,
                            result.destination_path,
                        )
                    else:
                        logger.warning(
                            "Failed to organize: %s -> %s (error: %s)",
                            result.source_path,
                            result.destination_path,
                            result.message,
                        )

                    # Update progress
                    progress = int((idx + 1) * 100 / total_operations)
                    current_filename = Path(result.source_path).name
                    self.organization_progress.emit(progress, current_filename)

            # pylint: disable-next=broad-exception-caught

            # pylint: disable-next=broad-exception-caught

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception("Failed to execute batch operations")
                # Create failure results for all remaining operations
                for idx, operation in enumerate(self._plan):
                    if self._cancelled:
                        logger.info("Organization cancelled by user")
                        self.organization_cancelled.emit()
                        return

                    failure_result = OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                    operation_results.append(failure_result)
                    self.file_organized.emit(failure_result)

                    # Update progress
                    progress = int((idx + 1) * 100 / total_operations)
                    current_filename = operation.source_path.name
                    self.organization_progress.emit(progress, current_filename)

            # Cleanup empty directories after organization
            moved_files = [(r.source_path, r.destination_path) for r in operation_results if r.success and not r.skipped]
            if moved_files:
                self._cleanup_empty_directories(moved_files)

            # Emit completion with OperationResult objects
            self.organization_finished.emit(operation_results)
            logger.info(
                "File organization completed: %d/%d files moved",
                len([r for r in operation_results if r.success]),
                total_operations,
            )

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Error during file organization")
            self.organization_error.emit(f"정리 중 오류 발생: {e}")

    def cancel(self) -> None:
        """Cancel the ongoing organization operation."""
        logger.info("Cancelling file organization")
        self._cancelled = True

    def _cleanup_empty_directories(self, moved_files: list[tuple[str, str]]) -> None:
        """Remove empty directories after file organization.

        IMPORTANT: This method preserves the source root directory.
        Only subdirectories that become empty after file organization are removed.

        Args:
            moved_files: List of (source_path, destination_path) tuples
        """
        if not moved_files:
            logger.debug("No moved files, skipping directory cleanup")
            return

        logger.info("Starting directory cleanup for %d moved files", len(moved_files))

        # Determine source root directory (the common root to preserve)
        # Use the first file's parent directory as a reference point
        first_source = Path(moved_files[0][0])
        source_root = first_source.parent

        # Find the actual source root by checking all files
        for source_path, _ in moved_files:
            current_parent = Path(source_path).parent
            # Find common ancestor
            while source_root not in current_parent.parents and source_root != current_parent:
                if source_root.parent == source_root:  # Reached filesystem root
                    break
                source_root = source_root.parent

        logger.info("Source root directory (will be preserved): %s", source_root)

        # Collect unique source directories and their parents (excluding source root)
        source_dirs: set[Path] = set()
        for source_path, _ in moved_files:
            source_dir = Path(source_path).parent

            # Add this directory and parent directories up to (but not including) source root
            current_dir = source_dir
            depth = 0
            max_depth = 10  # Reasonable nesting limit

            while current_dir and depth < max_depth:
                # Stop if we reached the source root
                if current_dir == source_root:
                    logger.debug("Reached source root, stopping: %s", current_dir)
                    break

                # Stop at filesystem root
                if current_dir.parent == current_dir:
                    break

                source_dirs.add(current_dir)
                logger.debug("Collected dir (depth %d): %s", depth, current_dir)

                current_dir = current_dir.parent
                depth += 1

        logger.info(
            "Found %d unique directories to check (excluding source root)",
            len(source_dirs),
        )

        # Sort directories by depth (deepest first) for bottom-up removal
        sorted_dirs = sorted(source_dirs, key=lambda p: len(p.parts), reverse=True)

        removed_count = 0
        skipped_count = 0
        for directory in sorted_dirs:
            try:
                # Skip if directory doesn't exist
                if not directory.exists():
                    logger.debug("Directory doesn't exist (already removed?): %s", directory)
                    skipped_count += 1
                    continue

                # Check if directory is empty
                contents = list(directory.iterdir())
                if not contents:
                    # Remove empty directory
                    directory.rmdir()
                    removed_count += 1
                    logger.debug("✅ Removed empty directory: %s", directory)
                else:
                    logger.debug(
                        "Directory not empty (%d items), skipping: %s",
                        len(contents),
                        directory,
                    )
                    skipped_count += 1

            except OSError as e:
                # Log but don't fail on cleanup errors
                logger.warning("Failed to remove directory %s: %s", directory, e)
                skipped_count += 1
                continue

        logger.info(
            "Directory cleanup complete: %d removed, %d skipped",
            removed_count,
            skipped_count,
        )

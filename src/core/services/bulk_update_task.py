"""Bulk update task for data synchronization workflows.

This module provides optimized bulk update operations to eliminate N+1 query patterns
in data synchronization and file processing workflows.
"""

from __future__ import annotations

import logging
from typing import Any

from ..database import AnimeMetadata, DatabaseManager, ParsedFile
from .file_pipeline_worker import WorkerTask

# Logger for this module
logger = logging.getLogger(__name__)


class ConcreteBulkUpdateTask(WorkerTask):
    """Concrete task for performing bulk updates on database records.

    This task eliminates N+1 query patterns by collecting updates
    and applying them in optimized batch operations.
    """

    def __init__(
        self,
        update_type: str,
        updates: list[dict[str, Any]],
        db_manager: DatabaseManager | None = None,
        progress_callback: Any | None = None,
    ) -> None:
        """Initialize the bulk update task.

        Args:
            update_type: Type of update ('anime_metadata', 'parsed_files', 'generic')
            updates: List of update dictionaries
            db_manager: Database manager instance
            progress_callback: Optional callback for progress updates
        """
        self.update_type = update_type
        self.updates = updates
        self.db_manager = db_manager
        self.progress_callback = progress_callback
        self._updated_count = 0

    def execute(self) -> int:
        """Execute the bulk update operation.

        Returns:
            Number of records updated
        """
        if not self.updates:
            logger.warning("No updates provided for bulk update task")
            return 0

        if not self.db_manager:
            raise ValueError("Database manager is required for bulk update operations")

        logger.info(f"Starting bulk update for {len(self.updates)} {self.update_type} records")

        try:
            if self.update_type == "anime_metadata":
                self._updated_count = self._bulk_update_anime_metadata()
            elif self.update_type == "parsed_files":
                self._updated_count = self._bulk_update_parsed_files()
            elif self.update_type == "generic":
                self._updated_count = self._bulk_update_generic()
            else:
                raise ValueError(f"Unsupported update type: {self.update_type}")

            logger.info(f"Bulk update completed: {self._updated_count} records updated")
            return self._updated_count

        except Exception as e:
            logger.error(f"Bulk update failed: {e}", exc_info=True)
            raise

    def _bulk_update_anime_metadata(self) -> int:
        """Perform bulk update on anime metadata records.

        Returns:
            Number of records updated
        """
        # Group updates by operation type for optimization
        status_updates = []
        general_updates = []

        for update_dict in self.updates:
            if "status" in update_dict and len(update_dict) == 2:  # Only status update
                status_updates.append(update_dict)
            else:
                general_updates.append(update_dict)

        total_updated = 0

        # Handle status-only updates efficiently
        if status_updates:
            # Group by status value
            status_groups = {}
            for update in status_updates:
                tmdb_id = update.get("tmdb_id")
                status = update.get("status")
                if tmdb_id and status:
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(tmdb_id)

            # Perform bulk status updates
            for status, tmdb_ids in status_groups.items():
                updated_count = self.db_manager.bulk_update_anime_metadata_by_status(
                    tmdb_ids, status
                )
                total_updated += updated_count

        # Handle general updates using bulk_update_mappings
        if general_updates:
            updated_count = self.db_manager.bulk_update_anime_metadata(general_updates)
            total_updated += updated_count

        return total_updated

    def _bulk_update_parsed_files(self) -> int:
        """Perform bulk update on parsed files records.

        Returns:
            Number of records updated
        """
        # Group updates by operation type for optimization
        status_updates = []
        general_updates = []

        for update_dict in self.updates:
            if "is_processed" in update_dict and len(update_dict) == 2:  # Only status update
                status_updates.append(update_dict)
            else:
                general_updates.append(update_dict)

        total_updated = 0

        # Handle status-only updates efficiently
        if status_updates:
            # Group by processing status
            status_groups = {}
            for update in status_updates:
                file_path = update.get("file_path")
                is_processed = update.get("is_processed")
                if file_path and is_processed is not None:
                    if is_processed not in status_groups:
                        status_groups[is_processed] = []
                    status_groups[is_processed].append(file_path)

            # Perform bulk status updates
            for is_processed, file_paths in status_groups.items():
                updated_count = self.db_manager.bulk_update_parsed_files_by_status(
                    file_paths, is_processed
                )
                total_updated += updated_count

        # Handle general updates using bulk_update_mappings
        if general_updates:
            updated_count = self.db_manager.bulk_update_parsed_files(general_updates)
            total_updated += updated_count

        return total_updated

    def _bulk_update_generic(self) -> int:
        """Perform generic bulk update using flexible conditions.

        Returns:
            Number of records updated
        """
        # Determine table class and condition field from first update
        if not self.updates:
            return 0

        first_update = self.updates[0]

        # Determine table class based on update fields
        if "tmdb_id" in first_update:
            table_class = AnimeMetadata
            condition_field = "tmdb_id"
        elif "file_path" in first_update:
            table_class = ParsedFile
            condition_field = "file_path"
        else:
            raise ValueError("Cannot determine table class from update data")

        return self.db_manager.bulk_update_with_conditions(
            table_class, self.updates, condition_field
        )

    def get_name(self) -> str:
        """Get task name."""
        return f"Bulk Update ({self.update_type})"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Updating {len(self.updates)} {self.update_type} records in bulk"

    def get_updated_count(self) -> int:
        """Get the number of records updated."""
        return self._updated_count

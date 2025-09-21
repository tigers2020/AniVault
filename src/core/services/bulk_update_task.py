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
        """Execute the bulk update operation with comprehensive error handling.

        This method orchestrates the bulk update process with the following features:

        1. Input Validation:
           - Verifies that updates are provided
           - Ensures database manager is available
           - Validates update type compatibility

        2. Update Type Routing:
           - Routes to specialized update methods based on update_type
           - Supports 'anime_metadata', 'parsed_files', and 'generic' types
           - Provides clear error messages for unsupported types

        3. Error Management:
           - Comprehensive exception handling with detailed logging
           - Re-raises exceptions for upstream error handling
           - Maintains operation integrity through proper error propagation

        4. Progress Tracking:
           - Logs operation start and completion
           - Reports the number of records updated
           - Provides detailed progress information for monitoring

        Returns:
            int: Number of records successfully updated. Returns 0 if no updates
                were provided or if the operation fails.

        Raises:
            ValueError: If database manager is not provided or update type is
                unsupported. This ensures proper configuration validation.
            Exception: Any database or processing errors are re-raised for
                upstream error handling and logging.
        """

    def _bulk_update_anime_metadata(self) -> int:
        """Perform bulk update on anime metadata records with optimization strategies.

        This method implements a two-phase optimization strategy for updating anime
        metadata records:

        Phase 1 - Status-Only Updates:
        - Groups updates that only modify the status field by status value
        - Uses bulk_update_anime_metadata_by_status for maximum efficiency
        - Reduces database round trips by batching identical status updates

        Phase 2 - General Updates:
        - Handles complex updates with multiple field changes
        - Uses bulk_update_anime_metadata for flexible field updates
        - Maintains data integrity while supporting diverse update patterns

        The optimization strategy significantly reduces database load by minimizing
        the number of individual UPDATE statements, particularly for status-only
        changes which are common in metadata synchronization workflows.

        Returns:
            int: Total number of records updated across both optimization phases.

        Note:
            Updates are processed in order of efficiency, with status-only updates
            handled first to maximize the benefits of bulk operations.
        """

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

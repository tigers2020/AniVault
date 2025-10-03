"""
Rollback management for AniVault file operations.

This module provides functionality to generate rollback plans from operation logs,
allowing users to reverse file organization operations.
"""

from pathlib import Path

from .log_manager import LogFileNotFoundError, OperationLogManager
from .models import FileOperation


class RollbackManager:
    """
    Manages rollback operations for AniVault file operations.

    This class provides functionality to generate rollback plans from operation logs,
    allowing users to reverse file organization operations by creating counter-operations
    that swap source and destination paths.
    """

    def __init__(self, log_manager: OperationLogManager) -> None:
        """
        Initialize the RollbackManager.

        Args:
            log_manager: Instance of OperationLogManager for loading operation logs.
        """
        self.log_manager = log_manager

    def generate_rollback_plan(self, log_path: str) -> list[FileOperation]:
        """
        Generate a rollback plan from an operation log file.

        This method loads the operation log and creates a rollback plan by:
        1. Loading the original operations from the log file
        2. Creating counter-operations with swapped source and destination paths
        3. Reversing the order to ensure LIFO (Last-In, First-Out) execution

        Args:
            log_path: Path to the operation log file to generate rollback from.

        Returns:
            List of FileOperation objects representing the rollback plan.

        Raises:
            LogFileNotFoundError: If the specified log file does not exist.
        """
        try:
            # Load the operation log using the OperationLogManager
            operations = self.log_manager.load_plan(Path(log_path))

            # Create rollback plan by reversing operations
            rollback_plan = []

            # Iterate through the loaded operations and create counter-operations
            for operation in operations:
                # Create a new FileOperation with swapped source and destination paths
                rollback_operation = FileOperation(
                    operation_type=operation.operation_type,  # Keep the same operation type
                    source_path=operation.destination_path,  # Original destination becomes source
                    destination_path=operation.source_path,  # Original source becomes destination
                )
                rollback_plan.append(rollback_operation)

            # Reverse the order to ensure LIFO (Last-In, First-Out) execution
            # This ensures that the last operation performed is the first to be rolled back
            rollback_plan.reverse()

            return rollback_plan

        except FileNotFoundError:
            # Re-raise as LogFileNotFoundError for consistent error handling
            raise LogFileNotFoundError(Path(log_path))

"""
Unit tests for RollbackManager.

This module tests the functionality of the RollbackManager class,
including successful plan generation and error handling.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.log_manager import LogFileNotFoundError
from anivault.core.models import FileOperation, OperationType
from anivault.core.rollback_manager import RollbackManager


class TestRollbackManager:
    """Test cases for RollbackManager functionality."""

    def test_init(self):
        """Test RollbackManager initialization."""
        mock_log_manager = Mock()
        rollback_manager = RollbackManager(mock_log_manager)

        assert rollback_manager.log_manager is mock_log_manager

    def test_generate_rollback_plan_success(self):
        """Test successful rollback plan generation."""
        # Create mock operations
        mock_operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/file1.mkv"),
                destination_path=Path("/dest/file1.mkv"),
            ),
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/file2.mp4"),
                destination_path=Path("/dest/file2.mp4"),
            ),
        ]

        # Create mock log manager
        mock_log_manager = Mock()
        mock_log_manager.load_plan.return_value = mock_operations

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Generate rollback plan
        rollback_plan = rollback_manager.generate_rollback_plan("/path/to/log.json")

        # Verify the plan
        assert len(rollback_plan) == 2

        # Check that operations are reversed (LIFO order)
        # First operation should be the last original operation
        assert rollback_plan[0].operation_type == OperationType.MOVE
        assert rollback_plan[0].source_path == Path("/dest/file2.mp4")
        assert rollback_plan[0].destination_path == Path("/source/file2.mp4")

        # Second operation should be the first original operation
        assert rollback_plan[1].operation_type == OperationType.MOVE
        assert rollback_plan[1].source_path == Path("/dest/file1.mkv")
        assert rollback_plan[1].destination_path == Path("/source/file1.mkv")

        # Verify that load_plan was called with the correct path
        mock_log_manager.load_plan.assert_called_once_with(Path("/path/to/log.json"))

    def test_generate_rollback_plan_empty_operations(self):
        """Test rollback plan generation with empty operations list."""
        # Create mock log manager with empty operations
        mock_log_manager = Mock()
        mock_log_manager.load_plan.return_value = []

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Generate rollback plan
        rollback_plan = rollback_manager.generate_rollback_plan("/path/to/log.json")

        # Verify the plan is empty
        assert rollback_plan == []

    def test_generate_rollback_plan_log_file_not_found(self):
        """Test rollback plan generation when log file is not found."""
        # Create mock log manager that raises FileNotFoundError
        mock_log_manager = Mock()
        mock_log_manager.load_plan.side_effect = FileNotFoundError("File not found")

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Test that LogFileNotFoundError is raised
        with pytest.raises(LogFileNotFoundError) as exc_info:
            rollback_manager.generate_rollback_plan("/nonexistent/log.json")

        # Verify the error message
        assert "Log file not found" in str(exc_info.value)
        assert exc_info.value.log_path == Path("/nonexistent/log.json")

    def test_generate_rollback_plan_different_operation_types(self):
        """Test rollback plan generation with different operation types."""
        # Create mock operations with different types
        mock_operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/move_file.mkv"),
                destination_path=Path("/dest/move_file.mkv"),
            ),
            FileOperation(
                operation_type=OperationType.COPY,
                source_path=Path("/source/copy_file.mp4"),
                destination_path=Path("/dest/copy_file.mp4"),
            ),
        ]

        # Create mock log manager
        mock_log_manager = Mock()
        mock_log_manager.load_plan.return_value = mock_operations

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Generate rollback plan
        rollback_plan = rollback_manager.generate_rollback_plan("/path/to/log.json")

        # Verify the plan
        assert len(rollback_plan) == 2

        # Check that operation types are preserved
        assert rollback_plan[0].operation_type == OperationType.COPY
        assert rollback_plan[1].operation_type == OperationType.MOVE

    def test_generate_rollback_plan_path_swapping(self):
        """Test that source and destination paths are correctly swapped."""
        # Create mock operations
        mock_operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/original/source/path/file.mkv"),
                destination_path=Path("/original/dest/path/file.mkv"),
            ),
        ]

        # Create mock log manager
        mock_log_manager = Mock()
        mock_log_manager.load_plan.return_value = mock_operations

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Generate rollback plan
        rollback_plan = rollback_manager.generate_rollback_plan("/path/to/log.json")

        # Verify that paths are swapped
        assert len(rollback_plan) == 1
        assert rollback_plan[0].source_path == Path("/original/dest/path/file.mkv")
        assert rollback_plan[0].destination_path == Path(
            "/original/source/path/file.mkv"
        )

    def test_generate_rollback_plan_lifo_order(self):
        """Test that rollback operations are in LIFO (Last-In, First-Out) order."""
        # Create mock operations with multiple files
        mock_operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/first.mkv"),
                destination_path=Path("/dest/first.mkv"),
            ),
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/second.mkv"),
                destination_path=Path("/dest/second.mkv"),
            ),
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=Path("/source/third.mkv"),
                destination_path=Path("/dest/third.mkv"),
            ),
        ]

        # Create mock log manager
        mock_log_manager = Mock()
        mock_log_manager.load_plan.return_value = mock_operations

        # Create rollback manager
        rollback_manager = RollbackManager(mock_log_manager)

        # Generate rollback plan
        rollback_plan = rollback_manager.generate_rollback_plan("/path/to/log.json")

        # Verify the plan is in reverse order (LIFO)
        assert len(rollback_plan) == 3

        # First rollback operation should be for the last original operation
        assert "third.mkv" in str(rollback_plan[0].source_path)
        assert "first.mkv" in str(rollback_plan[2].source_path)

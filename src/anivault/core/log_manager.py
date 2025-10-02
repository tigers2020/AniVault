"""
Operation log management for AniVault.

This module provides functionality to save and load operation logs,
which are essential for dry-run previews and rollback capabilities.
"""

import json
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError, parse_obj_as

from .models import FileOperation


class LogFileNotFoundError(Exception):
    """Raised when a requested log file cannot be found."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        super().__init__(f"Log file not found: {log_path}")


class LogFileCorruptedError(Exception):
    """Raised when a log file exists but cannot be parsed."""

    def __init__(self, log_path: Path, reason: str) -> None:
        self.log_path = log_path
        self.reason = reason
        super().__init__(f"Log file corrupted: {log_path} - {reason}")


class OperationLogManager:
    """
    Manages operation logs for AniVault file operations.

    This class handles the serialization and deserialization of file
    operation plans, storing them in timestamped JSON files within
    the `.anivault/logs` directory.
    """

    def __init__(self, root_path: Path) -> None:
        """
        Initialize the OperationLogManager.

        Args:
            root_path: Root path of the project where `.anivault` directory resides.
        """
        self.root_path = Path(root_path)
        self.logs_dir = self.root_path / ".anivault" / "logs"

    def save_plan(self, plan: list[FileOperation]) -> Path:
        """
        Save a list of file operations to a timestamped log file.

        Args:
            plan: List of FileOperation objects to save.

        Returns:
            Path to the created log file.

        Raises:
            OSError: If the log directory cannot be created or file cannot be written.
        """
        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp string in YYYYMMDD-HHMMSS format
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # Construct log file path
        log_filename = f"organize-{timestamp}.json"
        log_path = self.logs_dir / log_filename

        # Serialize the plan to JSON
        try:
            # Convert FileOperation objects to dictionaries
            plan_data = [operation.model_dump() for operation in plan]

            # Ensure paths are serialized as strings
            for operation_data in plan_data:
                operation_data["source_path"] = str(operation_data["source_path"])
                operation_data["destination_path"] = str(
                    operation_data["destination_path"],
                )

            # Write to file
            with log_path.open("w", encoding="utf-8") as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)

            return log_path

        except (OSError, json.JSONEncodeError) as e:
            raise OSError(f"Failed to save operation log to {log_path}: {e}") from e

    def load_plan(self, log_path: Path) -> list[FileOperation]:
        """
        Load a list of file operations from a log file.

        Args:
            log_path: Path to the log file to load.

        Returns:
            List of FileOperation objects.

        Raises:
            LogFileNotFoundError: If the log file does not exist.
            LogFileCorruptedError: If the log file cannot be parsed.
        """
        if not log_path.exists():
            raise LogFileNotFoundError(log_path)

        try:
            # Read JSON content
            with log_path.open("r", encoding="utf-8") as f:
                plan_data = json.load(f)

            # Deserialize to FileOperation objects
            operations = parse_obj_as(list[FileOperation], plan_data)
            return operations

        except FileNotFoundError:
            raise LogFileNotFoundError(log_path)
        except (json.JSONDecodeError, ValidationError) as e:
            raise LogFileCorruptedError(log_path, str(e)) from e

    def list_logs(self) -> list[Path]:
        """
        List all available operation log files.

        Returns:
            List of Path objects for available log files, sorted by creation time (newest first).
        """
        if not self.logs_dir.exists():
            return []

        # Find all JSON files that match the organize-*.json pattern
        log_files = [
            path for path in self.logs_dir.glob("organize-*.json") if path.is_file()
        ]

        # Sort by modification time (newest first)
        return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)

    def get_log_by_id(self, log_id: str) -> Path:
        """
        Find a log file by its ID (timestamp part).

        Args:
            log_id: The timestamp ID of the log file (e.g., "20231027-153000").

        Returns:
            Path to the matching log file.

        Raises:
            LogFileNotFoundError: If no log file with the given ID is found.
        """
        expected_filename = f"organize-{log_id}.json"
        log_path = self.logs_dir / expected_filename

        if not log_path.exists():
            raise LogFileNotFoundError(log_path)

        return log_path

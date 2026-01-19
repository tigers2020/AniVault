"""
Operation log management for AniVault.

This module provides functionality to save and load operation logs,
which are essential for dry-run previews and auditability.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError, parse_obj_as

from anivault.shared.constants import CLI, Encoding, FileSystem, Logging

from .models import FileOperation


class LogFileNotFoundError(Exception):
    """Raised when a requested log file cannot be found."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        msg = f"Log file not found: {log_path}"
        super().__init__(msg)


class LogFileCorruptedError(Exception):
    """Raised when a log file exists but cannot be parsed."""

    def __init__(self, log_path: Path, reason: str) -> None:
        self.log_path = log_path
        self.reason = reason
        msg = f"Log file corrupted: {log_path} - {reason}"
        super().__init__(msg)


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
        self.logs_dir = self.root_path / FileSystem.HOME_DIR / "logs"

    def save_plan(self, plan: list[FileOperation]) -> Path:
        """
        Save a list of file operations to a timestamped log file.

        This method orchestrates the saving process by delegating to
        specialized methods.

        Args:
            plan: List of FileOperation objects to save.

        Returns:
            Path to the created log file.

        Raises:
            OSError: If the log directory cannot be created or file cannot be written.
        """
        # Ensure logs directory exists
        self._ensure_logs_directory()

        # Generate log file path
        log_path = self._generate_log_file_path()

        # Serialize plan data
        plan_data = self._serialize_plan_data(plan)

        # Write to file
        self._write_log_file(log_path, plan_data)

        return log_path

    def _ensure_logs_directory(self) -> None:
        """Ensure the logs directory exists.

        Raises:
            OSError: If directory creation fails
        """
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _generate_log_file_path(self) -> Path:
        """Generate a timestamped log file path.

        Returns:
            Path object for the log file
        """
        timestamp = self._get_timestamp()
        log_filename = f"{Logging.ORGANIZE_LOG_PREFIX}{timestamp}{Logging.FILE_EXTENSION}"
        return self.logs_dir / log_filename

    def _get_timestamp(self) -> str:
        """Generate timestamp string in YYYYMMDD-HHMMSS format.

        Returns:
            Timestamp string
        """
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def _serialize_plan_data(self, plan: list[FileOperation]) -> list[dict[str, Any]]:
        """Serialize FileOperation objects to dictionaries.

        Args:
            plan: List of FileOperation objects to serialize

        Returns:
            List of dictionaries representing the operations

        Raises:
            json.JSONEncodeError: If serialization fails
        """
        # Convert FileOperation objects to dictionaries using asdict for dataclass
        plan_data = [asdict(operation) for operation in plan]

        # Ensure paths are serialized as strings
        for operation_data in plan_data:
            operation_data["source_path"] = str(operation_data["source_path"])
            operation_data["destination_path"] = str(operation_data["destination_path"])

        return plan_data

    def _write_log_file(self, log_path: Path, plan_data: list[dict[str, Any]]) -> None:
        """Write serialized plan data to log file.

        Args:
            log_path: Path to the log file
            plan_data: Serialized plan data to write

        Raises:
            OSError: If file writing fails
        """
        try:
            with log_path.open("w", encoding=Encoding.DEFAULT) as f:
                json.dump(plan_data, f, indent=CLI.INDENT_SIZE, ensure_ascii=False)
        except (OSError, json.JSONDecodeError) as e:
            msg = f"Failed to save operation log to {log_path}: {e}"
            raise OSError(msg) from e

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
            with log_path.open("r", encoding=Encoding.DEFAULT) as f:
                plan_data = json.load(f)

            # Deserialize to FileOperation objects
            operations: list[FileOperation] = parse_obj_as(
                list[FileOperation],
                plan_data,
            )
            return operations

        except FileNotFoundError as e:
            raise LogFileNotFoundError(log_path) from e
        except (json.JSONDecodeError, ValidationError) as e:
            raise LogFileCorruptedError(log_path, str(e)) from e

    def list_logs(self) -> list[Path]:
        """
        List all available operation log files.

        Returns:
            List of Path objects for available log files, sorted by
            creation time (newest first).
        """
        if not self.logs_dir.exists():
            return []

        # Find all JSON files that match the organize-*.json pattern
        log_files = [
            path
            for path in self.logs_dir.glob(
                f"{Logging.ORGANIZE_LOG_PREFIX}*{Logging.FILE_EXTENSION}",
            )
            if path.is_file()
        ]

        # Sort by modification time (newest first)
        return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)

    def get_log_identifiers(self) -> list[str]:
        """
        Get a list of log identifiers (timestamps) from available log files.

        Returns:
            List of log identifiers sorted by creation time (newest first).
        """
        log_files = self.list_logs()
        identifiers = []

        for log_file in log_files:
            # Extract timestamp from filename
            # (e.g., "organize-20231027-153000.json" -> "20231027-153000")
            filename = log_file.name
            if filename.startswith(Logging.ORGANIZE_LOG_PREFIX) and filename.endswith(Logging.FILE_EXTENSION):
                timestamp = filename[len(Logging.ORGANIZE_LOG_PREFIX) : -len(Logging.FILE_EXTENSION)]  # Remove prefix and suffix
                identifiers.append(timestamp)

        return identifiers

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
        expected_filename = f"{Logging.ORGANIZE_LOG_PREFIX}{log_id}{Logging.FILE_EXTENSION}"
        log_path = self.logs_dir / expected_filename

        if not log_path.exists():
            raise LogFileNotFoundError(log_path)

        return log_path

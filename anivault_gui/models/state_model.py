"""State model for the AniVault GUI application.

This module contains the StateModel class that manages the application's
shared state, decoupled from the UI components.
"""

from pathlib import Path
from typing import Any, Optional


class StateModel:
    """Central repository for application data and state management.

    This class manages the shared state of the GUI application,
    keeping it decoupled from the UI components.
    """

    def __init__(self) -> None:
        """Initialize the state model with default values."""
        self.selected_directory: Optional[Path] = None
        self.scanned_files: list[dict[str, Any]] = []
        self.api_key: Optional[str] = None
        self.current_operation: Optional[str] = None
        self.is_scanning: bool = False
        self.is_matching: bool = False
        self.is_organizing: bool = False

    def set_selected_directory(self, directory: Path) -> None:
        """Set the selected directory for file operations.

        Args:
            directory: Path to the selected directory
        """
        self.selected_directory = directory
        self.scanned_files.clear()  # Clear previous scan results

    def add_scanned_file(self, file_info: dict[str, Any]) -> None:
        """Add a scanned file to the list.

        Args:
            file_info: Dictionary containing file information
        """
        self.scanned_files.append(file_info)

    def set_api_key(self, api_key: str) -> None:
        """Set the TMDB API key.

        Args:
            api_key: The TMDB API key
        """
        self.api_key = api_key

    def set_operation_status(self, operation: str, is_running: bool) -> None:
        """Set the status of a specific operation.

        Args:
            operation: The operation name (scanning, matching, organizing)
            is_running: Whether the operation is currently running
        """
        if operation == "scanning":
            self.is_scanning = is_running
        elif operation == "matching":
            self.is_matching = is_running
        elif operation == "organizing":
            self.is_organizing = is_running

        if is_running:
            self.current_operation = operation
        else:
            self.current_operation = None

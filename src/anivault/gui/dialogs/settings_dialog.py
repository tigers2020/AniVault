"""
Settings Dialog for API Key Management

This module contains the SettingsDialog class for managing TMDB API key
configuration in the AniVault GUI application.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from anivault.config.auto_scanner import AutoScanner
from anivault.config.folder_validator import FolderValidator
from anivault.config import Settings, get_config, update_and_save_config
from anivault.shared.constants.gui_constants import (
    DialogConstants,
)
from anivault.shared.constants.gui_messages import DialogMessages, DialogTitles
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
)

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Settings dialog for API key management.

    This dialog provides a modal interface for users to input and save
    their TMDB API key, integrating with the AniVault configuration system.
    """

    # Signals
    api_key_saved: Signal = Signal(str)  # Emitted when API key is successfully saved
    folder_settings_changed: Signal = (
        Signal()
    )  # Emitted when folder settings are changed

    def __init__(
        self,
        parent: QWidget | None = None,
        config_path: str | Path = "config/config.toml",
    ):
        """
        Initialize the settings dialog.

        Args:
            parent: Parent widget
            config_path: Path to configuration file
        """
        super().__init__(parent)

        self.config_path = Path(config_path)
        self.current_api_key = ""
        self._cached_config: Settings | None = None  # Cache for loaded config

        # Initialize auto scanner
        self.auto_scanner = AutoScanner(self.config_path)

        # Set dialog properties
        self.setWindowTitle(DialogConstants.DIALOG_TITLE)
        self.setModal(True)
        self.setFixedSize(DialogConstants.DIALOG_WIDTH, DialogConstants.DIALOG_HEIGHT)

        # Initialize UI
        self._setup_ui()
        self._load_current_config()

        logger.info("SettingsDialog initialized")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # API Key tab
        self._setup_api_tab()

        # Folder Settings tab
        self._setup_folder_tab()

        layout.addWidget(self.tab_widget)

        # Button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        # Connect buttons directly to avoid double signal emission
        self.button_box.button(QDialogButtonBox.StandardButton.Save).clicked.connect(
            self._save_settings,
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(
            self.reject,
        )

        layout.addWidget(self.button_box)

    def _setup_api_tab(self) -> None:
        """Set up the API Key tab."""
        api_tab = QWidget()
        layout = QVBoxLayout(api_tab)

        # Form layout for API key input
        form_layout = QFormLayout()

        # API Key label and input
        self.api_key_label = QLabel("TMDB API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your TMDB API key")

        # Set font to monospace for better readability
        font = QFont()
        font.setFamily("Consolas, Monaco, monospace")
        self.api_key_input.setFont(font)

        form_layout.addRow(self.api_key_label, self.api_key_input)

        # Info label
        info_label = QLabel(
            "Get your API key from: https://www.themoviedb.org/settings/api",
        )
        info_label.setWordWrap(True)
        info_label.setObjectName("infoLabel")

        layout.addLayout(form_layout)
        layout.addWidget(info_label)
        layout.addStretch()

        self.tab_widget.addTab(api_tab, "API Key")

    def _setup_folder_tab(self) -> None:
        """Set up the Folder Settings tab."""
        folder_tab = QWidget()
        layout = QVBoxLayout(folder_tab)

        # Source Folder Group
        source_group = QGroupBox("Source Folder")
        source_layout = QFormLayout(source_group)

        self.source_folder_input = QLineEdit()
        self.source_folder_input.setPlaceholderText(
            "Select source folder for media files",
        )
        self.source_folder_btn = QPushButton("Browse...")
        self.source_folder_btn.clicked.connect(self._browse_source_folder)

        source_row_layout = QHBoxLayout()
        source_row_layout.addWidget(self.source_folder_input)
        source_row_layout.addWidget(self.source_folder_btn)
        source_layout.addRow("Source Folder:", source_row_layout)

        # Target Folder Group
        target_group = QGroupBox("Target Folder")
        target_layout = QFormLayout(target_group)

        self.target_folder_input = QLineEdit()
        self.target_folder_input.setPlaceholderText(
            "Select target folder for organized files",
        )
        self.target_folder_btn = QPushButton("Browse...")
        self.target_folder_btn.clicked.connect(self._browse_target_folder)

        target_row_layout = QHBoxLayout()
        target_row_layout.addWidget(self.target_folder_input)
        target_row_layout.addWidget(self.target_folder_btn)
        target_layout.addRow("Target Folder:", target_row_layout)

        # Resolution-based organization
        self.organize_by_resolution_checkbox = QCheckBox(
            "Organize by resolution (1080p, 720p, etc.)",
        )
        self.organize_by_resolution_checkbox.setChecked(False)
        target_layout.addRow(self.organize_by_resolution_checkbox)

        # Year-based organization
        self.organize_by_year_checkbox = QCheckBox(
            "Organize by release year (2013, 2020, etc.)",
        )
        self.organize_by_year_checkbox.setChecked(False)
        target_layout.addRow(self.organize_by_year_checkbox)

        # Auto Scan Group
        auto_scan_group = QGroupBox("Auto Scan Settings")
        auto_scan_layout = QFormLayout(auto_scan_group)

        self.auto_scan_startup_checkbox = QCheckBox("Scan source folder on startup")
        self.auto_scan_interval_spinbox = QSpinBox()
        self.auto_scan_interval_spinbox.setRange(0, 1440)
        self.auto_scan_interval_spinbox.setSuffix(" minutes")
        self.auto_scan_interval_spinbox.setSpecialValueText("Disabled")
        self.auto_scan_interval_spinbox.setValue(0)

        self.include_subdirs_checkbox = QCheckBox("Include subdirectories")
        self.include_subdirs_checkbox.setChecked(True)

        auto_scan_layout.addRow(self.auto_scan_startup_checkbox)
        auto_scan_layout.addRow("Scan Interval:", self.auto_scan_interval_spinbox)
        auto_scan_layout.addRow(self.include_subdirs_checkbox)

        # Add groups to layout
        layout.addWidget(source_group)
        layout.addWidget(target_group)
        layout.addWidget(auto_scan_group)
        layout.addStretch()

        self.tab_widget.addTab(folder_tab, "Folders")

    def _load_current_config(self) -> None:
        """Load current configuration and populate the form."""
        try:
            # Load config only once and cache it
            if self._cached_config is None:
                self._cached_config = get_config()

            if self._cached_config.tmdb.api_key:
                self.current_api_key = self._cached_config.tmdb.api_key
                self.api_key_input.setText(self._cached_config.tmdb.api_key)
                logger.debug("Loaded existing API key from configuration")

            # Load folder settings
            if (
                hasattr(self._cached_config, "folders")
                and self._cached_config.folders is not None
            ):
                folders = self._cached_config.folders
                self.source_folder_input.setText(folders.source_folder)
                self.target_folder_input.setText(folders.target_folder)
                self.organize_by_resolution_checkbox.setChecked(
                    folders.organize_by_resolution,
                )
                self.organize_by_year_checkbox.setChecked(
                    folders.organize_by_year,
                )
                self.auto_scan_startup_checkbox.setChecked(folders.auto_scan_on_startup)
                self.auto_scan_interval_spinbox.setValue(
                    folders.auto_scan_interval_minutes,
                )
                self.include_subdirs_checkbox.setChecked(folders.include_subdirectories)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning("Failed to load current configuration: %s", e)
            # Continue with empty form

    def _save_settings(self) -> None:
        """Save the settings and close the dialog."""
        api_key = self.api_key_input.text().strip()

        # Validate API key
        if not api_key:
            self._show_error(
                DialogTitles.API_KEY_REQUIRED,
                DialogMessages.API_KEY_REQUIRED,
            )
            return

        if len(api_key) < 10:
            self._show_error(
                DialogTitles.INVALID_API_KEY,
                DialogMessages.API_KEY_TOO_SHORT,
            )
            return

        try:
            # Save API key to configuration
            self._save_api_key_to_config(api_key)

            # Save folder settings
            self._save_folder_settings()

            # Emit signals
            self.api_key_saved.emit(api_key)
            self.folder_settings_changed.emit()

            # Show success message with .env file notice
            success_message = (
                f"{DialogMessages.API_KEY_SAVED}\n\n"
                "🔒 보안 알림: API 키는 .env 파일에 안전하게 저장되었습니다.\n"
                "(config.toml에는 저장되지 않음)"
            )
            QMessageBox.information(
                self,
                DialogTitles.SETTINGS_SAVED,
                success_message,
            )

            # Close dialog
            self.accept()

        except Exception as e:
            logger.exception("Failed to save API key: %s")
            self._show_error(
                DialogTitles.SAVE_FAILED,
                DialogMessages.SETTINGS_SAVE_FAILED.format(error=e),
            )

    def _save_api_key_to_config(self, api_key: str) -> None:
        """
        Save API key to .env file (SECURE).

        API keys are stored in .env file for security, not in config.toml.
        This prevents accidental commits of sensitive information.

        Args:
            api_key: The API key to save

        Raises:
            AniVaultError: If saving fails
        """
        try:
            # 1. Save to .env file (SECURE)
            self._save_api_key_to_env_file(api_key)

            # 2. Update memory cache (for current session)
            def update_api_key(cfg: Settings) -> None:
                cfg.tmdb.api_key = api_key

            # Note: This updates memory only, NOT saved to config.toml
            # to_toml_file() excludes api_key for security
            update_and_save_config(update_api_key, self.config_path)

            logger.info("API key saved successfully to .env file")

        except (OSError, PermissionError) as e:
            logger.exception("Failed to save API key")
            raise AniVaultError(
                ErrorCode.VALIDATION_ERROR,
                f"Failed to save API key: {e!s}",
                ErrorContext(operation="save_api_key"),
            ) from e

    def _save_api_key_to_env_file(
        self,
        api_key: str,
        env_file_path: Path | None = None,
    ) -> None:
        """
        Save API key to .env file.

        Args:
            api_key: The API key to save
            env_file_path: Optional custom .env file path (for testing)

        Raises:
            OSError: If file write fails
        """

        env_file = env_file_path if env_file_path is not None else Path(".env")
        env_lines = []

        # Read existing .env file if it exists
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                env_lines = f.readlines()

        # Update or add TMDB_API_KEY
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("TMDB_API_KEY="):
                env_lines[i] = f"TMDB_API_KEY={api_key}\n"
                found = True
                break

        if not found:
            env_lines.append(f"TMDB_API_KEY={api_key}\n")

        # Write back to .env file
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(env_lines)

        # Set environment variable for current process
        os.environ["TMDB_API_KEY"] = api_key

        logger.info("API key saved to .env file")

    def _show_error(self, title: str, message: str) -> None:
        """
        Show error message dialog.

        Args:
            title: Error dialog title
            message: Error message
        """
        QMessageBox.critical(self, title, message)

    def _browse_source_folder(self) -> None:
        """Browse for source folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Source Folder",
            self.source_folder_input.text() or str(Path.home()),
        )
        if folder:
            # Validate the folder
            is_valid, error = FolderValidator.validate_folder_path(folder)
            if is_valid:
                self.source_folder_input.setText(folder)
            else:
                self._show_error(
                    "Invalid Folder",
                    f"Cannot use selected folder: {error}",
                )

    def _browse_target_folder(self) -> None:
        """Browse for target folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Target Folder",
            self.target_folder_input.text() or str(Path.home()),
        )
        if folder:
            # Validate the folder (target can be created if not exists)
            is_valid, error = FolderValidator.validate_target_folder(folder)
            if is_valid:
                self.target_folder_input.setText(folder)
            else:
                self._show_error(
                    "Invalid Folder",
                    f"Cannot use selected folder: {error}",
                )

    def _save_folder_settings(self) -> None:
        """Save folder settings to configuration."""
        try:
            source_folder = self.source_folder_input.text().strip()
            target_folder = self.target_folder_input.text().strip()
            organize_by_resolution = self.organize_by_resolution_checkbox.isChecked()
            organize_by_year = self.organize_by_year_checkbox.isChecked()
            auto_scan_startup = self.auto_scan_startup_checkbox.isChecked()
            auto_scan_interval = self.auto_scan_interval_spinbox.value()
            include_subdirs = self.include_subdirs_checkbox.isChecked()

            # Update folder settings using auto scanner
            success, error = self.auto_scanner.update_folder_settings(
                source_folder=source_folder,
                target_folder=target_folder,
                organize_by_resolution=organize_by_resolution,
                organize_by_year=organize_by_year,
                auto_scan_on_startup=auto_scan_startup,
                auto_scan_interval_minutes=auto_scan_interval,
                include_subdirectories=include_subdirs,
            )

            if not success:
                msg = f"Failed to update folder settings: {error}"
                raise ValueError(msg)

            logger.info("Folder settings saved successfully")

        except Exception as e:
            logger.exception("Failed to save folder settings: %s")
            raise AniVaultError(
                ErrorCode.VALIDATION_ERROR,
                f"Failed to save folder settings: {e!s}",
                ErrorContext(operation="save_folder_settings"),
            ) from e

    def get_api_key(self) -> str:
        """
        Get the current API key from the input field.

        Returns:
            Current API key string
        """
        return self.api_key_input.text().strip()

    def get_folder_settings(self) -> dict[str, Any]:
        """
        Get current folder settings.

        Returns:
            dict: Folder settings dictionary
        """
        return {
            "source_folder": self.source_folder_input.text().strip(),
            "destination_folder": self.target_folder_input.text().strip(),
            "organize_by_resolution": self.organize_by_resolution_checkbox.isChecked(),
            "organize_by_year": self.organize_by_year_checkbox.isChecked(),
        }

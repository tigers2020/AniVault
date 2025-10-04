"""Main window implementation for AniVault GUI application.

This module contains the MainWindow class that serves as the root container
for all UI elements using PySide6 QMainWindow.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..models.state_model import StateModel


class MainWindow(QMainWindow):
    """Main application window class.

    This class represents the main GUI window and handles the
    basic window properties and layout structure using PySide6.
    """

    def __init__(
        self, state_model: StateModel, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the main application window.

        Args:
            state_model: The application state model
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.state_model = state_model

        self._setup_window()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._create_layout()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.setWindowTitle("AniVault")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(800, 600)

        # Set window icon (placeholder)
        # self.setWindowIcon(QIcon("icon.ico"))

    def _create_menu_bar(self) -> None:
        """Create the main menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Select Directory action
        select_dir_action = QAction("&Select Directory...", self)
        select_dir_action.setShortcut("Ctrl+O")
        select_dir_action.setStatusTip("Select directory to scan")
        select_dir_action.triggered.connect(self._on_select_directory)
        file_menu.addAction(select_dir_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        # Settings action
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.setStatusTip("Open settings dialog")
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)

        # Match Files action
        match_action = QAction("&Match Files", self)
        match_action.setShortcut("Ctrl+M")
        match_action.setStatusTip("Match files with TMDB")
        match_action.triggered.connect(self._on_match_files)
        tools_menu.addAction(match_action)

        # Organize Files action
        organize_action = QAction("&Organize Files", self)
        organize_action.setShortcut("Ctrl+G")
        organize_action.setStatusTip("Organize files")
        organize_action.triggered.connect(self._on_organize_files)
        tools_menu.addAction(organize_action)

        # Rollback action
        rollback_action = QAction("&Rollback", self)
        rollback_action.setShortcut("Ctrl+R")
        rollback_action.setStatusTip("Rollback last operation")
        rollback_action.triggered.connect(self._on_rollback)
        tools_menu.addAction(rollback_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        # Show Logs action
        logs_action = QAction("&Show Logs", self)
        logs_action.setStatusTip("Show application logs")
        logs_action.triggered.connect(self._on_show_logs)
        help_menu.addAction(logs_action)

        # About action
        about_action = QAction("&About", self)
        about_action.setStatusTip("About AniVault")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """Create the main toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        # Select Directory action
        select_dir_action = QAction("📁 Select Directory", self)
        select_dir_action.setStatusTip("Select directory to scan")
        select_dir_action.triggered.connect(self._on_select_directory)
        toolbar.addAction(select_dir_action)

        toolbar.addSeparator()

        # Match Files action
        match_action = QAction("🔍 Match Files", self)
        match_action.setStatusTip("Match files with TMDB")
        match_action.triggered.connect(self._on_match_files)
        toolbar.addAction(match_action)

        # Organize Files action
        organize_action = QAction("📋 Organize Files", self)
        organize_action.setStatusTip("Organize files")
        organize_action.triggered.connect(self._on_organize_files)
        toolbar.addAction(organize_action)

        # Rollback action
        rollback_action = QAction("↶ Rollback", self)
        rollback_action.setStatusTip("Rollback last operation")
        rollback_action.triggered.connect(self._on_rollback)
        toolbar.addAction(rollback_action)

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Add permanent widgets to status bar
        self.operation_label = QLabel("Idle")
        self.status_bar.addPermanentWidget(self.operation_label)

    def _create_layout(self) -> None:
        """Create the main layout structure with dockable widgets."""

        # Create File Explorer dock widget
        self.file_explorer_dock = QDockWidget("File Explorer", self)
        file_explorer_widget = QWidget()
        file_explorer_layout = QVBoxLayout(file_explorer_widget)

        # Create tree view for file explorer
        self.file_tree = QTreeView()
        file_explorer_layout.addWidget(self.file_tree)

        # Add placeholder label
        placeholder_label = QLabel(
            "File Explorer\n\nSelect a directory to scan for anime files."
        )
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("color: #666; font-style: italic;")
        file_explorer_layout.addWidget(placeholder_label)

        self.file_explorer_dock.setWidget(file_explorer_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_explorer_dock)

        # Create Log Console dock widget
        self.log_console_dock = QDockWidget("Log Console", self)
        log_console_widget = QWidget()
        log_console_layout = QVBoxLayout(log_console_widget)

        # Create text edit for logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_console_layout.addWidget(self.log_text)

        # Add placeholder text
        self.log_text.append("AniVault GUI started successfully.")
        self.log_text.append("Select a directory to begin scanning for anime files.")

        self.log_console_dock.setWidget(log_console_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_console_dock)

        # Create Main Work Area (central widget)
        main_work_widget = QWidget()
        main_work_layout = QVBoxLayout(main_work_widget)

        # Add placeholder content
        main_label = QLabel(
            "Main Work Area\n\nThis area will display scanned files and their details."
        )
        main_label.setAlignment(Qt.AlignCenter)
        main_label.setStyleSheet("color: #666; font-size: 14px; font-style: italic;")
        main_work_layout.addWidget(main_label)

        self.setCentralWidget(main_work_widget)

        # Set dock widget properties
        self.file_explorer_dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable,
        )
        self.log_console_dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable,
        )

    # Event handlers (placeholder implementations)
    def _on_select_directory(self) -> None:
        """Handle directory selection."""
        self.status_bar.showMessage("Directory selection not yet implemented")
        self.log_text.append("Directory selection clicked")

    def _on_settings(self) -> None:
        """Handle settings dialog."""
        self.status_bar.showMessage("Settings dialog not yet implemented")
        self.log_text.append("Settings dialog clicked")

    def _on_match_files(self) -> None:
        """Handle file matching."""
        self.status_bar.showMessage("File matching not yet implemented")
        self.log_text.append("Match files clicked")

    def _on_organize_files(self) -> None:
        """Handle file organization."""
        self.status_bar.showMessage("File organization not yet implemented")
        self.log_text.append("Organize files clicked")

    def _on_rollback(self) -> None:
        """Handle rollback operation."""
        self.status_bar.showMessage("Rollback not yet implemented")
        self.log_text.append("Rollback clicked")

    def _on_show_logs(self) -> None:
        """Handle show logs."""
        self.status_bar.showMessage("Show logs not yet implemented")
        self.log_text.append("Show logs clicked")

    def _on_about(self) -> None:
        """Handle about dialog."""
        self.status_bar.showMessage("About dialog not yet implemented")
        self.log_text.append("About dialog clicked")

"""Signal Connection Coordinator.

This module provides SignalCoordinator, which centrally manages all signal
connections between MainWindow and its components (StateModel, Controllers, Views).

Design Pattern:
    - Follows the manager pattern for centralized signal management
    - Groups signal connections by component for clarity
    - Provides connect_all() for initialization and disconnect_all() for cleanup
    - Does NOT inherit from QObject as it only manages connections

Usage:
    Signal connections are organized into logical groups:
    - StateModel signals (2): files_updated, file_status_changed
    - View signals (1): groupSelected
    - ScanController signals (5): scan_started, scan_progress, etc.
    - TMDBController signals (7): matching_started, file_matched, etc.
    - OrganizeController signals (1): plan_generated

Example:
    >>> coordinator = SignalCoordinator(main_window)
    >>> coordinator.connect_all()
    >>> # Later, when cleaning up:
    >>> coordinator.disconnect_all()
"""

from __future__ import annotations

from anivault.gui.main_window import MainWindow


class SignalCoordinator:
    """Centrally manages signal connections for MainWindow.

    This class extracts signal connection logic from MainWindow to improve
    organization and maintainability. All signal connections are grouped by
    component for clarity.

    Attributes:
        _main_window: Reference to the parent MainWindow
        _connections: List of active signal connections for cleanup

    Signal Groups:
        - StateModel (2 signals)
        - View widgets (1 signal)
        - ScanController (5 signals)
        - TMDBController (7 signals)
        - OrganizeController (1 signal)

    Total: 16 signal connections
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize SignalCoordinator.

        Args:
            main_window: Parent MainWindow instance containing all components
        """
        self._main_window = main_window
        self._connections: list[tuple[object, ...]] = []

    def connect_all(self) -> None:
        """Connect all signals from components to MainWindow handlers.

        This is the main entry point that MainWindow should call during
        initialization to establish all signal connections.

        Signal connections are grouped by component:
        - StateModel: Application state changes
        - View: User interactions in UI
        - Controllers: Business logic events
        """
        self._connect_state_signals()
        self._connect_view_signals()
        self._connect_scan_controller()
        self._connect_tmdb_controller()
        self._connect_organize_controller()

    def disconnect_all(self) -> None:
        """Disconnect all signal connections.

        This method should be called during MainWindow cleanup to properly
        disconnect all signals and prevent memory leaks.
        """
        # Note: In PySide6, disconnecting is typically automatic when objects
        # are destroyed, but explicit disconnect can be used if needed.
        # For now, we keep this as a placeholder for future cleanup needs.

    def _connect_state_signals(self) -> None:
        """Connect StateModel signals to MainWindow handlers.

        StateModel signals notify MainWindow of changes to application state
        such as file updates and status changes.

        Signals:
            - files_updated: Emitted when file list changes
            - file_status_changed: Emitted when a file's status changes
        """
        self._main_window.state_model.files_updated.connect(
            self._main_window.on_files_updated,
        )
        self._main_window.state_model.file_status_changed.connect(
            self._main_window.on_file_status_changed,
        )

    def _connect_view_signals(self) -> None:
        """Connect View widget signals to MainWindow handlers.

        View signals notify MainWindow of user interactions with UI components.

        Signals:
            - groupSelected: Emitted when user selects a group in the grid view
        """
        self._main_window.group_view.groupSelected.connect(
            self._main_window.on_group_selected,
        )

    def _connect_scan_controller(self) -> None:
        """Connect ScanController signals to ScanEventHandler.

        ScanController signals are now handled by a dedicated ScanEventHandler
        instance instead of MainWindow methods, providing better separation of
        concerns and testability.

        Signals:
            - scan_started: Scanning begins
            - scan_progress: Scanning progress update
            - scan_finished: Scanning completes successfully
            - scan_error: Scanning encounters an error
            - files_grouped: Files have been grouped
        """
        handler = self._main_window.scan_event_handler

        self._main_window.scan_controller.scan_started.connect(
            handler.on_scan_started,
        )
        self._main_window.scan_controller.scan_progress.connect(
            handler.on_scan_progress,
        )
        self._main_window.scan_controller.scan_finished.connect(
            handler.on_scan_finished,
        )
        self._main_window.scan_controller.scan_error.connect(
            handler.on_scan_error,
        )
        self._main_window.scan_controller.files_grouped.connect(
            handler.on_files_grouped,
        )
        # Also connect to MainWindow for TMDB auto-start orchestration
        self._main_window.scan_controller.files_grouped.connect(
            self._main_window.on_files_grouped,
        )

    def _connect_tmdb_controller(self) -> None:
        """Connect TMDBController signals to TMDBEventHandler.

        TMDBController signals are now handled by a dedicated TMDBEventHandler
        instance instead of MainWindow methods, providing better separation of
        concerns and testability.

        Signals:
            - matching_started: TMDB matching begins
            - file_matched: A file has been matched
            - matching_progress: Matching progress update
            - matching_finished: Matching completes successfully
            - matching_error: Matching encounters an error
            - matching_cancelled: Matching is cancelled by user
            - cache_stats_updated: Cache statistics have changed (still handled by MainWindow)
        """
        handler = self._main_window.tmdb_event_handler

        self._main_window.tmdb_controller.matching_started.connect(
            handler.on_tmdb_matching_started,
        )
        self._main_window.tmdb_controller.file_matched.connect(
            handler.on_tmdb_file_matched,
        )
        self._main_window.tmdb_controller.matching_progress.connect(
            handler.on_tmdb_matching_progress,
        )
        self._main_window.tmdb_controller.matching_finished.connect(
            handler.on_tmdb_matching_finished,
        )
        self._main_window.tmdb_controller.matching_error.connect(
            handler.on_tmdb_matching_error,
        )
        self._main_window.tmdb_controller.matching_cancelled.connect(
            handler.on_tmdb_matching_cancelled,
        )
        # Cache stats still handled by MainWindow (not event-driven UI update)
        self._main_window.tmdb_controller.cache_stats_updated.connect(
            self._main_window.update_cache_status,
        )

    def _connect_organize_controller(self) -> None:
        """Connect OrganizeController signals to OrganizeEventHandler.

        OrganizeController signals are now handled by a dedicated OrganizeEventHandler
        instance instead of MainWindow methods, providing better separation of
        concerns and testability.

        Signals:
            - plan_generated: Organization plan has been generated
            - organization_started: Organization execution begins
            - file_organized: A file has been organized
            - organization_progress: Organization progress update
            - organization_finished: Organization completes successfully
            - organization_error: Organization encounters an error
            - organization_cancelled: Organization is cancelled by user
        """
        handler = self._main_window.organize_event_handler

        self._main_window.organize_controller.plan_generated.connect(
            handler.on_plan_generated,
        )
        self._main_window.organize_controller.organization_started.connect(
            handler.on_organization_started,
        )
        self._main_window.organize_controller.file_organized.connect(
            handler.on_file_organized,
        )
        self._main_window.organize_controller.organization_progress.connect(
            handler.on_organization_progress,
        )
        self._main_window.organize_controller.organization_finished.connect(
            handler.on_organization_finished,
        )
        self._main_window.organize_controller.organization_error.connect(
            handler.on_organization_error,
        )
        self._main_window.organize_controller.organization_cancelled.connect(
            handler.on_organization_cancelled,
        )

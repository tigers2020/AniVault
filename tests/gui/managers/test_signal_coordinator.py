"""Unit tests for SignalCoordinator.

This module tests SignalCoordinator functionality including:
- Signal connection setup
- Proper handler mapping
- Connection grouping by component
"""

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, call

import pytest
from PySide6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from anivault.gui.managers.signal_coordinator import SignalCoordinator

if TYPE_CHECKING:
    from anivault.gui.main_window import MainWindow


@pytest.fixture
def main_window_with_components(qtbot: QtBot) -> QMainWindow:
    """Create a QMainWindow with mocked components for testing.

    Args:
        qtbot: PyTest-Qt fixture for Qt testing

    Returns:
        QMainWindow instance with mocked state_model, controllers, and views
    """
    window = QMainWindow()
    qtbot.addWidget(window)

    # Mock components
    window.state_model = Mock()  # type: ignore
    window.group_view = Mock()  # type: ignore
    window.scan_controller = Mock()  # type: ignore
    window.tmdb_controller = Mock()  # type: ignore
    window.organize_controller = Mock()  # type: ignore

    # Mock handler methods
    window.on_files_updated = Mock()  # type: ignore
    window.on_file_status_changed = Mock()  # type: ignore
    window.on_group_selected = Mock()  # type: ignore
    window.on_scan_started = Mock()  # type: ignore
    window.on_scan_progress = Mock()  # type: ignore
    window.on_scan_finished = Mock()  # type: ignore
    window.on_scan_error = Mock()  # type: ignore
    window.on_files_grouped = Mock()  # type: ignore
    window.on_tmdb_matching_started = Mock()  # type: ignore
    window.on_tmdb_file_matched = Mock()  # type: ignore
    window.on_tmdb_matching_progress = Mock()  # type: ignore
    window.on_tmdb_matching_finished = Mock()  # type: ignore
    window.on_tmdb_matching_error = Mock()  # type: ignore
    window.on_tmdb_matching_cancelled = Mock()  # type: ignore
    window.update_cache_status = Mock()  # type: ignore
    window._on_organize_plan_generated = Mock()  # type: ignore

    return window


@pytest.fixture
def signal_coordinator(main_window_with_components: QMainWindow) -> SignalCoordinator:
    """Create a SignalCoordinator instance for testing.

    Args:
        main_window_with_components: Main window fixture with components

    Returns:
        SignalCoordinator instance
    """
    return SignalCoordinator(cast("MainWindow", main_window_with_components))


class TestSignalCoordinator:
    """Unit tests for SignalCoordinator class."""

    def test_init(
        self,
        main_window_with_components: QMainWindow,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test SignalCoordinator initialization."""
        assert signal_coordinator._main_window == main_window_with_components
        assert isinstance(signal_coordinator._connections, list)
        assert len(signal_coordinator._connections) == 0

    def test_connect_all(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that connect_all() connects all signal groups."""
        # When: connect_all is called
        signal_coordinator.connect_all()

        # Then: All component signals should be connected
        # (We verify this by checking that connect() was called on each signal)
        main_window = signal_coordinator._main_window

        # StateModel signals (2)
        main_window.state_model.files_updated.connect.assert_called_once_with(
            main_window.on_files_updated,
        )
        main_window.state_model.file_status_changed.connect.assert_called_once_with(
            main_window.on_file_status_changed,
        )

        # View signals (1)
        main_window.group_view.groupSelected.connect.assert_called_once_with(
            main_window.on_group_selected,
        )

        # ScanController signals (5)
        main_window.scan_controller.scan_started.connect.assert_called_once_with(
            main_window.on_scan_started,
        )
        main_window.scan_controller.scan_progress.connect.assert_called_once_with(
            main_window.on_scan_progress,
        )
        main_window.scan_controller.scan_finished.connect.assert_called_once_with(
            main_window.on_scan_finished,
        )
        main_window.scan_controller.scan_error.connect.assert_called_once_with(
            main_window.on_scan_error,
        )
        main_window.scan_controller.files_grouped.connect.assert_called_once_with(
            main_window.on_files_grouped,
        )

        # TMDBController signals (7)
        main_window.tmdb_controller.matching_started.connect.assert_called_once_with(
            main_window.on_tmdb_matching_started,
        )
        main_window.tmdb_controller.file_matched.connect.assert_called_once_with(
            main_window.on_tmdb_file_matched,
        )
        main_window.tmdb_controller.matching_progress.connect.assert_called_once_with(
            main_window.on_tmdb_matching_progress,
        )
        main_window.tmdb_controller.matching_finished.connect.assert_called_once_with(
            main_window.on_tmdb_matching_finished,
        )
        main_window.tmdb_controller.matching_error.connect.assert_called_once_with(
            main_window.on_tmdb_matching_error,
        )
        main_window.tmdb_controller.matching_cancelled.connect.assert_called_once_with(
            main_window.on_tmdb_matching_cancelled,
        )
        main_window.tmdb_controller.cache_stats_updated.connect.assert_called_once_with(
            main_window.update_cache_status,
        )

        # OrganizeController signals (1)
        main_window.organize_controller.plan_generated.connect.assert_called_once_with(
            main_window._on_organize_plan_generated,
        )

    def test_connect_state_signals(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that _connect_state_signals() connects StateModel signals."""
        # When: _connect_state_signals is called
        signal_coordinator._connect_state_signals()

        # Then: StateModel signals should be connected
        main_window = signal_coordinator._main_window

        main_window.state_model.files_updated.connect.assert_called_once_with(
            main_window.on_files_updated,
        )
        main_window.state_model.file_status_changed.connect.assert_called_once_with(
            main_window.on_file_status_changed,
        )

    def test_connect_view_signals(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that _connect_view_signals() connects View widget signals."""
        # When: _connect_view_signals is called
        signal_coordinator._connect_view_signals()

        # Then: View signals should be connected
        main_window = signal_coordinator._main_window

        main_window.group_view.groupSelected.connect.assert_called_once_with(
            main_window.on_group_selected,
        )

    def test_connect_scan_controller(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that _connect_scan_controller() connects ScanController signals."""
        # When: _connect_scan_controller is called
        signal_coordinator._connect_scan_controller()

        # Then: ScanController signals should be connected
        main_window = signal_coordinator._main_window

        main_window.scan_controller.scan_started.connect.assert_called_once_with(
            main_window.on_scan_started,
        )
        main_window.scan_controller.scan_progress.connect.assert_called_once_with(
            main_window.on_scan_progress,
        )
        main_window.scan_controller.scan_finished.connect.assert_called_once_with(
            main_window.on_scan_finished,
        )
        main_window.scan_controller.scan_error.connect.assert_called_once_with(
            main_window.on_scan_error,
        )
        main_window.scan_controller.files_grouped.connect.assert_called_once_with(
            main_window.on_files_grouped,
        )

    def test_connect_tmdb_controller(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that _connect_tmdb_controller() connects TMDBController signals."""
        # When: _connect_tmdb_controller is called
        signal_coordinator._connect_tmdb_controller()

        # Then: TMDBController signals should be connected
        main_window = signal_coordinator._main_window

        main_window.tmdb_controller.matching_started.connect.assert_called_once_with(
            main_window.on_tmdb_matching_started,
        )
        main_window.tmdb_controller.file_matched.connect.assert_called_once_with(
            main_window.on_tmdb_file_matched,
        )
        main_window.tmdb_controller.matching_progress.connect.assert_called_once_with(
            main_window.on_tmdb_matching_progress,
        )
        main_window.tmdb_controller.matching_finished.connect.assert_called_once_with(
            main_window.on_tmdb_matching_finished,
        )
        main_window.tmdb_controller.matching_error.connect.assert_called_once_with(
            main_window.on_tmdb_matching_error,
        )
        main_window.tmdb_controller.matching_cancelled.connect.assert_called_once_with(
            main_window.on_tmdb_matching_cancelled,
        )
        main_window.tmdb_controller.cache_stats_updated.connect.assert_called_once_with(
            main_window.update_cache_status,
        )

    def test_connect_organize_controller(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that _connect_organize_controller() connects OrganizeController signals."""
        # When: _connect_organize_controller is called
        signal_coordinator._connect_organize_controller()

        # Then: OrganizeController signals should be connected
        main_window = signal_coordinator._main_window

        main_window.organize_controller.plan_generated.connect.assert_called_once_with(
            main_window._on_organize_plan_generated,
        )

    def test_disconnect_all(
        self,
        signal_coordinator: SignalCoordinator,
    ) -> None:
        """Test that disconnect_all() completes without errors.

        Note: disconnect_all() is currently a placeholder for future cleanup.
        This test verifies it can be called without errors.
        """
        # When: disconnect_all is called
        signal_coordinator.disconnect_all()

        # Then: No errors should occur (placeholder implementation)
        # In the future, this would verify that signals are actually disconnected

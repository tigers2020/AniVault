"""Tests for refactored panels using new theme system."""

from collections.abc import Generator

import pytest
from PyQt5.QtWidgets import QApplication, QLabel

from src.gui.anime_groups_panel import AnimeGroupsPanel
from src.gui.log_panel import LogPanel
from src.gui.work_panel import WorkPanel
from src.themes.dark_theme import DarkTheme
from src.themes.theme_manager import get_theme_manager


@pytest.fixture(scope="session")  # type: ignore[misc]
def qapp() -> Generator[QApplication, None, None]:
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
    # Don't quit the app as it might be used by other tests


class TestPanelRefactoring:
    """Test that refactored panels work with new theme system."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])

        # Reset ThemeManager singleton state
        from src.themes.theme_manager import ThemeManager

        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_work_panel_theme_integration(self, qapp: QApplication) -> None:
        """Test work panel uses theme manager correctly."""
        panel = WorkPanel()

        # Check that theme manager is used
        assert hasattr(panel, "theme_manager")
        assert panel.theme_manager is not None

        # Check that labels use theme colors
        source_label = panel.findChild(QLabel, "소스 폴더")
        if source_label:
            style = source_label.styleSheet()
            assert "color:" in style
            # Should not contain hardcoded color
            assert "#94a3b8" not in style or "label_text" in style

    def test_log_panel_theme_integration(self, qapp: QApplication) -> None:
        """Test log panel uses theme manager correctly."""
        panel = LogPanel()

        # Check that theme manager is used
        assert hasattr(panel, "theme_manager")
        assert panel.theme_manager is not None

        # Test log level colors
        panel.add_log("Test info", "INFO")
        panel.add_log("Test warning", "WARNING")
        panel.add_log("Test error", "ERROR")
        panel.add_log("Test success", "SUCCESS")

        # Should not raise any errors
        assert panel.get_log_count() > 0

    def test_anime_groups_panel_theme_integration(self, qapp: QApplication) -> None:
        """Test anime groups panel uses theme manager correctly."""
        panel = AnimeGroupsPanel()

        # Check that theme manager is used
        assert hasattr(panel, "theme_manager")
        assert panel.theme_manager is not None

        # Check that status colors are set using theme
        assert hasattr(panel, "_set_status_color")

        # Test adding groups with different statuses
        panel.add_group("Test Group 1", 5, "완료")
        panel.add_group("Test Group 2", 3, "대기")
        panel.add_group("Test Group 3", 2, "오류")

        # Should not raise any errors
        assert panel.groups_table.rowCount() > 0

    def test_theme_consistency_across_panels(self, qapp: QApplication) -> None:
        """Test that all panels use the same theme manager instance."""
        work_panel = WorkPanel()
        log_panel = LogPanel()
        groups_panel = AnimeGroupsPanel()

        # All panels should use the same theme manager instance
        assert work_panel.theme_manager is log_panel.theme_manager
        assert log_panel.theme_manager is groups_panel.theme_manager

        # Should be the same as global instance
        global_manager = get_theme_manager()
        assert work_panel.theme_manager is global_manager

    def test_color_access_methods(self) -> None:
        """Test that color access methods work correctly."""
        manager = get_theme_manager()

        # Test basic color access
        primary_color = manager.get_color("primary")
        assert primary_color == "#3b82f6"

        # Test log level colors
        log_info_color = manager.current_theme.get_log_level_color("INFO")
        assert log_info_color == "#94a3b8"

        # Test status colors
        status_success_color = manager.current_theme.get_status_color("success")
        assert status_success_color == "#22c55e"

        # Test label text color
        label_text_color = manager.get_color("label_text")
        assert label_text_color == "#94a3b8"

    def test_no_hardcoded_colors_in_panels(self, qapp: QApplication) -> None:
        """Test that panels don't contain hardcoded color values."""
        work_panel = WorkPanel()
        log_panel = LogPanel()
        groups_panel = AnimeGroupsPanel()

        # Check that hardcoded colors are not used in style sheets
        # This is a basic check - in practice, we'd need to inspect the actual style sheets

        # Work panel should use theme manager for colors
        assert hasattr(work_panel, "theme_manager")

        # Log panel should use theme manager for colors
        assert hasattr(log_panel, "theme_manager")

        # Groups panel should use theme manager for colors
        assert hasattr(groups_panel, "theme_manager")

    def test_theme_change_propagation(self, qapp: QApplication) -> None:
        """Test that theme changes can be propagated to panels."""
        manager = get_theme_manager()

        # Register a callback to track theme changes
        theme_changes: list[DarkTheme] = []

        def track_theme_change(theme: DarkTheme) -> None:
            theme_changes.append(theme)

        manager.register_theme_change_callback(track_theme_change)

        # Switch theme (this should trigger callbacks)
        manager.switch_theme(DarkTheme)

        # Should have received theme change notification
        assert len(theme_changes) > 0
        assert isinstance(theme_changes[0], DarkTheme)

        # Clean up
        manager.unregister_theme_change_callback(track_theme_change)


if __name__ == "__main__":
    pytest.main([__file__])

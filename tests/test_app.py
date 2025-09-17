"""Tests for the main application."""

from collections.abc import Generator

import pytest
from PyQt5.QtWidgets import QApplication

from src.app import AniVaultApp


@pytest.fixture  # type: ignore[misc]
def app() -> Generator[QApplication, None, None]:
    """Create a QApplication instance for testing."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture  # type: ignore[misc]
def main_window(app: QApplication) -> Generator[AniVaultApp, None, None]:
    """Create a main window instance for testing."""
    window = AniVaultApp()
    yield window
    window.close()


def test_main_window_creation(main_window: AniVaultApp) -> None:
    """Test that the main window is created successfully."""
    assert main_window is not None
    assert main_window.windowTitle() == "AniVault - Anime Management"


def test_main_window_geometry(main_window: AniVaultApp) -> None:
    """Test that the main window has correct geometry."""
    assert main_window.width() == 800
    assert main_window.height() == 600


def test_main_window_central_widget(main_window: AniVaultApp) -> None:
    """Test that the main window has a central widget."""
    assert main_window.centralWidget() is not None

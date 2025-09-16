"""Tests for the main application."""

import pytest
from PyQt5.QtWidgets import QApplication

from src.app import AniVaultApp


@pytest.fixture
def app():
    """Create a QApplication instance for testing."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def main_window(app):
    """Create a main window instance for testing."""
    window = AniVaultApp()
    yield window
    window.close()


def test_main_window_creation(main_window):
    """Test that the main window is created successfully."""
    assert main_window is not None
    assert main_window.windowTitle() == "AniVault - Anime Management"


def test_main_window_geometry(main_window):
    """Test that the main window has correct geometry."""
    assert main_window.width() == 800
    assert main_window.height() == 600


def test_main_window_central_widget(main_window):
    """Test that the main window has a central widget."""
    assert main_window.centralWidget() is not None

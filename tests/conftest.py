"""Pytest configuration and fixtures for AniVault tests."""

import os
import pytest
from PyQt5 import QtCore


@pytest.fixture(autouse=True)
def _qt_offscreen_env(monkeypatch):
    """Set Qt to offscreen mode for CI compatibility."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    yield


@pytest.fixture(autouse=True)
def _cleanup_qt_threads():
    """Clean up Qt threads and event processing after each test."""
    yield
    try:
        # Wait for global thread pool to finish
        QtCore.QThreadPool.globalInstance().waitForDone(500)
    except Exception:
        pass
    # Process any remaining events
    try:
        QtCore.QCoreApplication.processEvents()
    except Exception:
        pass


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for the entire test session."""
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    # Clean up
    app.processEvents()
    QtCore.QThreadPool.globalInstance().waitForDone(1000)

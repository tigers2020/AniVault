"""
Worker classes for AniVault GUI

This module contains worker classes that handle background operations
using PySide6's QThread and signal/slot mechanism.
"""

from .file_scanner_worker import FileScannerWorker
from .tmdb_matching_worker import TMDBMatchingWorker

__all__ = ["FileScannerWorker", "TMDBMatchingWorker"]

"""Event Handlers for MainWindow.

This package contains event handler classes that process signals from controllers
and update the UI accordingly. Handlers follow a consistent pattern established
by BaseEventHandler.

Classes:
    BaseEventHandler: Base class for all event handlers
    ScanEventHandler: Handles scan-related events
    TMDBEventHandler: Handles TMDB matching events
    OrganizeEventHandler: Handles file organization events
"""

from .base_event_handler import BaseEventHandler
from .organize_event_handler import OrganizeEventHandler
from .scan_event_handler import ScanEventHandler
from .tmdb_event_handler import TMDBEventHandler

__all__ = [
    "BaseEventHandler",
    "OrganizeEventHandler",
    "ScanEventHandler",
    "TMDBEventHandler",
]

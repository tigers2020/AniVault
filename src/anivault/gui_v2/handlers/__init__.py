"""Event handlers for MainWindow."""

from __future__ import annotations

from .match_event_handler import MatchEventHandler
from .organize_event_handler import OrganizeEventHandler
from .scan_event_handler import ScanEventHandler

__all__ = ["MatchEventHandler", "OrganizeEventHandler", "ScanEventHandler"]

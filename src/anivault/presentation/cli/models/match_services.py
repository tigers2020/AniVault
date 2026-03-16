"""Typed service container for match CLI helpers.

Re-exports from app.models for backward compatibility.
"""

from __future__ import annotations

from anivault.application.models.match_services import MatchServices

__all__ = ["MatchServices"]

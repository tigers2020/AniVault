"""Protocol definitions for dependency inversion.

This module provides Protocol interfaces to break dependency layer violations.
Core modules can use these protocols without importing from services layer.
"""

from __future__ import annotations

from .services import TMDBClientProtocol

__all__ = ["TMDBClientProtocol"]

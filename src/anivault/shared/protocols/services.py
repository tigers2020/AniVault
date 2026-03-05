"""Service protocols for dependency inversion.

Re-exports from domain.interfaces for backward compatibility.
"""

from __future__ import annotations

from anivault.domain.interfaces.tmdb_client import TMDBClientProtocol

__all__ = ["TMDBClientProtocol"]

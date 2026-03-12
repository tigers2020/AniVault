"""Cache infrastructure (Phase 5).

Re-exports from services.cache for backward compatibility.
"""

from anivault.services.cache import SQLiteCacheDB

__all__ = ["SQLiteCacheDB"]

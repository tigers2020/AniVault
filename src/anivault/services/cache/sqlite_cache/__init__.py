"""SQLite cache module with modular operations.

NOTE: The public cache API is ``from anivault.services.cache import SQLiteCacheDB``,
which resolves to ``sqlite_cache_db.SQLiteCacheDB``. The ``sqlite_cache.cache_db``
implementation is currently unused and deprecated; see cache_db.py docstring.
"""

from anivault.services.cache.sqlite_cache.cache_db import SQLiteCacheDB

__all__ = ["SQLiteCacheDB"]

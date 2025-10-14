# TMDB Cache Database System

**Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: Production Ready

---

## Overview

AniVault's TMDB Cache Database System provides high-performance, reliable caching for TMDB API responses using SQLite. This system reduces API calls, improves response times, and enables offline functionality.

### Key Features

- ✅ **SQLite-based caching** with Write-Ahead Logging (WAL) for concurrency
- ✅ **Hybrid schema** - JSON blob storage with partial normalization
- ✅ **TTL-based expiration** with automatic cleanup
- ✅ **Security-first design** - File permissions 600, API key validation
- ✅ **Performance optimized** - Indexed queries, batch operations
- ✅ **Hybrid mode** - SQLite + JSON fallback for reliability

---

## Quick Start

### Basic Usage

```python
from pathlib import Path
from anivault.services.sqlite_cache_db import SQLiteCacheDB

# Initialize cache
cache = SQLiteCacheDB(Path("~/.anivault/tmdb_cache.db"))

# Store data
cache.set_cache(
    key="search:movie:attack on titan",
    data={"results": [{"id": 1234, "title": "Attack on Titan"}]},
    cache_type="search",
    ttl_seconds=86400  # 24 hours
)

# Retrieve data
results = cache.get("search:movie:attack on titan", cache_type="search")

# Close connection
cache.close()
```

### Use Case 1: CLI Command Integration

```python
# In CLI command handler
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.tmdb_client import TMDBClient

def match_command(directory: str, use_cache: bool = True):
    """Match anime files with TMDB."""
    # Initialize cache
    cache_db = SQLiteCacheDB(Path("~/.anivault/cache.db"))

    # Create TMDB client with cache
    tmdb_client = TMDBClient(api_key=api_key, cache=cache_db)

    # Match files
    results = tmdb_client.search_anime("進撃の巨人", language="ja")

    cache_db.close()
    return results
```

### Use Case 2: GUI Application

```python
# In GUI controller
from PySide6.QtCore import QObject, Signal
from anivault.services.sqlite_cache_db import SQLiteCacheDB

class TMDBController(QObject):
    cache_stats_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.cache = SQLiteCacheDB(Path("~/.anivault/cache.db"))

    def get_cache_stats(self):
        """Get cache statistics for UI display."""
        info = self.cache.get_cache_info()
        stats = {
            "total_items": info["total_files"],
            "valid_items": info["valid_entries"],
            "cache_type": "SQLite"
        }
        self.cache_stats_updated.emit(stats)
```

### Use Case 3: Performance Monitoring

```python
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from pathlib import Path

# Initialize cache
cache = SQLiteCacheDB(Path("~/.anivault/cache.db"))

# Monitor cache performance
info = cache.get_cache_info()
print(f"""
Cache Performance:
- Total entries: {info['total_files']}
- Valid entries: {info['valid_entries']}
- Expired entries: {info['expired_entries']}
- Cache size: {info['total_size_bytes'] / (1024*1024):.2f} MB
""")

# Periodic cleanup
removed = cache.purge_expired()
print(f"Cleaned up {removed} expired entries")

cache.close()
```

---

## Configuration

### Cache Mode

AniVault uses **SQLite-only** cache mode for optimal performance:

| Mode | Description | Status |
|------|-------------|--------|
| `db-only` | SQLite exclusively | ✅ **Active** (Production) |
| ~~`json-only`~~ | ~~JSON files only~~ | ❌ **Deprecated** (Removed) |
| ~~`hybrid`~~ | ~~SQLite + JSON fallback~~ | ❌ **Deprecated** (Removed) |

### Cache Configuration

**Default**: SQLite cache is automatically used

**Via Configuration File** (`~/.anivault/config.toml`):

```toml
[cache]
db_path = "~/.anivault/tmdb_cache.db"
auto_cleanup = true  # Purge expired entries on startup
```

**Cache Location**:
- **Default**: `~/.anivault/tmdb_cache.db`
- **Custom**: Set via `db_path` in config

---

## API Reference

### SQLiteCacheDB Class

#### Methods

##### `__init__(db_path, statistics=None)`

Initialize SQLite cache database.

**Parameters**:
- `db_path` (Path | str): Path to SQLite database file
- `statistics` (StatisticsCollector, optional): Statistics collector

**Raises**:
- `InfrastructureError`: If database initialization fails

---

##### `set_cache(key, data, cache_type='search', ttl_seconds=None)`

Store data in cache with optional TTL.

**Parameters**:
- `key` (str): Cache key identifier
- `data` (dict): Data to cache
- `cache_type` (str): Type of cache ('search' or 'details')
- `ttl_seconds` (int, optional): Time-to-live in seconds

**Raises**:
- `ApplicationError`: If data contains sensitive information (API keys)
- `InfrastructureError`: If database operation fails

**Example**:
```python
cache.set_cache(
    key="search:tv:진격의거인:lang=ko",
    data={"results": [...]},
    cache_type="search",
    ttl_seconds=86400
)
```

---

##### `get(key, cache_type='search')`

Retrieve data from cache.

**Parameters**:
- `key` (str): Cache key identifier
- `cache_type` (str): Type of cache ('search' or 'details')

**Returns**:
- `dict | None`: Cached data if found and valid, None otherwise

**Example**:
```python
data = cache.get("search:tv:진격의거인:lang=ko", cache_type="search")
if data:
    print(f"Found {len(data['results'])} results")
```

---

##### `delete(key, cache_type='search')`

Delete specific cache entry.

**Parameters**:
- `key` (str): Cache key identifier
- `cache_type` (str): Type of cache

**Returns**:
- `bool`: True if deleted, False if not found

---

##### `purge_expired(cache_type=None)`

Remove all expired cache entries.

**Parameters**:
- `cache_type` (str, optional): Filter by cache type

**Returns**:
- `int`: Number of entries removed

**Example**:
```python
removed = cache.purge_expired()
print(f"Cleaned up {removed} expired entries")
```

---

##### `clear(cache_type=None)`

Clear all cache entries (or by type).

**Parameters**:
- `cache_type` (str, optional): Filter by cache type

**Returns**:
- `int`: Number of entries removed

---

##### `get_cache_info(cache_type=None)`

Get cache statistics and information.

**Returns**:
- `dict`: Cache information with keys:
  - `total_files`: Total cache entries
  - `valid_entries`: Non-expired entries
  - `expired_entries`: Expired entries
  - `total_size_bytes`: Total cache size
  - `cache_directory`: Database file path

**Example**:
```python
info = cache.get_cache_info()
print(f"Cache: {info['valid_entries']} valid, {info['expired_entries']} expired")
```

---

##### `close()`

Close database connection.

**Important**: Always call `close()` when done to release resources.

---

## Cache Key Design

### Format

Cache keys follow this format:
```
{cache_type}:{media_type}:{query}:{params}
```

### Examples

```python
# Search query
"search:tv:진격의거인:lang=ko"

# Movie details
"details:movie:1234:append_to_response=credits,images"

# TV details with language
"details:tv:5678:lang=ja&append_to_response=credits"
```

### Key Normalization

Keys are automatically normalized:
- Converted to lowercase
- Parameters sorted alphabetically
- SHA-256 hashed for storage

---

## TTL Strategy

Different cache types have different expiration times:

| Cache Type | TTL | Reason |
|------------|-----|--------|
| **Movie Details** | 14 days | Rarely change |
| **TV Details** | 14 days | Rarely change |
| **Search Results** | 24 hours | May change frequently |
| **Credits** | 7 days | Occasionally updated |
| **Images** | 7 days | Occasionally updated |

### Custom TTL

```python
# Short TTL for frequently changing data
cache.set_cache(key, data, ttl_seconds=3600)  # 1 hour

# Long TTL for stable data
cache.set_cache(key, data, ttl_seconds=604800)  # 7 days

# No expiration
cache.set_cache(key, data, ttl_seconds=0)
```

---

## Security

### File Permissions

SQLite database files are automatically secured:
- **Unix/Linux**: `chmod 600` (owner read/write only)
- **Windows**: Owner-only ACL (requires pywin32 for full security)

### API Key Protection

The cache system **prevents caching sensitive data**:

```python
# ❌ This will raise ApplicationError
cache.set_cache(
    key="search:test",
    data={"api_key": "sk-123", "results": [...]},  # API key detected!
    cache_type="search"
)
# ApplicationError: Attempted to cache sensitive data: api_key

# ✅ This is safe
cache.set_cache(
    key="search:test",
    data={"results": [...]},  # No sensitive data
    cache_type="search"
)
```

Detected sensitive keys:
- `api_key`, `apikey`, `api-key`
- `secret`, `password`
- `token`, `access_token`, `refresh_token`

---

## Maintenance

### Cleanup Expired Entries

Automatic cleanup runs on startup. Manual cleanup:

```python
# Remove all expired entries
cache.purge_expired()

# Remove expired entries of specific type
cache.purge_expired(cache_type="search")
```

### Clear Cache

```python
# Clear all cache
cache.clear()

# Clear specific cache type
cache.clear(cache_type="search")
```

### Backup

```bash
# SQLite database can be backed up while running (WAL mode)
cp ~/.anivault/tmdb_cache.db ~/.anivault/backups/cache_backup_$(date +%Y%m%d).db
```

---

## Performance

See [Performance Benchmark Report](../performance/cache_benchmark.md) for detailed metrics.

**Summary**:
- **Sequential operations**: SQLite 2-9x faster than JSON
- **Concurrent operations**: JSON 1.4x faster than SQLite
- **Recommendation**: Use SQLite for production (better overall performance)

---

## Troubleshooting

### Issue: "Database is locked"

**Cause**: Multiple processes accessing database without WAL mode

**Solution**:
- WAL mode is enabled by default
- Check if `PRAGMA journal_mode=WAL` is active
- Ensure proper connection cleanup with `close()`

### Issue: "Permission denied"

**Cause**: Insufficient file permissions

**Solution**:
```bash
# Unix/Linux
chmod 600 ~/.anivault/tmdb_cache.db

# Windows
# Run as administrator or check file ownership
```

### Issue: "Cache not working"

**Cause**: Cache might be disabled or misconfigured

**Solution**:
1. Check cache mode: `config.get("cache.mode")`
2. Verify database file exists and is writable
3. Check logs for errors: `anivault --log-level=DEBUG`

---

## Migration

See [Migration Guide](../migration/json_to_sqlite.md) for migrating from JSONCacheV2 to SQLiteCacheDB.

---

## Further Reading

- [Architecture Documentation](../architecture/cache_system.md)
- [Performance Benchmarks](../performance/cache_benchmark.md)
- [Security Guidelines](../security/README.md)

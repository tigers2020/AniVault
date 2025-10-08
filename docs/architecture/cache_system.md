# TMDB Cache System Architecture

**Version**: 1.0  
**Last Updated**: 2025-10-06  
**Component**: Cache Layer

---

## System Overview

The TMDB Cache System is a critical component of AniVault that optimizes API usage, improves performance, and enables offline functionality.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AniVault Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐       ┌──────────────┐                    │
│  │ MatchingEngine│──────▶│ TMDBClient   │                    │
│  └──────────────┘       └──────┬───────┘                    │
│                                 │                             │
│                         ┌───────▼────────┐                   │
│                         │ Cache Layer    │                   │
│                         │  (SQLite-only) │                   │
│                         └───────┬────────┘                   │
│                                 │                             │
│                         ┌───────▼───────┐                    │
│                         │ SQLiteCacheDB │                    │
│                         │  (Production) │                    │
│                         └───────┬───────┘                    │
│                                 │                             │
│                         ┌───────▼───────┐                    │
│                         │  cache.db     │                    │
│                         │  (WAL mode)   │                    │
│                         │  Permissions: │                    │
│                         │  600 (secure) │                    │
│                         └───────────────┘                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. SQLiteCacheDB (Primary Cache)

**File**: `src/anivault/services/sqlite_cache_db.py`

**Responsibilities**:
- Store TMDB API responses as JSON blobs
- Provide fast indexed lookups
- Manage TTL-based expiration
- Ensure data integrity with transactions

**Technology Stack**:
- SQLite 3 (Python standard library)
- WAL (Write-Ahead Logging) mode for concurrency
- JSON serialization for flexible data storage

**Schema**:
```sql
CREATE TABLE tmdb_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Cache key information
    cache_key TEXT NOT NULL UNIQUE,
    key_hash TEXT NOT NULL UNIQUE,
    
    -- Cache type (extensible)
    cache_type TEXT NOT NULL,
    endpoint_category TEXT,
    
    -- Response data (JSON BLOB)
    response_data TEXT NOT NULL,
    
    -- TTL and metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    
    -- Statistics
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    response_size INTEGER,
    
    -- Constraints
    CHECK (length(cache_key) > 0),
    CHECK (length(key_hash) = 64)
);

-- Performance indexes
CREATE INDEX idx_key_hash ON tmdb_cache(key_hash);
CREATE INDEX idx_cache_type ON tmdb_cache(cache_type);
CREATE INDEX idx_expires_at ON tmdb_cache(expires_at);
```

---

### 2. ~~JSONCacheV2~~ (Deprecated - Removed)

**Status**: ❌ **Removed from codebase**

**Previous File**: ~~`src/anivault/services/cache_v2.py`~~ (deleted)

**Reason for Removal**:
- SQLite provides superior performance (8.8x faster reads)
- No longer needed after successful migration
- Reduced code complexity and maintenance burden

**Legacy Reference**: See benchmark results in `docs/performance/cache_benchmark.md`

---

### 3. Cache Utilities

**File**: `src/anivault/shared/cache_utils.py`

**Responsibilities**:
- Generate normalized cache keys
- Create SHA-256 hashes
- Validate cache parameters

**Key Functions**:
```python
def generate_cache_key(
    cache_type: str,
    media_type: str,
    query: str,
    params: dict
) -> str:
    """Generate normalized cache key."""
    
def hash_cache_key(key: str) -> str:
    """Generate SHA-256 hash of cache key."""
```

---

### 4. Security Layer

**File**: `src/anivault/security/permissions.py`

**Responsibilities**:
- Set secure file permissions (600)
- Validate against sensitive data caching
- Cross-platform security support

**Functions**:
- `set_secure_file_permissions(file_path)`: Set OS-specific permissions
- `validate_api_key_not_in_data(data)`: Prevent API key caching

---

## Cache Strategy

### SQLite-Only Mode (Production)

```python
def cache_get(key: str, cache_type: str = "search") -> dict | None:
    """SQLite cache retrieval strategy."""
    # 1. Try SQLite cache
    data = sqlite_cache.get(key, cache_type)
    if data:
        logger.debug("Cache hit: %s", key)
        return data
    
    # 2. Cache miss - fetch from API
    logger.debug("Cache miss: %s", key)
    return None

def cache_set(key: str, data: dict, cache_type: str = "search", ttl_seconds: int = 86400):
    """Store data in SQLite cache with validation."""
    # Security validation
    validate_api_key_not_in_data(data)
    
    # Store in cache
    sqlite_cache.set_cache(key, data, cache_type, ttl_seconds)
    logger.debug("Cached: %s", key)
```

---

## Performance Characteristics

### Benchmark Results Summary

| Operation | SQLiteCacheDB | ~~JSONCacheV2~~ (Legacy) | Winner |
|-----------|---------------|--------------------------|--------|
| Single Write (1K items) | 0.29ms/item | ~~0.72ms/item~~ | ✅ SQLite (2.5x faster) |
| Single Read (1K items) | 0.12ms/item | ~~1.05ms/item~~ | ✅ SQLite (8.8x faster) |
| Bulk Write (10K items) | 2,705 TPS | ~~1,253 TPS~~ | ✅ SQLite (2.2x faster) |
| Concurrent (10 threads) | 3,610 ops/sec | ~~5,114 ops/sec~~ | ℹ️ JSON was faster |

**Decision**: SQLite-only for production (8.8x read performance critical for UX)

---

## Concurrency Model

### SQLite WAL Mode

**Benefits**:
- Multiple readers don't block each other
- Writers don't block readers
- Auto-checkpoint for consistency

**Configuration**:
```python
# Automatically configured in SQLiteCacheDB.__init__
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
```

**Limitations**:
- Single writer at a time (but very fast)
- Requires file system support for memory-mapped I/O

---

## Data Flow

### Cache Write Flow

```
1. Request to cache data
   ↓
2. Validate data (no API keys)
   ↓
3. Generate cache key + hash
   ↓
4. Calculate expiration timestamp
   ↓
5. Serialize to JSON
   ↓
6. INSERT OR REPLACE into database
   ↓
7. Update statistics
   ↓
8. Return success
```

### Cache Read Flow

```
1. Request data by key
   ↓
2. Generate key hash
   ↓
3. Query database (indexed)
   ↓
4. Check expiration
   ↓
5. Deserialize JSON
   ↓
6. Update hit statistics
   ↓
7. Return data (or None if expired/missing)
```

---

## Integration Points

### MatchingEngine Integration

**File**: `src/anivault/core/matching/engine.py`

The MatchingEngine uses cache through TMDBClient:

```python
class MatchingEngine:
    def __init__(self, tmdb_client, cache_mode="db-only"):
        self.tmdb_client = tmdb_client
        self.cache_mode = cache_mode
    
    def get_cache_stats(self):
        """Get cache statistics for UI."""
        return {
            "cache_mode": self.cache_mode,
            "cache_type": "SQLite" if self.cache_mode == "db-only" else "Hybrid",
            # ... more stats
        }
```

### TMDBClient Integration

**File**: `src/anivault/services/tmdb_client.py`

TMDBClient accepts cache instance:

```python
class TMDBClient:
    def __init__(self, api_key, cache=None):
        self.cache = cache or SQLiteCacheDB(default_db_path)
    
    async def search_tv(self, query, language="en"):
        # Check cache first
        cache_key = generate_cache_key("search", "tv", query, {"language": language})
        cached = self.cache.get(cache_key, cache_type="search")
        
        if cached:
            return cached
        
        # Fetch from API
        result = await self._api_call(...)
        
        # Store in cache
        self.cache.set_cache(cache_key, result, cache_type="search", ttl_seconds=86400)
        
        return result
```

---

## Dependency Graph

```
MatchingEngine
    └─▶ TMDBClient
            └─▶ SQLiteCacheDB
                    ├─▶ StatisticsCollector
                    ├─▶ SecurityPermissions (validate_api_key_not_in_data, set_secure_file_permissions)
                    └─▶ CacheUtils (generate_cache_key, hash_cache_key)
```

---

## Design Decisions

### 1. Why SQLite over JSON files?

**Decision**: Use SQLite as primary cache

**Rationale**:
- 8.8x faster reads (critical for performance)
- ACID guarantees for data integrity
- Built-in query optimization
- No external dependencies (stdlib)

**Trade-offs**:
- Slightly more complex setup
- Binary format (less human-readable)
- Requires proper connection management

---

### 2. Why Hybrid Schema (JSON blob + partial normalization)?

**Decision**: Store full response as JSON, normalize only key fields

**Rationale**:
- **Completeness**: Full API response preserved in JSON
- **Performance**: Key fields (cache_type, expires_at) indexed
- **Flexibility**: No schema changes needed for API updates

**Trade-offs**:
- Some data duplication
- Cannot query deep into JSON easily

---

### 3. Why TTL-based expiration?

**Decision**: Different TTL per cache type, auto-cleanup

**Rationale**:
- **Freshness**: Search results expire quickly (24h)
- **Efficiency**: Details cached longer (14 days)
- **Storage**: Auto-cleanup prevents unbounded growth

---

### 4. Why WAL mode?

**Decision**: Enable Write-Ahead Logging by default

**Rationale**:
- **Concurrency**: Multiple readers + single writer
- **Performance**: 2-3x faster writes
- **Reliability**: Crash recovery built-in

**Trade-offs**:
- Extra files (-wal, -shm)
- Requires checkpoint management

---

## Future Improvements

### Planned (platformdirs integration)

**Issue**: OS-specific cache paths

**Current**: Hardcoded `~/.anivault/cache.db`

**Planned**: Use `platformdirs` for platform-specific paths:
- **Windows**: `%LOCALAPPDATA%\AniVault\Cache`
- **macOS**: `~/Library/Caches/AniVault`
- **Linux**: `~/.cache/anivault`

**Priority**: Low (current approach works)

---

### Considered (Database compression)

**Issue**: Large cache size

**Potential**: Enable SQLite compression

**Status**: Deferred (performance impact unknown)

---

## Testing Strategy

### Unit Tests

**File**: `tests/services/test_sqlite_cache_db.py`

- CRUD operations
- TTL expiration
- Error handling
- Edge cases

### Integration Tests

**File**: `tests/integration/test_cache_security.py`

- TMDBClient integration
- Security validation
- Hybrid mode switching

### Performance Tests

**File**: `tests/performance/bench_cache_db.py`

- Read/write throughput
- Bulk operations
- Concurrency stress tests

---

## Monitoring & Observability

### Statistics Collection

```python
# Get cache statistics
stats = cache.statistics.get_stats()

# Metrics available:
# - cache_hits: Number of successful cache retrievals
# - cache_misses: Number of cache misses
# - cache_sets: Number of cache writes
# - avg_response_time: Average operation time
```

### Health Check

```python
def health_check(cache: SQLiteCacheDB) -> dict:
    """Check cache health."""
    info = cache.get_cache_info()
    
    return {
        "healthy": info["total_files"] > 0,
        "total_entries": info["total_files"],
        "expired_ratio": info["expired_entries"] / info["total_files"],
        "db_size_mb": info["total_size_bytes"] / (1024 * 1024)
    }
```

---

## References

- [SQLite WAL Mode Documentation](https://www.sqlite.org/wal.html)
- [TMDB API Documentation](https://developers.themoviedb.org/3)
- [Performance Benchmark Report](../performance/cache_benchmark.md)
- [User Guide](../tmdb_cache_db.md)


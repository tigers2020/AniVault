# Migration Guide: JSONCacheV2 to SQLiteCacheDB

**Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: ❌ **DEPRECATED** - Migration Complete, JSON cache removed
**Migration Strategy**: ~~Gradual with Rollback Support~~

> ⚠️ **Note**: This guide is now for historical reference only.
> AniVault has completed migration to SQLite-only cache.
> JSONCacheV2 has been removed from the codebase.

---

## Overview

This guide provides step-by-step instructions for migrating from the file-based JSONCacheV2 cache system to the SQLite-based SQLiteCacheDB system.

### Migration Phases

1. **Week 1**: Hybrid mode (both caches active)
2. **Week 2-3**: DB-primary mode (SQLite primary, JSON fallback)
3. **Week 4**: DB-only mode (SQLite exclusively)

---

## Pre-Migration Checklist

Before starting migration:

- [ ] **Backup existing cache**:
  ```bash
  cp -r ~/.anivault/json_cache ~/.anivault/backups/json_cache_$(date +%Y%m%d)
  ```

- [ ] **Verify disk space**:
  ```bash
  du -sh ~/.anivault/json_cache
  # Ensure 2x space available for SQLite conversion
  ```

- [ ] **Test SQLite installation**:
  ```python
  import sqlite3
  print(sqlite3.sqlite_version)  # Should be 3.35.0+
  ```

- [ ] **Review current cache usage**:
  ```bash
  find ~/.anivault/json_cache -type f | wc -l  # Count cache files
  ```

---

## Phase 1: Hybrid Mode (Week 1)

### Step 1: Update Configuration

**File**: `~/.anivault/config.toml`

```toml
[cache]
mode = "hybrid"  # Enable both caches
db_path = "~/.anivault/tmdb_cache.db"
json_path = "~/.anivault/json_cache"
```

### Step 2: Initialize SQLite Cache

```python
from pathlib import Path
from anivault.services.sqlite_cache_db import SQLiteCacheDB

# Create new SQLite cache
cache = SQLiteCacheDB(Path.home() / ".anivault" / "tmdb_cache.db")

# Verify initialization
info = cache.get_cache_info()
print(f"Cache initialized: {info['cache_directory']}")

cache.close()
```

### Step 3: Run Application in Hybrid Mode

```bash
# CLI usage
anivault match /path/to/anime --cache-mode=hybrid

# GUI usage - cache mode is automatic from config
python -m anivault.gui.app
```

### Step 4: Monitor Both Caches

```python
# Check cache statistics
from anivault.core.matching.engine import MatchingEngine

engine = MatchingEngine(tmdb_client, cache_mode="hybrid")
stats = engine.get_cache_stats()

print(f"Cache mode: {stats['cache_mode']}")
print(f"Hit ratio: {stats['hit_ratio']:.1f}%")
```

### Expected Behavior

In hybrid mode:
- ✅ **Reads**: Try SQLite first, fallback to JSON
- ✅ **Writes**: Write to both caches
- ✅ **Performance**: SQLite provides speed boost
- ✅ **Safety**: JSON provides fallback

---

## Phase 2: DB-Primary Mode (Week 2-3)

### Step 1: Update Configuration

```toml
[cache]
mode = "db-primary"  # SQLite primary, JSON fallback only
```

### Step 2: Verify SQLite Performance

Run benchmark to ensure SQLite is performing well:

```bash
python -m pytest tests/performance/bench_cache_db.py -v -s
```

Expected output:
```
SQLite read: 0.12ms/item
JSON read: 1.05ms/item
✅ SQLite is 8.8x faster
```

### Step 3: Monitor Error Rate

```bash
# Check logs for cache errors
grep "cache.*error" ~/.anivault/logs/anivault.log

# Should see minimal errors
```

### Step 4: Archive Old JSON Cache (Optional)

```bash
# Move JSON cache to archive
mv ~/.anivault/json_cache ~/.anivault/archive/json_cache_$(date +%Y%m%d)
```

⚠️ **Keep JSON cache** for rollback capability

---

## Phase 3: DB-Only Mode (Week 4)

### Step 1: Final Validation

Before switching to db-only:

```python
# Verify cache coverage
from anivault.services.sqlite_cache_db import SQLiteCacheDB

cache = SQLiteCacheDB(Path.home() / ".anivault" / "tmdb_cache.db")
info = cache.get_cache_info()

print(f"Total entries: {info['total_files']}")
print(f"Valid entries: {info['valid_entries']}")

# Should have significant cache population
assert info['valid_entries'] > 100, "Cache not sufficiently populated"

cache.close()
```

### Step 2: Update Configuration

```toml
[cache]
mode = "db-only"  # SQLite exclusively
```

### Step 3: Remove JSON Cache

```bash
# Archive JSON cache
tar -czf ~/.anivault/backups/json_cache_final_$(date +%Y%m%d).tar.gz ~/.anivault/json_cache

# Remove JSON cache directory
rm -rf ~/.anivault/json_cache
```

### Step 4: Celebrate! 🎉

Migration complete. Your cache is now SQLite-only.

---

## Rollback Procedures

### Rollback from DB-Only to Hybrid

```bash
# 1. Restore JSON cache from archive
tar -xzf ~/.anivault/backups/json_cache_final_YYYYMMDD.tar.gz -C ~/

# 2. Update config
# Change mode = "db-only" to mode = "hybrid"

# 3. Restart application
```

### Rollback from Hybrid to JSON-Only

```toml
[cache]
mode = "json-only"  # Revert to original system
```

### Emergency Rollback

If critical issues occur:

```bash
# 1. Quick config change
echo 'mode = "json-only"' >> ~/.anivault/config.toml

# 2. Restart application immediately

# 3. Investigate SQLite issues
python -m pytest tests/services/test_sqlite_cache_db.py -v
```

---

## Data Migration (Optional)

### Migrate Existing JSON Cache to SQLite

⚠️ **Note**: This is optional. Hybrid mode will naturally migrate data over time.

For immediate migration:

```python
#!/usr/bin/env python3
"""Migrate JSON cache to SQLite."""

import json
from pathlib import Path
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.cache_v2 import JSONCacheV2

def migrate_cache():
    """Migrate all JSON cache files to SQLite."""
    # Initialize both caches
    json_cache_path = Path.home() / ".anivault" / "json_cache"
    sqlite_cache_path = Path.home() / ".anivault" / "tmdb_cache.db"

    json_cache = JSONCacheV2(json_cache_path)
    sqlite_cache = SQLiteCacheDB(sqlite_cache_path)

    migrated = 0
    errors = 0

    # Migrate search cache
    for cache_file in (json_cache_path / "search").glob("*.json"):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                entry = json.load(f)

            # Extract key from filename (hash)
            key_hash = cache_file.stem

            # Store in SQLite
            sqlite_cache.set_cache(
                key=key_hash,  # Use hash as key
                data=entry.get("data", {}),
                cache_type="search",
                ttl_seconds=86400  # 24 hours default
            )

            migrated += 1

        except Exception as e:
            print(f"Error migrating {cache_file}: {e}")
            errors += 1

    # Migrate details cache
    for cache_file in (json_cache_path / "details").glob("*.json"):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                entry = json.load(f)

            key_hash = cache_file.stem

            sqlite_cache.set_cache(
                key=key_hash,
                data=entry.get("data", {}),
                cache_type="details",
                ttl_seconds=1209600  # 14 days default
            )

            migrated += 1

        except Exception as e:
            print(f"Error migrating {cache_file}: {e}")
            errors += 1

    sqlite_cache.close()

    print(f"\n✅ Migration complete!")
    print(f"Migrated: {migrated} files")
    print(f"Errors: {errors} files")

    return migrated, errors

if __name__ == "__main__":
    migrate_cache()
```

**Run migration**:
```bash
python scripts/migrate_cache.py
```

---

## Verification

### Verify Migration Success

```python
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from pathlib import Path

cache = SQLiteCacheDB(Path.home() / ".anivault" / "tmdb_cache.db")

# Check cache info
info = cache.get_cache_info()
print(f"""
Migration Verification:
- Total entries: {info['total_files']}
- Valid entries: {info['valid_entries']}
- Expired entries: {info['expired_entries']}
- Cache size: {info['total_size_bytes'] / (1024*1024):.2f} MB
""")

# Sample some data
sample_key = "search:tv:test:lang=ko"
sample_data = cache.get(sample_key, cache_type="search")

if sample_data:
    print("✅ Cache is working correctly")
else:
    print("⚠️ No data found for sample key")

cache.close()
```

---

## Troubleshooting

### Issue: Migration is slow

**Symptoms**: Taking hours to migrate cache

**Solutions**:
1. Use batch transactions:
   ```python
   # Wrap in transaction for speed
   sqlite_cache.conn.execute("BEGIN")
   # ... migrate files ...
   sqlite_cache.conn.execute("COMMIT")
   ```

2. Disable auto-cleanup during migration:
   ```python
   # Skip purge_expired() in __init__
   ```

---

### Issue: Disk space exhausted

**Symptoms**: "No space left on device"

**Solutions**:
1. Clean expired JSON entries first:
   ```python
   json_cache.purge_expired()
   ```

2. Migrate in batches:
   ```python
   # Migrate 1000 files at a time
   for batch in batches(cache_files, 1000):
       migrate_batch(batch)
   ```

---

### Issue: Cache hit ratio dropped

**Symptoms**: More API calls after migration

**Cause**: Cache keys might have changed

**Solutions**:
1. Check key generation:
   ```python
   from anivault.shared.cache_utils import generate_cache_key

   key = generate_cache_key("search", "tv", "test", {"language": "ko"})
   print(key)  # Verify format
   ```

2. Rebuild cache by re-fetching:
   ```bash
   # Clear and rebuild
   cache.clear()
   anivault match /path/to/anime  # Rebuild cache
   ```

---

## Success Criteria

Migration is successful when:

- ✅ Cache hit ratio > 80%
- ✅ Zero cache-related errors in logs
- ✅ Application performance improved (faster response times)
- ✅ Database file has secure permissions (600 on Unix)
- ✅ No API key leaks detected

---

## Timeline Example

**Real-world migration timeline**:

| Date | Phase | Activity | Status |
|------|-------|----------|--------|
| Day 1 | Pre-migration | Backup, verification | ✅ |
| Day 2-7 | Hybrid | Dual-cache mode | ✅ |
| Day 8 | Validation | Performance check | ✅ |
| Day 9-21 | DB-Primary | SQLite primary | ✅ |
| Day 22-28 | DB-Only | SQLite exclusively | ✅ |
| Day 29 | Cleanup | Archive JSON cache | ✅ |

**Total**: ~4 weeks for safe, gradual migration

---

## Support

If you encounter issues during migration:

1. **Check logs**: `~/.anivault/logs/anivault.log`
2. **Run diagnostics**: `python -m pytest tests/integration/test_cache_security.py`
3. **Rollback if needed**: See "Rollback Procedures" section
4. **Report issues**: Create GitHub issue with logs

---

## References

- [Cache System User Guide](../tmdb_cache_db.md)
- [Architecture Documentation](../architecture/cache_system.md)
- [Performance Benchmarks](../performance/cache_benchmark.md)

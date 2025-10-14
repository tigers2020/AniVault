# Settings Migration Guide

## Overview

AniVault settings module has been refactored to provide better organization and type safety. This guide helps you migrate your code to the new settings structure.

## What Changed

### New Settings Structure

The settings have been reorganized into domain-specific namespaces:

| Old Field | New Field | Status |
|-----------|-----------|--------|
| `settings.tmdb` | `settings.api.tmdb` | ⚠️ Deprecated |
| `settings.file_processing` | `settings.scan` | ⚠️ Deprecated |
| `settings.filter` | `settings.scan.filter_config` | ⚠️ Deprecated |

### New Namespaces

- **`settings.api`**: All external API configurations
  - `settings.api.tmdb`: TMDB API settings
- **`settings.scan`**: File scanning and processing
  - `settings.scan.filter_config`: File filtering settings

## Migration Examples

### TMDB Configuration

**Before:**
```python
from anivault.config import get_config

config = get_config()
api_key = config.tmdb.api_key
timeout = config.tmdb.timeout
rate_limit = config.tmdb.rate_limit_rps
```

**After:**
```python
from anivault.config import get_config

config = get_config()
api_key = config.api.tmdb.api_key
timeout = config.api.tmdb.timeout
rate_limit = config.api.tmdb.rate_limit_rps
```

### File Processing Configuration

**Before:**
```python
config = get_config()
batch_size = config.file_processing.batch_size
max_workers = config.file_processing.max_workers
```

**After:**
```python
config = get_config()
batch_size = config.scan.batch_size
max_workers = config.scan.max_workers
```

### Filter Configuration

**Before:**
```python
config = get_config()
extensions = config.filter.allowed_extensions
min_size = config.filter.min_file_size_mb
```

**After:**
```python
config = get_config()
extensions = config.scan.filter_config.allowed_extensions
min_size = config.scan.filter_config.min_file_size_mb
```

## Backward Compatibility

### Deprecation Warnings

The old field names still work but will emit `DeprecationWarning`:

```python
config = get_config()
# This works but emits a warning:
api_key = config.tmdb.api_key  # DeprecationWarning: Use settings.api.tmdb instead
```

### Suppressing Warnings (Temporary)

If you need to suppress warnings temporarily:

```python
import warnings

# Suppress for specific code block
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    api_key = config.tmdb.api_key
```

**Note:** This is only recommended during gradual migration. Update your code as soon as possible.

## Migration Checklist

- [ ] Search your codebase for `settings.tmdb` or `config.tmdb`
- [ ] Replace with `settings.api.tmdb` or `config.api.tmdb`
- [ ] Search for `settings.file_processing` or `config.file_processing`
- [ ] Replace with `settings.scan` or `config.scan`
- [ ] Search for `settings.filter` or `config.filter`
- [ ] Replace with `settings.scan.filter_config` or `config.scan.filter_config`
- [ ] Run tests to ensure everything works
- [ ] Remove any warning suppression code

## Timeline

- **v1.x**: Old field names deprecated (warnings emitted)
- **v2.0**: Old field names will be removed

## Migrated Files

The following files have already been migrated to the new structure:

- ✅ `src/anivault/services/tmdb_client.py` (Task 12: API compatibility)

## Need Help?

If you encounter issues during migration:

1. Check this guide for examples
2. Look at already-migrated files for reference
3. Run tests to catch any issues early
4. The old field names still work (with warnings) for gradual migration

## Technical Details

### Security Improvements

The refactoring also includes security enhancements:

- API keys are masked in logs and `repr()`
- API keys are excluded from file serialization
- Sensitive data is protected by default

### Type Safety

All settings models now have full type hints and validation:

```python
# Old: Dict[str, Any] (unsafe)
config: Dict[str, Any] = get_config()

# New: Settings (type-safe)
config: Settings = get_config()
api_key: str = config.api.tmdb.api_key  # Type-checked!
```

## Examples from Real Code

### Example 1: TMDB Client (Already Migrated)

```python
# File: src/anivault/services/tmdb_client.py
# Migrated to new Settings structure (Task 12: API compatibility)

# Before:
self.rate_limiter = TokenBucketRateLimiter(
    capacity=int(self.config.tmdb.rate_limit_rps),
    refill_rate=int(self.config.tmdb.rate_limit_rps),
)

# After:
self.rate_limiter = TokenBucketRateLimiter(
    capacity=int(self.config.api.tmdb.rate_limit_rps),
    refill_rate=int(self.config.api.tmdb.rate_limit_rps),
)
```

### Example 2: Settings Dialog (To Be Migrated)

```python
# File: src/anivault/gui/dialogs/settings_dialog.py
# TO BE MIGRATED

# Before:
api_key = settings.tmdb.api_key

# After:
api_key = settings.api.tmdb.api_key
```

## Summary

The new settings structure provides:

- ✅ Better organization (domain-specific namespaces)
- ✅ Improved type safety (full Pydantic validation)
- ✅ Enhanced security (API key masking)
- ✅ Backward compatibility (deprecated fields still work)
- ✅ Clear migration path (this guide + warnings)

**Recommendation**: Migrate your code incrementally. The old fields work during the transition period.

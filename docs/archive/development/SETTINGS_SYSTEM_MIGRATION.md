# Settings System Migration Guide

## Overview

AniVault's settings system has been refactored for thread-safety, security, and maintainability. This guide helps developers migrate to the new API.

## What Changed

### 1. Thread-Safe Singleton
**Before:**
```python
config = get_config()  # Not thread-safe
```

**After:**
```python
config = get_config()  # Thread-safe with RLock
```
✅ No code changes needed - backward compatible!

### 2. Configuration Updates
**Before (❌ Deprecated):**
```python
config = get_config()
config.tmdb.timeout = 60
config.to_toml_file("config/config.toml")  # Direct call
# WARNING: Global cache not updated!
```

**After (✅ Recommended):**
```python
from anivault.config.settings import update_and_save_config

def update_timeout(cfg):
    cfg.tmdb.timeout = 60

update_and_save_config(update_timeout)
# ✅ Validates, saves, AND updates cache
```

### 3. API Key Storage
**Before (🚨 SECURITY RISK):**
```toml
# config/config.toml
[tmdb]
api_key = "your_key_here"  # ❌ Never do this!  # pragma: allowlist secret
```

**After (✅ SECURE):**
```bash
# .env file only
TMDB_API_KEY=your_key_here
```

```toml
# config/config.toml
[tmdb]
# Note: NEVER set api_key here! Use .env file
api_key = ""
```

### 4. TMDB base_url Removed
**Before:**
```toml
[tmdb]
base_url = "https://api.themoviedb.org/3"  # ❌ Removed
```

**After:**
```toml
[tmdb]
# Note: base_url managed by tmdbv3api library
# No need to specify
```

## Migration Steps

### For Application Code

1. **Find direct `to_toml_file()` calls:**
```bash
grep -r "to_toml_file" src/
```

2. **Replace with `update_and_save_config()`:**
```python
# Old
config = get_config()
config.some_field = new_value
config.to_toml_file("config/config.toml")

# New
def update_field(cfg):
    cfg.some_field = new_value

update_and_save_config(update_field)
```

3. **Import the new helper:**
```python
from anivault.config.settings import update_and_save_config
```

### For Configuration Files

1. **Remove deprecated fields:**
```bash
# Remove from config/config.toml
- base_url line from [tmdb] section
```

2. **Add Pydantic extra='ignore':**
Already done! Old config files won't break.

### For API Keys

1. **Move API key to .env:**
```bash
# Create/edit .env file
echo "TMDB_API_KEY=your_actual_key" > .env  # pragma: allowlist secret
```

2. **Remove from config.toml:**
```toml
[tmdb]
api_key = ""  # Empty is OK
```

3. **Verify `.gitignore`:**
```bash
git check-ignore .env config/config.toml
# Both should be ignored
```

## Testing

### Run New Tests
```bash
# Thread-safety tests
pytest tests/config/test_settings_threadsafe.py -v

# Update helper tests
pytest tests/config/test_update_and_save_config.py -v

# Security tests
pytest tests/config/test_settings_security.py -v

# Parallel execution
pytest -n auto tests/config
```

### Expected Results
- All tests pass ✅
- No race conditions
- API keys never saved to files
- Config updates are atomic

## Benefits

### Thread-Safety
- ✅ Safe concurrent access from multiple threads
- ✅ Double-checked locking for performance
- ✅ No race conditions in GUI + background workers

### Security
- ✅ API keys NEVER saved to config files
- ✅ Secrets only in .env
- ✅ Pre-commit hooks prevent leaks

### Maintainability
- ✅ Single update API (`update_and_save_config`)
- ✅ Automatic validation before save
- ✅ Automatic cache refresh

### Developer Experience
- ✅ Backward compatible (extra='ignore')
- ✅ Clear error messages
- ✅ Comprehensive tests

## Troubleshooting

### Q: Config changes not reflected?
**A:** Ensure you're using `update_and_save_config()`, not direct `to_toml_file()`.

### Q: API key not working?
**A:** Check `.env` file exists and contains `TMDB_API_KEY=your_key`.

### Q: Tests failing with threading errors?
**A:** Run `pytest -n auto tests/config` to reproduce, check for global state.

### Q: Old config.toml with base_url?
**A:** No problem! Pydantic `extra='ignore'` handles it gracefully.

## References
- Security guide: `docs/security/GIT_HISTORY_CLEANUP_GUIDE.md`
- Thread-safety tests: `tests/config/test_settings_threadsafe.py`
- Update helper tests: `tests/config/test_update_and_save_config.py`

## Questions?
Ask in #dev-questions or create an issue.

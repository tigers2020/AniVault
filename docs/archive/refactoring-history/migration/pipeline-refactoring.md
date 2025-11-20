# Pipeline Refactoring Migration Guide

## Overview

The `core/pipeline/` module has been refactored to improve maintainability and organization. This guide helps you migrate your code to use the new import paths.

## What Changed?

### Before (Old Structure)
```
src/anivault/core/pipeline/
├── main.py (180 lines - orchestration logic)
├── utils.py (207 lines - utilities mixed together)
├── scanner.py (403 lines)
├── parser.py (222 lines)
├── collector.py (118 lines)
├── cache.py (139 lines)
└── ...
```

### After (New Structure)
```
src/anivault/core/pipeline/
├── main.py (17 lines - backward compatibility facade)
├── __init__.py (re-exports run_pipeline)
├── domain/
│   ├── __init__.py
│   ├── orchestrator.py (326 lines - orchestration + factory)
│   ├── lifecycle.py (220 lines - lifecycle management)
│   └── statistics.py (222 lines - statistics aggregation)
├── components/
│   ├── __init__.py
│   ├── scanner.py (403 lines)
│   ├── parser.py (222 lines)
│   ├── collector.py (118 lines)
│   └── ...
└── utils/
    ├── __init__.py
    ├── bounded_queue.py (80 lines)
    └── statistics.py (127 lines)
```

## Migration Steps

### 1. Update Import Paths

#### ✅ **Recommended: Use Top-Level Import**

```python
# OLD (still works, but deprecated)
from anivault.core.pipeline.main import run_pipeline

# NEW (recommended)
from anivault.core.pipeline import run_pipeline
```

#### Alternative Import Paths

```python
# Also valid
from anivault.core.pipeline.domain import run_pipeline
from anivault.core.pipeline.domain.orchestrator import run_pipeline
```

### 2. Component Imports

If you're importing pipeline components directly:

```python
# OLD
from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.parser import ParserWorkerPool

# NEW
from anivault.core.pipeline.components import DirectoryScanner, ParserWorkerPool
```

### 3. Utility Imports

```python
# OLD
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics

# NEW (unchanged - still works!)
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics
```

### 4. Statistics Functions

```python
# OLD
from anivault.core.pipeline.main import format_statistics

# NEW
from anivault.core.pipeline.domain import format_statistics
```

## Backward Compatibility

### Supported for 2 Major Versions

The old import path (`from anivault.core.pipeline.main import run_pipeline`) will continue to work for **2 major versions**. However:

- **New code** should use the recommended import paths
- **Existing code** can be updated gradually
- **No breaking changes** to the `run_pipeline` function signature

### What Still Works?

| Old Import | Status | Recommended Alternative |
|------------|--------|-------------------------|
| `from anivault.core.pipeline.main import run_pipeline` | ✅ Works (facade) | `from anivault.core.pipeline import run_pipeline` |
| `from anivault.core.pipeline.utils import BoundedQueue` | ✅ Works | Same (no change needed) |
| `from anivault.core.pipeline.scanner import DirectoryScanner` | ❌ Broken | `from anivault.core.pipeline.components import DirectoryScanner` |

## Example: Full Migration

### Before (Old Code)

```python
from anivault.core.pipeline.main import run_pipeline, format_statistics
from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.utils import ScanStatistics

def process_anime_directory(path: str) -> list:
    """Process anime files in directory."""
    extensions = [".mkv", ".mp4", ".avi"]
    results = run_pipeline(path, extensions, num_workers=4)
    return results
```

### After (New Code)

```python
# Recommended imports
from anivault.core.pipeline import run_pipeline
from anivault.core.pipeline.domain import format_statistics
from anivault.core.pipeline.components import DirectoryScanner
from anivault.core.pipeline.utils import ScanStatistics

def process_anime_directory(path: str) -> list:
    """Process anime files in directory."""
    extensions = [".mkv", ".mp4", ".avi"]
    results = run_pipeline(path, extensions, num_workers=4)
    return results
```

## Benefits of New Structure

### 1. **Better Organization**
- Clear separation of concerns (domain, components, utils)
- Easier to locate and modify code

### 2. **Improved Maintainability**
- Smaller files (<300 lines each)
- Single Responsibility Principle

### 3. **Better Testability**
- Easier to mock components
- Clearer test boundaries

### 4. **No Performance Impact**
- Same underlying implementation
- <1% overhead from additional imports

## Troubleshooting

### Import Error: Cannot import 'DirectoryScanner'

**Problem:**
```python
from anivault.core.pipeline.scanner import DirectoryScanner
# ImportError: No module named 'anivault.core.pipeline.scanner'
```

**Solution:**
```python
from anivault.core.pipeline.components import DirectoryScanner
```

### Import Error: Cannot import 'format_statistics' from 'main'

**Problem:**
```python
from anivault.core.pipeline.main import format_statistics
# ImportError: cannot import name 'format_statistics' from 'anivault.core.pipeline.main'
```

**Solution:**
```python
from anivault.core.pipeline.domain import format_statistics
```

## Testing Your Migration

Run the test suite to verify everything still works:

```bash
# Run all pipeline tests
pytest tests/core/pipeline/ -v

# Check for import errors
python -c "from anivault.core.pipeline import run_pipeline; print('✅ Import works!')"

# Run full test suite
pytest tests/ -v
```

## Timeline

- **Version 1.0.0**: Refactoring introduced
- **Version 2.0.0**: Deprecation warnings may be added
- **Version 3.0.0**: Old import paths may be removed (earliest)

## Questions?

If you encounter any issues during migration:
1. Check this migration guide
2. Review the test files in `tests/core/pipeline/`
3. See the architecture documentation in `docs/architecture/pipeline.md`
4. Open an issue on GitHub

## See Also

- [Architecture Documentation](../architecture/pipeline.md)
- [Refactoring Briefing](../refactoring-briefing.md)
- [Testing Guide](../testing/pipeline-testing.md)


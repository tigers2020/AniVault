# File Grouper Migration Guide

## 📋 Overview

The File Grouper module has been refactored to use the **Facade** and **Strategy** design patterns, providing better extensibility, testability, and maintainability. This guide covers what has changed and how to migrate your code if needed.

---

## ✅ Public API (Unchanged - No Migration Needed)

### Basic Usage

The following public APIs remain **100% backward compatible**. No code changes required.

```python
from anivault.core.file_grouper import FileGrouper, group_similar_files

# ✅ Still works exactly the same
grouper = FileGrouper()
groups = grouper.group_files(scanned_files)

# ✅ Still works exactly the same
groups = group_similar_files(scanned_files, similarity_threshold=0.85)
```

### Data Models

```python
from anivault.core.file_grouper import Group, GroupingEvidence

# ✅ Still works exactly the same
for group in groups:
    print(f"{group.title}: {len(group.files)} files")
    if group.evidence:
        print(f"  Confidence: {group.evidence.confidence}")
        print(f"  Method: {group.evidence.selected_matcher}")
```

---

## 🆕 New Features (Advanced API)

### 1. Dependency Injection

You can now inject custom implementations for testing or custom behavior.

```python
from anivault.core.file_grouper import (
    FileGrouper,
    GroupingEngine,
    DuplicateResolver,
    GroupNameManager,
)

# Custom configuration
custom_engine = GroupingEngine(matchers=[...], weights={...})
custom_resolver = DuplicateResolver(config=ResolutionConfig(...))

# Inject dependencies
grouper = FileGrouper(
    engine=custom_engine,
    resolver=custom_resolver,
    name_manager=GroupNameManager(),
)
```

### 2. Custom Matchers

Implement your own matching strategy by following the `BaseMatcher` protocol.

```python
from anivault.core.file_grouper import BaseMatcher, Group
from anivault.core.models import ScannedFile

class CustomMatcher:
    """Custom matcher implementation."""

    component_name: str = "custom"

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Your custom grouping logic."""
        # Implement your grouping algorithm
        groups = []
        # ... your logic here ...
        return groups

# Use with GroupingEngine
from anivault.core.file_grouper import GroupingEngine

engine = GroupingEngine(
    matchers=[CustomMatcher()],
    weights={"custom": 1.0}
)

grouper = FileGrouper(engine=engine)
```

### 3. Weighted Scoring

Combine multiple matchers with custom weights.

```python
from anivault.core.file_grouper import GroupingEngine
from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
from anivault.core.file_grouper.matchers.hash_matcher import HashSimilarityMatcher
from anivault.core.file_grouper.matchers.season_matcher import SeasonEpisodeMatcher

# Create matchers
title_matcher = TitleSimilarityMatcher(...)
hash_matcher = HashSimilarityMatcher(...)
season_matcher = SeasonEpisodeMatcher()

# Custom weights (must sum to 1.0)
custom_weights = {
    "title": 0.5,   # 50% weight on title similarity
    "hash": 0.3,    # 30% weight on hash matching
    "season": 0.2,  # 20% weight on season/episode
}

engine = GroupingEngine(
    matchers=[title_matcher, hash_matcher, season_matcher],
    weights=custom_weights,
)

grouper = FileGrouper(engine=engine)
groups = grouper.group_files(scanned_files)

# Access evidence
for group in groups:
    if group.evidence:
        print(f"Grouped by: {group.evidence.selected_matcher}")
        print(f"Confidence: {group.evidence.confidence}")
        print(f"Scores: {group.evidence.match_scores}")
```

### 4. Custom Duplicate Resolution

Control how duplicates are resolved.

```python
from anivault.core.file_grouper import DuplicateResolver, ResolutionConfig

# Prefer older versions and lower quality (unusual use case)
config = ResolutionConfig(
    prefer_higher_version=False,
    prefer_higher_quality=False,
    prefer_larger_size=False,
)

resolver = DuplicateResolver(config=config)
grouper = FileGrouper(resolver=resolver)
```

### 5. Evidence Tracking

Every group now includes evidence about why files were grouped together.

```python
from anivault.core.file_grouper import FileGrouper

grouper = FileGrouper()
groups = grouper.group_files(scanned_files)

for group in groups:
    print(f"\n{group.title}:")
    if group.evidence:
        print(f"  Matcher: {group.evidence.selected_matcher}")
        print(f"  Confidence: {group.evidence.confidence * 100:.1f}%")
        print(f"  Explanation: {group.evidence.explanation}")
        print(f"  All scores: {group.evidence.match_scores}")
```

---

## ❌ Breaking Changes (Internal Only)

### Removed Private Methods

The following **private methods** were removed from `FileGrouper`. These were never part of the public API.

If you were using these (you shouldn't have been), here's how to migrate:

| Old Private Method | Migration Path |
|--------------------|----------------|
| `_merge_similar_groups()` | Use `GroupingEngine` with appropriate matchers |
| `_group_by_normalized_hash()` | Use `HashSimilarityMatcher` |
| `_select_best_group_key()` | Use `GroupNameManager.merge_similar_group_names()` |
| `_update_group_names_with_parser()` | Use `TitleExtractor.extract_title_with_parser()` |
| `_extract_base_title()` | Use `TitleExtractor.extract_base_title()` |
| `_score_title_quality()` | Use `TitleQualityEvaluator.score_title_quality()` |
| `_is_cleaner_title()` | Use `TitleQualityEvaluator.is_cleaner_title()` |

### Example Migration

```python
# ❌ OLD (Never supported, but if you did this):
grouper = FileGrouper()
title = grouper._extract_base_title("some_file.mkv")  # Private method

# ✅ NEW (Proper way):
from anivault.core.file_grouper import TitleExtractor

extractor = TitleExtractor()
title = extractor.extract_base_title("some_file.mkv")
```

---

## 📊 Architecture Changes

### Before (Monolithic)

```
FileGrouper (812 lines)
├── group_files()
├── _merge_similar_groups()
├── _group_by_normalized_hash()
├── _merge_using_union_find()
├── _calculate_similarity()
├── _update_group_names_with_parser()
├── ... 17 private methods ...
└── (Complex, hard to test)
```

### After (Facade + Strategy)

```
FileGrouper (Facade - 208 lines)
├── engine: GroupingEngine
│   ├── TitleSimilarityMatcher
│   ├── HashSimilarityMatcher
│   └── SeasonEpisodeMatcher
├── resolver: DuplicateResolver
└── name_manager: GroupNameManager

✅ Clean separation of concerns
✅ Easy to test each component
✅ Easy to add new matchers
✅ Easy to customize behavior
```

---

## 🧪 Testing Your Migration

### Quick Compatibility Check

```python
# Test basic usage (should work without changes)
from anivault.core.file_grouper import FileGrouper, group_similar_files

grouper = FileGrouper()
assert hasattr(grouper, 'group_files')

# Test advanced API (new features)
from anivault.core.file_grouper import GroupingEngine, DuplicateResolver

engine = GroupingEngine(matchers=[], weights={"title": 1.0})
resolver = DuplicateResolver()

grouper = FileGrouper(engine=engine, resolver=resolver)
assert grouper.engine is engine
assert grouper.resolver is resolver

print("✅ All compatibility checks passed!")
```

### Run Existing Tests

```bash
# All existing tests should pass
pytest tests/unit/core/file_grouper/ -v

# Expected: 79/79 tests passed
```

---

## 📚 Additional Resources

### Code Examples

See the following for working examples:

- **Basic usage**: `src/anivault/gui/controllers/scan_controller.py`
- **CLI usage**: `src/anivault/cli/helpers/organize.py`
- **Custom matchers**: `src/anivault/core/file_grouper/matchers/`
- **Unit tests**: `tests/unit/core/file_grouper/`

### Related Documentation

- [Design Patterns](../docs/architecture/DESIGN_PATTERNS.md) *(if exists)*
- [Testing Guide](../docs/TESTING.md) *(if exists)*

---

## 💡 FAQs

### Q: Do I need to change my existing code?

**A:** No! If you're using the public API (`FileGrouper`, `group_similar_files`), everything works exactly as before.

### Q: Can I still use the old similarity_threshold parameter?

**A:** Yes! It's fully supported for backward compatibility:

```python
grouper = FileGrouper(similarity_threshold=0.9)
```

### Q: How do I access the new evidence feature?

**A:** It's automatic! Just check the `evidence` field on each `Group`:

```python
for group in groups:
    if group.evidence:
        print(f"Confidence: {group.evidence.confidence}")
```

### Q: Can I mix old and new APIs?

**A:** Yes! You can use basic `FileGrouper` for most cases and inject custom components when needed.

### Q: What if I need the old behavior exactly?

**A:** The default behavior is designed to be equivalent. If you notice differences, please file an issue!

---

## 🆘 Support

If you encounter issues during migration:

1. Check this guide for common patterns
2. Review the examples in `tests/unit/core/file_grouper/`
3. File an issue on GitHub with details

---

**Last Updated**: 2024-10-13
**Version**: v2.0 (Facade + Strategy Pattern)

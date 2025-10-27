# Extending File Grouper with Custom Matchers

## 📋 Overview

The File Grouper's **Strategy Pattern** architecture makes it easy to add new matching strategies without modifying existing code. This guide walks you through creating a custom matcher from scratch.

---

## 🎯 BaseMatcher Protocol

All matchers must implement the `BaseMatcher` protocol:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class BaseMatcher(Protocol):
    """Protocol that all matchers must implement."""

    component_name: str  # Unique identifier for this matcher

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files based on this matcher's similarity criteria.

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with similar files grouped together.
        """
        ...
```

**Key Points:**
- `component_name`: Used in `GroupingEvidence` and weight dictionary
- `match()`: Takes files, returns groups
- Duck typing: No explicit inheritance required

---

## 🛠️ Step-by-Step: Creating a Custom Matcher

### Example: MetadataQualityMatcher

Let's create a matcher that groups files by their metadata quality score.

#### Step 1: Create the Matcher File

```bash
# Create new file
touch src/anivault/core/file_grouper/matchers/quality_matcher.py
```

#### Step 2: Implement the Protocol

```python
# src/anivault/core/file_grouper/matchers/quality_matcher.py
"""Quality-based matcher for file grouping.

Groups files by metadata quality score, helping identify
files that need metadata enrichment.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.core.file_grouper.models import Group
    from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)


class MetadataQualityMatcher:
    """Matcher that groups files by metadata quality.

    Groups files into quality categories:
    - High quality: Complete metadata (title, season, episode)
    - Medium quality: Partial metadata (title only)
    - Low quality: No metadata or filename fallback only

    Attributes:
        component_name: Identifier for this matcher ("quality").

    Example:
        >>> matcher = MetadataQualityMatcher()
        >>> groups = matcher.match(scanned_files)
        >>> for group in groups:
        ...     print(f"{group.title}: {len(group.files)} files")
        High Quality: 45 files
        Medium Quality: 12 files
        Low Quality: 3 files
    """

    def __init__(self) -> None:
        """Initialize the quality matcher."""
        self.component_name = "quality"

    def _calculate_quality_score(self, file: ScannedFile) -> int:
        """Calculate metadata quality score for a file.

        Args:
            file: ScannedFile to score.

        Returns:
            Quality score (0-100):
            - 100: Complete metadata (title, season, episode, year)
            - 50: Partial metadata (title only)
            - 0: No metadata

        Example:
            >>> file = ScannedFile(...)
            >>> matcher._calculate_quality_score(file)
            75
        """
        if not hasattr(file, "metadata") or not file.metadata:
            return 0

        score = 0

        # Title present and not filename
        if (
            hasattr(file.metadata, "title")
            and file.metadata.title
            and file.metadata.title != file.file_path.name
        ):
            score += 40

        # Season present
        if hasattr(file.metadata, "season") and file.metadata.season is not None:
            score += 20

        # Episode present
        if hasattr(file.metadata, "episode") and file.metadata.episode is not None:
            score += 20

        # Year present
        if hasattr(file.metadata, "year") and file.metadata.year:
            score += 10

        # Quality tag present
        if hasattr(file.metadata, "quality") and file.metadata.quality:
            score += 10

        return score

    def _categorize_quality(self, score: int) -> str:
        """Categorize quality score into human-readable category.

        Args:
            score: Quality score (0-100).

        Returns:
            Quality category string.

        Example:
            >>> matcher._categorize_quality(85)
            'High Quality'
        """
        if score >= 80:
            return "High Quality"
        elif score >= 40:
            return "Medium Quality"
        else:
            return "Low Quality"

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files by metadata quality.

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects grouped by quality category.

        Example:
            >>> matcher = MetadataQualityMatcher()
            >>> groups = matcher.match(scanned_files)
            >>> len(groups)
            3  # High, Medium, Low
        """
        if not files:
            return []

        # Import here to avoid circular dependency
        from anivault.core.file_grouper.models import Group

        # Group files by quality category
        quality_groups: dict[str, list[ScannedFile]] = {}

        for file in files:
            score = self._calculate_quality_score(file)
            category = self._categorize_quality(score)

            if category not in quality_groups:
                quality_groups[category] = []

            quality_groups[category].append(file)

        # Convert to Group objects
        result = [
            Group(title=category, files=file_list)
            for category, file_list in quality_groups.items()
        ]

        logger.info(
            "Quality matcher grouped %d files into %d categories",
            len(files),
            len(result),
        )

        return result


__all__ = ["MetadataQualityMatcher"]
```

#### Step 3: Write Unit Tests

```python
# tests/unit/core/file_grouper/test_quality_matcher.py
"""Unit tests for MetadataQualityMatcher."""

from pathlib import Path

from anivault.core.file_grouper.matchers.quality_matcher import MetadataQualityMatcher
from anivault.core.models import ParsingResult, ScannedFile


def create_file(filename: str, **metadata_kwargs) -> ScannedFile:
    """Helper to create ScannedFile with custom metadata."""
    return ScannedFile(
        file_path=Path(filename),
        metadata=ParsingResult(**metadata_kwargs),
    )


class TestQualityScoring:
    """Test quality score calculation."""

    def test_score_complete_metadata(self) -> None:
        """Test scoring file with complete metadata."""
        matcher = MetadataQualityMatcher()
        file = create_file(
            "test.mkv",
            title="Attack on Titan",
            season=1,
            episode=1,
            year=2013,
            quality="1080p",
        )

        score = matcher._calculate_quality_score(file)
        assert score == 100

    def test_score_partial_metadata(self) -> None:
        """Test scoring file with partial metadata."""
        matcher = MetadataQualityMatcher()
        file = create_file("test.mkv", title="Attack on Titan")

        score = matcher._calculate_quality_score(file)
        assert score == 40

    def test_score_no_metadata(self) -> None:
        """Test scoring file with no metadata."""
        matcher = MetadataQualityMatcher()
        file = create_file("test.mkv")

        score = matcher._calculate_quality_score(file)
        assert score == 0


class TestQualityGrouping:
    """Test quality-based grouping."""

    def test_match_groups_by_quality(self) -> None:
        """Test grouping files by quality category."""
        matcher = MetadataQualityMatcher()

        high_quality = create_file(
            "high.mkv",
            title="Attack on Titan",
            season=1,
            episode=1,
        )
        medium_quality = create_file("medium.mkv", title="Death Note")
        low_quality = create_file("low.mkv")

        groups = matcher.match([high_quality, medium_quality, low_quality])

        assert len(groups) >= 2  # At least 2 quality categories
        titles = {group.title for group in groups}
        assert "High Quality" in titles or "Medium Quality" in titles


class TestProtocolCompliance:
    """Test BaseMatcher protocol compliance."""

    def test_has_component_name(self) -> None:
        """Test matcher has component_name."""
        matcher = MetadataQualityMatcher()
        assert hasattr(matcher, "component_name")
        assert matcher.component_name == "quality"

    def test_match_returns_groups(self) -> None:
        """Test match returns list of Group objects."""
        from anivault.core.file_grouper.models import Group

        matcher = MetadataQualityMatcher()
        file = create_file("test.mkv", title="Test")

        groups = matcher.match([file])
        assert isinstance(groups, list)
        assert all(isinstance(g, Group) for g in groups)
```

#### Step 4: Register with GroupingEngine

```python
# In your application code or configuration
from anivault.core.file_grouper import FileGrouper, GroupingEngine
from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
from anivault.core.file_grouper.matchers.hash_matcher import HashSimilarityMatcher
from anivault.core.file_grouper.matchers.season_matcher import SeasonEpisodeMatcher
from anivault.core.file_grouper.matchers.quality_matcher import MetadataQualityMatcher

# Create matchers
title_matcher = TitleSimilarityMatcher(...)
hash_matcher = HashSimilarityMatcher(...)
season_matcher = SeasonEpisodeMatcher()
quality_matcher = MetadataQualityMatcher()  # Your new matcher!

# Configure weights (must sum to 1.0)
weights = {
    "title": 0.5,      # 50% weight on title
    "hash": 0.2,       # 20% weight on hash
    "season": 0.2,     # 20% weight on season
    "quality": 0.1,    # 10% weight on quality
}

# Create engine with all matchers
engine = GroupingEngine(
    matchers=[title_matcher, hash_matcher, season_matcher, quality_matcher],
    weights=weights,
)

# Inject into FileGrouper
grouper = FileGrouper(engine=engine)

# Use as normal
groups = grouper.group_files(scanned_files)

# Access evidence
for group in groups:
    if group.evidence:
        print(f"Grouped by: {group.evidence.selected_matcher}")
        print(f"Quality score: {group.evidence.match_scores.get('quality', 0)}")
```

---

## 🧪 Testing Your Matcher

### 1. Unit Tests (Required)

**Minimum test coverage:**
- ✅ Protocol compliance (`component_name`, `match` signature)
- ✅ Empty input handling
- ✅ Single file handling
- ✅ Multiple files grouping
- ✅ Edge cases specific to your logic

```python
def test_protocol_compliance():
    """Verify matcher implements BaseMatcher protocol."""
    from anivault.core.file_grouper.matchers.base import BaseMatcher

    matcher = YourCustomMatcher()
    assert isinstance(matcher, BaseMatcher)
```

### 2. Integration Tests (Recommended)

```python
def test_integration_with_grouping_engine():
    """Test matcher works with GroupingEngine."""
    from anivault.core.file_grouper import GroupingEngine

    matcher = YourCustomMatcher()
    engine = GroupingEngine(
        matchers=[matcher],
        weights={"your_matcher": 1.0}
    )

    groups = engine.group_files(test_files)
    assert all(group.evidence for group in groups)
    assert all(group.evidence.selected_matcher == "your_matcher" for group in groups)
```

### 3. Manual Testing

```python
# scripts/test_custom_matcher.py
from pathlib import Path
from anivault.core.models import ScannedFile, ParsingResult
from anivault.core.file_grouper.matchers.your_matcher import YourCustomMatcher

# Create test data
test_files = [
    ScannedFile(
        file_path=Path("file1.mkv"),
        metadata=ParsingResult(title="Test 1"),
    ),
    # ... more test files ...
]

# Test matcher
matcher = YourCustomMatcher()
groups = matcher.match(test_files)

# Inspect results
for group in groups:
    print(f"\nGroup: {group.title}")
    print(f"Files: {len(group.files)}")
    for file in group.files:
        print(f"  - {file.file_path.name}")
```

---

## 💡 Best Practices

### 1. Keep Matchers Focused

**❌ DON'T**: Create a "do-everything" matcher

```python
class SuperMatcher:
    def match(self, files):
        # Groups by title, season, quality, hash, and more
        # ... 500 lines of complex logic ...
```

**✅ DO**: Create specific, single-purpose matchers

```python
class TitleMatcher:
    def match(self, files):
        # Only groups by title similarity

class QualityMatcher:
    def match(self, files):
        # Only groups by quality score
```

### 2. Handle Edge Cases

**Required edge cases:**
- Empty input (`files = []`)
- Single file (`files = [file]`)
- Files without required metadata
- Malformed data

```python
def match(self, files: list[ScannedFile]) -> list[Group]:
    # 1. Handle empty input
    if not files:
        return []

    # 2. Validate file metadata
    valid_files = [f for f in files if self._is_valid(f)]
    if not valid_files:
        logger.warning("No valid files for %s matcher", self.component_name)
        return []

    # 3. Your grouping logic here
    ...
```

### 3. Provide Meaningful Logging

```python
logger.info(
    "%s matcher grouped %d files into %d groups",
    self.component_name,
    len(files),
    len(result),
)

# For debugging
logger.debug(
    "Group '%s' has %d files with score %.2f",
    group.title,
    len(group.files),
    score,
)
```

### 4. Document Your Algorithm

```python
def match(self, files: list[ScannedFile]) -> list[Group]:
    """Group files by audio codec similarity.

    Algorithm:
        1. Extract codec from each file's metadata
        2. Normalize codec names (e.g., AAC variants)
        3. Group files with identical codecs
        4. Sort groups by codec preference (lossless > lossy)

    Args:
        files: List of ScannedFile objects to group.

    Returns:
        List of Group objects, one per codec type.
        Returns empty list if no files or no codec metadata.

    Example:
        >>> matcher = AudioCodecMatcher()
        >>> groups = matcher.match(files_with_audio)
        >>> [g.title for g in groups]
        ['FLAC', 'AAC', 'MP3']
    """
```

---

## 📚 Reference Implementations

Study these existing matchers for guidance:

### Simple Matcher: HashSimilarityMatcher

**Good for learning:**
- Basic grouping logic
- Single responsibility
- Error handling

```python
# src/anivault/core/file_grouper/matchers/hash_matcher.py
class HashSimilarityMatcher:
    """Groups files by normalized title hash."""

    component_name = "hash"

    def match(self, files):
        # Normalize titles → hash → group
        ...
```

### Complex Matcher: TitleSimilarityMatcher

**Good for advanced features:**
- Fuzzy matching (rapidfuzz)
- Quality evaluation
- Title extraction

```python
# src/anivault/core/file_grouper/matchers/title_matcher.py
class TitleSimilarityMatcher:
    """Groups files by fuzzy title similarity."""

    component_name = "title"

    def __init__(self, title_extractor, quality_evaluator, threshold=0.85):
        # Dependency injection
        ...

    def match(self, files):
        # Extract titles → calculate similarity → group
        ...
```

---

## 🔍 Debugging Tips

### 1. Test in Isolation First

```python
# Test just your matcher
matcher = YourCustomMatcher()
groups = matcher.match(test_files)
print(f"Created {len(groups)} groups")
```

### 2. Use Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now your logger.debug() calls will show
groups = matcher.match(files)
```

### 3. Inspect Evidence

```python
grouper = FileGrouper(engine=custom_engine)
groups = grouper.group_files(files)

for group in groups:
    if group.evidence:
        print(f"\nGroup: {group.title}")
        print(f"Selected: {group.evidence.selected_matcher}")
        print(f"Scores: {group.evidence.match_scores}")
        print(f"Confidence: {group.evidence.confidence:.2%}")
```

### 4. Compare with Existing Matchers

```python
# Test your matcher against title matcher
title_groups = title_matcher.match(files)
your_groups = your_matcher.match(files)

print(f"Title matcher: {len(title_groups)} groups")
print(f"Your matcher: {len(your_groups)} groups")

# Are the results reasonable?
```

---

## 🚀 Advanced Topics

### 1. Stateful Matchers

```python
class LearningMatcher:
    """Matcher that learns from user corrections."""

    def __init__(self):
        self.component_name = "learning"
        self.corrections: dict[str, str] = {}  # file -> correct group

    def record_correction(self, file: ScannedFile, correct_group: str):
        """Record user correction for future matching."""
        self.corrections[str(file.file_path)] = correct_group

    def match(self, files):
        # Use corrections to improve grouping
        ...
```

### 2. Async Matchers (Future)

```python
class AsyncAPIMatcher:
    """Matcher that calls external API for metadata."""

    async def match_async(self, files):
        # Make async API calls
        results = await asyncio.gather(*[
            self._fetch_metadata(file) for file in files
        ])
        # Group based on API results
        ...
```

### 3. Configurable Matchers

```python
@dataclass
class AudioMatcherConfig:
    prefer_lossless: bool = True
    min_bitrate: int = 128
    codec_preferences: list[str] = field(default_factory=lambda: ["FLAC", "AAC", "MP3"])

class AudioCodecMatcher:
    def __init__(self, config: AudioMatcherConfig | None = None):
        self.config = config or AudioMatcherConfig()
        self.component_name = "audio"

    def match(self, files):
        # Use self.config for decisions
        ...
```

---

## 📝 Checklist

Before submitting your custom matcher:

- [ ] Implements `BaseMatcher` protocol
- [ ] Has unique `component_name`
- [ ] `match()` returns `list[Group]`
- [ ] Handles empty input gracefully
- [ ] Handles files without required metadata
- [ ] Includes comprehensive docstrings
- [ ] Has unit tests (>80% coverage)
- [ ] Passes integration tests with `GroupingEngine`
- [ ] Follows existing code style (ruff, mypy)
- [ ] Includes usage example in docstring
- [ ] Adds logging for debugging

---

## 🆘 Getting Help

- **Study existing matchers**: `src/anivault/core/file_grouper/matchers/`
- **Run existing tests**: `pytest tests/unit/core/file_grouper/test_*_matcher.py -v`
- **Check architecture doc**: [file-grouper.md](../architecture/file-grouper.md)
- **File an issue**: If you encounter problems or have questions

---

**Happy Matcher Building! 🎉**

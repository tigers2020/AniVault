# Extending Scorers Guide

**Audience**: Developers adding custom matching logic
**Difficulty**: Intermediate
**Last Updated**: 2025-10-12

---

## Overview

The `MetadataEnricher` uses a **Strategy pattern** for scoring. You can easily add custom scorers to improve matching accuracy for your specific use cases.

---

## Quick Start

### 1. Create Your Scorer

```python
from anivault.services.metadata_enricher.scoring import BaseScorer, ScoreResult
from anivault.core.parser.models import ParsingResult
from typing import Any

class GenreScorer:
    """Score based on genre overlap."""

    component_name = "genre"  # Required
    weight = 0.15  # Required (0.0-1.0)

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: dict[str, Any],
    ) -> ScoreResult:
        """Calculate genre-based score.

        Returns:
            ScoreResult with score (0.0-1.0) and reasoning
        """
        # Extract genres (implement your logic)
        file_genres = self._extract_file_genres(file_info)
        tmdb_genres = tmdb_candidate.get("genre_ids", [])

        # Calculate overlap
        if not file_genres or not tmdb_genres:
            return ScoreResult(
                component=self.component_name,
                score=0.0,
                weight=self.weight,
                reason="No genre information available",
            )

        overlap = len(set(file_genres) & set(tmdb_genres))
        total = len(set(file_genres) | set(tmdb_genres))
        score = overlap / total if total > 0 else 0.0

        return ScoreResult(
            component=self.component_name,
            score=score,
            weight=self.weight,
            reason=f"Genre overlap: {overlap}/{total} ({score:.0%})",
        )

    def _extract_file_genres(self, file_info: ParsingResult) -> list[int]:
        """Extract genre IDs from file info."""
        # Implement your genre extraction logic
        return []
```

### 2. Register Your Scorer

```python
from anivault.services import MetadataEnricher
from anivault.services.metadata_enricher.scoring import (
    ScoringEngine,
    TitleScorer,
    YearScorer,
    MediaTypeScorer,
)

# Create custom engine with your scorer
engine = ScoringEngine(
    scorers=[
        TitleScorer(weight=0.5),      # Reduce title weight
        YearScorer(weight=0.2),        # Reduce year weight
        MediaTypeScorer(weight=0.1),
        GenreScorer(weight=0.15),      # Add your scorer
    ]
)

# Use custom engine
enricher = MetadataEnricher(scoring_engine=engine)
```

### 3. Test Your Scorer

```python
import pytest
from unittest.mock import Mock

def test_genre_scorer_full_overlap():
    """Test genre scorer with 100% overlap."""
    # Given
    scorer = GenreScorer()
    file_info = Mock(spec=ParsingResult)
    # Mock file_info with genres...

    tmdb_candidate = {
        "genre_ids": [16, 10759, 10765],  # Animation, Action, Sci-Fi
    }

    # When
    result = scorer.score(file_info, tmdb_candidate)

    # Then
    assert result.component == "genre"
    assert 0.8 <= result.score <= 1.0  # High overlap
    assert "overlap" in result.reason.lower()
```

---

## BaseScorer Protocol

### Required Attributes

```python
class YourScorer:
    component_name: str  # Unique identifier (e.g., "genre", "popularity")
    weight: float        # Scorer weight 0.0-1.0 (normalized by ScoringEngine)
```

### Required Method

```python
def score(
    self,
    file_info: ParsingResult,
    tmdb_candidate: dict[str, Any],
) -> ScoreResult:
    """Calculate score for the match.

    Args:
        file_info: Parsed anime file information
        tmdb_candidate: TMDB search result (dict from API)

    Returns:
        ScoreResult with:
        - component: Your component_name
        - score: 0.0-1.0 (0=no match, 1=perfect match)
        - weight: Your weight (for reference)
        - reason: Human-readable explanation
    """
```

---

## Best Practices

### 1. Return Meaningful Reasons

**Bad**:
```python
return ScoreResult(
    component="genre",
    score=0.75,
    weight=0.15,
    reason="Match",  # ❌ Vague
)
```

**Good**:
```python
return ScoreResult(
    component="genre",
    score=0.75,
    weight=0.15,
    reason="Genre overlap: 3/4 (75%)",  # ✅ Specific
)
```

### 2. Handle Missing Data Gracefully

```python
def score(self, file_info, tmdb_candidate):
    # Check if required data exists
    if not tmdb_candidate.get("popularity"):
        return ScoreResult(
            component=self.component_name,
            score=0.0,
            weight=self.weight,
            reason="Popularity data not available",
        )

    # Continue with scoring...
```

### 3. Normalize Scores to 0.0-1.0

```python
def score(self, file_info, tmdb_candidate):
    raw_score = some_calculation()  # e.g., 0-100
    normalized = min(raw_score / 100, 1.0)  # Ensure ≤1.0

    return ScoreResult(
        component=self.component_name,
        score=normalized,  # ✅ Always 0.0-1.0
        weight=self.weight,
        reason=f"Raw: {raw_score:.1f}, Normalized: {normalized:.2f}",
    )
```

### 4. Use Type Hints

```python
from typing import Any
from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.scoring import ScoreResult

class YourScorer:
    component_name: str = "your_component"
    weight: float = 0.2

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: dict[str, Any],
    ) -> ScoreResult:
        ...
```

---

## Example Scorers

### Example 1: Popularity Scorer

```python
class PopularityScorer:
    """Score by TMDB popularity (higher = better match)."""

    component_name = "popularity"
    weight = 0.1

    def score(self, file_info, tmdb_candidate):
        popularity = tmdb_candidate.get("popularity", 0)

        # Normalize: popularity typically 0-100+
        score = min(popularity / 100, 1.0)

        return ScoreResult(
            component=self.component_name,
            score=score,
            weight=self.weight,
            reason=f"Popularity: {popularity:.1f}/100",
        )
```

### Example 2: Vote Average Scorer

```python
class VoteAverageScorer:
    """Score by TMDB vote average (8+ = high confidence)."""

    component_name = "vote_average"
    weight = 0.05

    def score(self, file_info, tmdb_candidate):
        vote_avg = tmdb_candidate.get("vote_average", 0)

        # Normalize: 0-10 scale
        score = vote_avg / 10

        return ScoreResult(
            component=self.component_name,
            score=score,
            weight=self.weight,
            reason=f"Rating: {vote_avg:.1f}/10",
        )
```

### Example 3: Episode Count Scorer

```python
class EpisodeCountScorer:
    """Score by episode count proximity."""

    component_name = "episode_count"
    weight = 0.15

    def score(self, file_info, tmdb_candidate):
        # Extract episode count from file info
        file_episodes = getattr(file_info, "total_episodes", None)
        tmdb_episodes = tmdb_candidate.get("number_of_episodes")

        if not file_episodes or not tmdb_episodes:
            return ScoreResult(
                component=self.component_name,
                score=0.0,
                weight=self.weight,
                reason="Episode count unavailable",
            )

        # Calculate proximity score
        diff = abs(file_episodes - tmdb_episodes)
        score = max(0, 1.0 - (diff / 100))  # Penalty for large differences

        return ScoreResult(
            component=self.component_name,
            score=score,
            weight=self.weight,
            reason=f"Episodes: {file_episodes} vs {tmdb_episodes} (diff: {diff})",
        )
```

---

## Weight Normalization

The `ScoringEngine` automatically normalizes weights:

```python
# Your weights
scorers = [
    TitleScorer(weight=0.6),
    YearScorer(weight=0.3),
    GenreScorer(weight=0.2),  # Total: 1.1 (over 1.0!)
]

# Engine normalizes to:
# TitleScorer:  0.6 / 1.1 = 0.545
# YearScorer:   0.3 / 1.1 = 0.273
# GenreScorer:  0.2 / 1.1 = 0.182
# Total:        1.0
```

**Tip**: Don't worry about exact weights, just use relative importance!

---

## Testing Your Scorer

### Unit Test Template

```python
import pytest
from unittest.mock import Mock
from anivault.core.parser.models import ParsingResult

class TestYourScorer:
    """Unit tests for YourScorer."""

    def test_perfect_match(self):
        """Test perfect match returns score=1.0."""
        # Given
        scorer = YourScorer()
        file_info = Mock(spec=ParsingResult)
        # Setup perfect match scenario...

        tmdb_candidate = {...}  # Perfect match data

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.component == "your_component"
        assert result.score == 1.0
        assert result.weight == scorer.weight
        assert "perfect" in result.reason.lower() or "100%" in result.reason

    def test_no_match(self):
        """Test no match returns score=0.0."""
        # Similar structure...
        assert result.score == 0.0

    def test_partial_match(self):
        """Test partial match returns 0.0 < score < 1.0."""
        # Similar structure...
        assert 0.0 < result.score < 1.0

    def test_missing_data_graceful(self):
        """Test graceful handling of missing data."""
        scorer = YourScorer()
        file_info = Mock(spec=ParsingResult)
        tmdb_candidate = {}  # Empty data

        # Should not raise
        result = scorer.score(file_info, tmdb_candidate)

        # Usually returns 0.0 with explanation
        assert result.score == 0.0
        assert "not available" in result.reason.lower() or "missing" in result.reason.lower()
```

### Integration Test

```python
from anivault.services import MetadataEnricher
from anivault.services.metadata_enricher.scoring import ScoringEngine

@pytest.mark.asyncio
async def test_custom_scorer_integration():
    """Test custom scorer in full enrichment workflow."""
    # Given
    custom_engine = ScoringEngine(scorers=[
        TitleScorer(weight=0.5),
        YearScorer(weight=0.3),
        YourScorer(weight=0.2),
    ])
    enricher = MetadataEnricher(scoring_engine=custom_engine)
    file_info = ParsingResult(title="Attack on Titan")

    # When
    result = await enricher.enrich_metadata(file_info)

    # Then
    assert result.match_confidence > 0.0
    # Check that your scorer contributed
    # (inspect match_evidence if available)
```

---

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("anivault.services.metadata_enricher")
logger.setLevel(logging.DEBUG)
```

### 2. Inspect Match Evidence

```python
result = await enricher.enrich_metadata(file_info)

# Check which scorers contributed
if hasattr(result, "match_evidence"):
    for score in result.match_evidence.component_scores:
        print(f"{score.component}: {score.score:.2f} - {score.reason}")
```

### 3. Test Scorer Independently

```python
scorer = YourScorer()
result = scorer.score(file_info, tmdb_candidate)

print(f"Score: {result.score}")
print(f"Reason: {result.reason}")
```

---

## FAQ

### Q: Can I remove built-in scorers?

**A**: Yes! Just don't include them in your `ScoringEngine`:

```python
# Only use your scorers
engine = ScoringEngine(scorers=[
    YourScorer1(weight=0.6),
    YourScorer2(weight=0.4),
])
```

### Q: Can scorers depend on each other?

**A**: No. Scorers should be independent. If you need dependencies, create a single scorer that combines the logic.

### Q: How do I access TMDB client in my scorer?

**A**: Pass it via constructor:

```python
class CustomScorer:
    def __init__(self, tmdb_client: TMDBClient, weight: float = 0.2):
        self.tmdb_client = tmdb_client
        self.weight = weight
        self.component_name = "custom"

    def score(self, file_info, tmdb_candidate):
        # Use self.tmdb_client...
```

### Q: Performance impact of many scorers?

**A**: Minimal. Scorers run synchronously in a single loop. Typical overhead: <1ms per scorer.

---

## References

- [MetadataEnricher Architecture](../architecture/metadata-enricher.md)
- [BaseScorer Protocol](../../src/anivault/services/metadata_enricher/scoring/base_scorer.py)
- [Example Scorers](../../src/anivault/services/metadata_enricher/scoring/)
- [Testing Guide](../testing/README.md)

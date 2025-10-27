# MetadataEnricher Architecture

**Status**: Production
**Version**: 2.0 (Refactored)
**Last Updated**: 2025-10-12

---

## Overview

`MetadataEnricher` is a service that enriches parsed anime file metadata with additional information from the TMDB API. The service uses a **Facade pattern** to orchestrate multiple specialized modules:

- **Scoring Engine**: Calculates match confidence using pluggable strategies
- **TMDB Fetcher**: Handles all TMDB API interactions
- **Metadata Transformer**: Converts TMDB data to internal format
- **Batch Processor**: Manages concurrent batch processing

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     MetadataEnricher                        │
│                       (Facade - 233 lines)                  │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │  Public API                                       │    │
│  │  • enrich_metadata(file_info) → EnrichedMetadata │    │
│  │  • enrich_batch(file_infos) → List[EnrichedMeta] │    │
│  │  • enrich_metadata_sync() - sync wrapper         │    │
│  └───────────────────────────────────────────────────┘    │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │  Orchestration Logic                              │    │
│  │  1. Search candidates (TMDBFetcher)               │    │
│  │  2. Score & find best (ScoringEngine)             │    │
│  │  3. Fetch details (TMDBFetcher)                   │    │
│  │  4. Transform (MetadataTransformer)               │    │
│  └───────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
           │           │            │            │
           ▼           ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  TMDB    │ │ Scoring  │ │Transform │ │  Batch   │
    │ Fetcher  │ │  Engine  │ │   er     │ │Processor │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
         │             │
         │             ▼
         │      ┌──────────────┐
         │      │   Scorers    │
         │      │ ┌──────────┐ │
         │      │ │  Title   │ │
         │      │ │ Scorer   │ │
         │      │ └──────────┘ │
         │      │ ┌──────────┐ │
         │      │ │   Year   │ │
         │      │ │ Scorer   │ │
         │      │ └──────────┘ │
         │      │ ┌──────────┐ │
         │      │ │MediaType │ │
         │      │ │ Scorer   │ │
         │      │ └──────────┘ │
         │      └──────────────┘
         │
         ▼
   ┌──────────┐
   │  TMDB    │
   │   API    │
   └──────────┘
```

---

## Module Details

### 1. MetadataEnricher (Facade)

**Location**: `src/anivault/services/enricher.py`
**Lines**: 233 (down from 874)
**Purpose**: Orchestrate enrichment workflow with dependency injection

**Key Methods**:
```python
async def enrich_metadata(file_info: ParsingResult) -> EnrichedMetadata
def enrich_metadata_sync(file_info: ParsingResult) -> EnrichedMetadata
async def enrich_batch(file_infos: list[ParsingResult]) -> list[EnrichedMetadata]
```

**Dependencies** (all injectable):
- `TMDBFetcher`: TMDB API interactions
- `ScoringEngine`: Match scoring
- `BatchProcessor`: Concurrent processing

---

### 2. Scoring Module

**Location**: `src/anivault/services/metadata_enricher/scoring/`

#### BaseScorer Protocol
```python
class BaseScorer(Protocol):
    component_name: str
    weight: float

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: dict[str, Any]
    ) -> ScoreResult:
        ...
```

#### Implementations

| Scorer | Weight | Purpose | Coverage |
|--------|--------|---------|----------|
| `TitleScorer` | 0.6 | Fuzzy title matching | 91.67% |
| `YearScorer` | 0.3 | Release year matching | 98.15% |
| `MediaTypeScorer` | 0.1 | TV vs Movie matching | 100% |

#### ScoringEngine

**Purpose**: Composite scoring with weighted aggregation
**Coverage**: 94.87%

**Key Features**:
- Weighted score normalization
- Match evidence generation (transparency)
- Graceful scorer failure handling

---

### 3. TMDBFetcher

**Location**: `src/anivault/services/metadata_enricher/fetcher.py`
**Coverage**: 95.16%

**Responsibilities**:
- TMDB API search
- Details retrieval with fallback
- Error handling & retry logic

**Key Methods**:
```python
async def search(query: str) -> list[dict[str, Any]]
async def fetch_details(
    tmdb_id: int,
    media_type: str,
    fallback_data: dict | None = None
) -> TMDBMediaDetails
```

---

### 4. MetadataTransformer

**Location**: `src/anivault/services/metadata_enricher/transformer.py`
**Coverage**: 100%

**Purpose**: Convert TMDB data to internal `FileMetadata` format

**Handles**:
- Pydantic models → dict conversion
- Title/name fallback logic
- Date extraction and validation

---

### 5. BatchProcessor

**Location**: `src/anivault/services/metadata_enricher/batch_processor.py`
**Coverage**: 100%

**Purpose**: Concurrent batch processing with rate limiting

**Features**:
- `asyncio.Semaphore` for concurrency control (default: 5)
- Summary statistics (`BatchSummary`)
- Graceful error handling (partial failures allowed)

---

## Match Evidence (Transparency)

**Problem**: Original implementation was a "black box" - users couldn't see why a match was chosen.

**Solution**: `MatchEvidence` provides detailed scoring breakdown:

```python
@dataclass
class MatchEvidence:
    """Match scoring evidence for transparency."""
    file_title: str
    matched_title: str
    tmdb_id: int
    media_type: str
    total_score: float
    component_scores: list[ScoreResult]  # Individual scorer results
```

**Example**:
```json
{
  "file_title": "Attack on Titan",
  "matched_title": "Shingeki no Kyojin",
  "tmdb_id": 1429,
  "media_type": "tv",
  "total_score": 0.85,
  "component_scores": [
    {
      "component": "title",
      "score": 0.72,
      "weight": 0.6,
      "reason": "Fuzzy match: 72% similar"
    },
    {
      "component": "year",
      "score": 1.0,
      "weight": 0.3,
      "reason": "Exact year match: 2013"
    },
    {
      "component": "media_type",
      "score": 1.0,
      "weight": 0.1,
      "reason": "Type match: TV"
    }
  ]
}
```

---

## Dependency Injection

All modules support dependency injection for testability and flexibility:

```python
# Default usage (auto-wired)
enricher = MetadataEnricher()

# Custom configuration
enricher = MetadataEnricher(
    tmdb_client=custom_client,
    scoring_engine=custom_engine,
    min_confidence=0.5,
    batch_concurrency=10,
)

# Custom ScoringEngine
engine = ScoringEngine(
    scorers=[
        TitleScorer(weight=0.7),  # Increase title weight
        YearScorer(weight=0.2),
        MediaTypeScorer(weight=0.1),
        CustomScorer(weight=0.5),  # Add custom scorer
    ]
)
enricher = MetadataEnricher(scoring_engine=engine)
```

---

## Performance

### Metrics

| Metric | Before (874 lines) | After (233 lines) | Improvement |
|--------|-------------------|-------------------|-------------|
| **Lines of Code** | 874 | 233 | **-73.3%** |
| **Test Coverage** | ~40% | **94.96%** | **+137%** |
| **Module Count** | 1 | 9 | Modular |
| **Runtime Overhead** | Baseline | ≤5% | ✅ Within target |

### Benchmarks

Typical performance (real TMDB API calls):
- **Single file**: 200-500ms (network-dependent)
- **Batch (10 files)**: 1-2s with concurrency=5
- **Batch (50 files)**: 5-10s with concurrency=5

To run benchmarks:
```bash
python scripts/benchmark_enricher_performance.py
```

---

## Testing

### Coverage by Module

| Module | Tests | Coverage |
|--------|-------|----------|
| ScoringEngine | 20 | 94.87% |
| TitleScorer | 21 | 91.67% |
| YearScorer | 26 | 98.15% |
| MediaTypeScorer | 23 | 100% |
| TMDBFetcher | 16 | 95.16% |
| MetadataTransformer | 12 | 100% |
| BatchProcessor | 11 | 100% |
| **Total** | **146** | **94.96%** |

### Test Categories

1. **Unit Tests**: Each scorer, transformer, fetcher
2. **Integration Tests**: Full enrichment workflow
3. **Error Tests**: Network failures, invalid data, edge cases
4. **Performance Tests**: Benchmark scripts

---

## Migration Guide

### From v1.0 to v2.0

**Public API is 100% backward compatible.**

```python
# v1.0 (still works in v2.0)
from anivault.services import MetadataEnricher

enricher = MetadataEnricher()
result = enricher.enrich_metadata_sync(file_info)

# v2.0 (recommended async)
result = await enricher.enrich_metadata(file_info)
```

**Internal Changes** (only if you extended `MetadataEnricher`):
- `_calculate_title_similarity()`: ❌ Removed (use `TitleScorer`)
- `_calculate_match_score()`: ✅ Still exists (delegates to `ScoringEngine`)
- `_find_best_match()`: ✅ Still exists (simplified)

---

## Extending

See [Extending Scorers Guide](../dev-guide/extending-scorers.md) for details.

**Quick Example**:
```python
from anivault.services.metadata_enricher.scoring import BaseScorer, ScoreResult

class PopularityScorer:
    """Score by TMDB popularity."""
    component_name = "popularity"
    weight = 0.2

    def score(self, file_info, tmdb_candidate):
        popularity = tmdb_candidate.get("popularity", 0)
        score = min(popularity / 100, 1.0)  # Normalize
        return ScoreResult(
            component=self.component_name,
            score=score,
            weight=self.weight,
            reason=f"Popularity: {popularity:.1f}",
        )

# Use custom scorer
engine = ScoringEngine(scorers=[
    TitleScorer(weight=0.5),
    YearScorer(weight=0.2),
    MediaTypeScorer(weight=0.1),
    PopularityScorer(weight=0.2),
])
enricher = MetadataEnricher(scoring_engine=engine)
```

---

## References

- [Refactoring Plan](../../refactoring-plans/metadata-enricher-refactoring-plan.md)
- [Development Protocol](../protocols/DEVELOPMENT_PROTOCOL.md)
- [Testing Guide](../testing/README.md)

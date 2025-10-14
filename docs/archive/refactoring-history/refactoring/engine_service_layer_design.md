# MatchingEngine Service Layer Design

**Date**: 2025-10-09
**Status**: Draft
**Author**: AniVault Team
**Tag**: refactor-engine-service-layer
**Baseline**: Task 1 (Complexity Analysis Completed)

---

## 📊 1. Baseline Metrics

### Current State (Pre-Refactor)

| Metric | Value | Status |
|--------|-------|--------|
| **Lines of Code** | 873 | ❌ Too large |
| **Methods** | 18 | ❌ Too many |
| **Cyclomatic Complexity** | 평균 A (4.0) | ✅ Acceptable |
| **Maintainability Index** | A (44.99) | ⚠️ Could improve (target: 55+) |
| **Test Pass Rate** | 2/14 (14%) | ❌ Failing (async issues) |
| **High Complexity Functions** | 4 (B grade: CC 7-10) | ⚠️ Needs attention |

### Dependencies

```python
# External
from rapidfuzz import fuzz

# Internal
from anivault.core.matching.models import MatchResult, NormalizedQuery
from anivault.core.matching.scoring import calculate_confidence_score
from anivault.core.normalization import normalize_query_from_anitopy
from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult
```

**Key Dependencies**:
- `SQLiteCacheDB`: Database cache (read/write)
- `TMDBClient`: TMDB API client (async HTTP calls)
- `StatisticsCollector`: Performance tracking
- `calculate_confidence_score`: Scoring algorithm
- `normalize_query_from_anitopy`: Input normalization

---

## 🏗️ 2. Service Layer Architecture

### 2.1 Service Decomposition

**Decomposition Strategy**: Split by **responsibility** (not by complexity)

```
┌─────────────────────────────────────────────────────────────┐
│                  MatchingEngine (Facade)                    │
│  - Orchestrates workflow                                    │
│  - Handles async/await coordination                         │
│  - Manages DI (Dependency Injection)                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ TMDBSearch    │   │ Scoring       │   │ Filter        │
│ Service       │   │ Service       │   │ Service       │
│               │   │               │   │               │
│ - search_tmdb │   │ - score_*     │   │ - filter_*    │
│ - get_cache   │   │ - rank_*      │   │ - sort_*      │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────┐                       ┌───────────────┐
│ Fallback      │                       │ CacheAdapter  │
│ Strategy      │                       │               │
│ Service       │                       │ - Wraps DB    │
│               │                       │ - Key gen     │
│ - apply_*     │                       │ - Stats       │
└───────────────┘                       └───────────────┘
```

---

### 2.2 Service Definitions

#### 2.2.1 CacheAdapter

**Responsibility**: Abstract cache operations from business logic

```python
class CacheAdapter:
    """Cache abstraction layer."""

    def __init__(self, cache_db: SQLiteCacheDB, language: str = "ko-KR"):
        self.cache_db = cache_db
        self.language = language

    def get(self, title: str, cache_type: str = "search") -> dict | None:
        """Get cached data by title."""
        cache_key = self._generate_cache_key(title)
        return self.cache_db.get(cache_key, cache_type)

    def set(self, title: str, data: dict, cache_type: str = "search") -> None:
        """Set cache data."""
        cache_key = self._generate_cache_key(title)
        self.cache_db.set(cache_key, data, cache_type)

    def _generate_cache_key(self, title: str) -> str:
        """Generate language-aware cache key."""
        return f"{title}:lang={self.language}"

    def get_stats(self) -> dict:
        """Get cache statistics."""
        # Delegated to cache_db
        pass
```

**Complexity**: Low (CC ~2-3 per method)
**Lines**: ~50-60
**Dependencies**: `SQLiteCacheDB` only

---

#### 2.2.2 TMDBSearchService

**Responsibility**: TMDB API calls + cache integration

```python
class TMDBSearchService:
    """TMDB search operations."""

    def __init__(
        self,
        tmdb_client: TMDBClient,
        cache_adapter: CacheAdapter,
        statistics: StatisticsCollector
    ):
        self.tmdb_client = tmdb_client
        self.cache = cache_adapter
        self.statistics = statistics

    async def search(
        self,
        normalized_query: NormalizedQuery
    ) -> list[TMDBSearchResult]:
        """Search TMDB with cache support."""
        # 1. Check cache
        cached = self.cache.get(normalized_query.title)
        if cached:
            self.statistics.record_cache_hit("search")
            return self._deserialize_results(cached)

        # 2. Call TMDB API
        tv_results = await self.tmdb_client.search_tv(normalized_query.title)
        movie_results = await self.tmdb_client.search_movie(normalized_query.title)

        # 3. Combine & cache
        combined = tv_results + movie_results
        self.cache.set(normalized_query.title, self._serialize_results(combined))
        self.statistics.record_cache_miss("search")

        return combined

    def _serialize_results(self, results: list[TMDBSearchResult]) -> dict:
        """Convert results to cache format."""
        pass

    def _deserialize_results(self, cached_data: dict) -> list[TMDBSearchResult]:
        """Convert cache format to TMDBSearchResult objects."""
        pass
```

**Complexity**: Medium (CC ~4-6 per method)
**Lines**: ~60-80
**Dependencies**: `TMDBClient`, `CacheAdapter`, `StatisticsCollector`

---

#### 2.2.3 CandidateScoringService

**Responsibility**: Confidence score calculation + ranking

```python
class CandidateScoringService:
    """Candidate scoring and ranking."""

    def __init__(self, statistics: StatisticsCollector):
        self.statistics = statistics

    def score_candidates(
        self,
        candidates: list[TMDBSearchResult],
        normalized_query: NormalizedQuery
    ) -> list[ScoredSearchResult]:
        """Calculate confidence scores for candidates."""
        scored = []

        for candidate in candidates:
            score = calculate_confidence_score(
                candidate_title=candidate.title,
                original_title=candidate.original_title,
                query_title=normalized_query.title,
                candidate_year=candidate.year,
                query_year=normalized_query.year,
            )

            scored.append(ScoredSearchResult(
                **candidate.model_dump(),
                confidence_score=score
            ))

        return scored

    def rank_candidates(
        self,
        scored_candidates: list[ScoredSearchResult]
    ) -> list[ScoredSearchResult]:
        """Rank candidates by confidence score (descending)."""
        return sorted(
            scored_candidates,
            key=lambda x: x.confidence_score,
            reverse=True
        )

    def get_confidence_level(self, confidence_score: float) -> str:
        """Get confidence level label."""
        if confidence_score >= ConfidenceThresholds.HIGH:
            return "high"
        elif confidence_score >= ConfidenceThresholds.MEDIUM:
            return "medium"
        else:
            return "low"
```

**Complexity**: Low (CC ~2-3 per method)
**Lines**: ~50-60
**Dependencies**: `calculate_confidence_score`, `StatisticsCollector`

---

#### 2.2.4 CandidateFilterService

**Responsibility**: Year-based filtering, genre boost, partial match

```python
class CandidateFilterService:
    """Candidate filtering and sorting."""

    def __init__(self, statistics: StatisticsCollector):
        self.statistics = statistics

    def filter_by_year(
        self,
        scored_candidates: list[ScoredSearchResult],
        query_year: int | None
    ) -> list[ScoredSearchResult]:
        """Filter candidates by year match."""
        if not query_year:
            return scored_candidates

        year_matched = [
            c for c in scored_candidates
            if self._is_year_match(c.year, query_year)
        ]

        return year_matched if year_matched else scored_candidates

    def apply_genre_boost(
        self,
        scored_candidates: list[ScoredSearchResult],
        target_genre_ids: list[int]
    ) -> list[ScoredSearchResult]:
        """Boost confidence for anime genre matches."""
        for candidate in scored_candidates:
            if self._has_anime_genre(candidate.genre_ids, target_genre_ids):
                candidate.confidence_score += GenreConfig.ANIME_GENRE_BOOST

        return scored_candidates

    def apply_partial_match(
        self,
        scored_candidates: list[ScoredSearchResult],
        query_title: str
    ) -> list[ScoredSearchResult]:
        """Apply partial substring matching."""
        for candidate in scored_candidates:
            if self._is_partial_match(candidate.title, query_title):
                candidate.confidence_score += GenreConfig.PARTIAL_MATCH_BOOST

        return scored_candidates

    def _is_year_match(self, candidate_year: int | None, query_year: int) -> bool:
        """Check if years match within tolerance."""
        pass

    def _has_anime_genre(
        self,
        candidate_genres: list[int],
        target_genres: list[int]
    ) -> bool:
        """Check for anime genre overlap."""
        pass

    def _is_partial_match(self, candidate_title: str, query_title: str) -> bool:
        """Check for partial substring match."""
        pass
```

**Complexity**: Medium (CC ~5-7 per method)
**Lines**: ~70-90
**Dependencies**: `StatisticsCollector`, `rapidfuzz`

---

#### 2.2.5 FallbackStrategyService

**Responsibility**: Apply fallback strategies when initial match fails

```python
class FallbackStrategyService:
    """Fallback strategy orchestration."""

    def __init__(
        self,
        filter_service: CandidateFilterService,
        scoring_service: CandidateScoringService,
        statistics: StatisticsCollector
    ):
        self.filter_service = filter_service
        self.scoring_service = scoring_service
        self.statistics = statistics
        self.strategies = [
            GenreBoostStrategy(),
            PartialMatchStrategy(),
        ]

    def apply_fallbacks(
        self,
        candidates: list[ScoredSearchResult],
        normalized_query: NormalizedQuery
    ) -> ScoredSearchResult | None:
        """Apply fallback strategies sequentially."""
        for strategy in self.strategies:
            best_candidate = strategy.apply(
                candidates=candidates,
                query=normalized_query,
                filter_service=self.filter_service,
                scoring_service=self.scoring_service
            )

            if best_candidate:
                self.statistics.record_fallback_success(strategy.name)
                return best_candidate

        self.statistics.record_fallback_failure()
        return None


class FallbackStrategy(Protocol):
    """Fallback strategy interface."""

    @property
    def name(self) -> str:
        """Strategy name for logging."""
        ...

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
        filter_service: CandidateFilterService,
        scoring_service: CandidateScoringService
    ) -> ScoredSearchResult | None:
        """Apply strategy and return best candidate if found."""
        ...


class GenreBoostStrategy:
    """Boost confidence for anime genre matches."""

    @property
    def name(self) -> str:
        return "genre_boost"

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
        filter_service: CandidateFilterService,
        scoring_service: CandidateScoringService
    ) -> ScoredSearchResult | None:
        """Apply genre boost and re-rank."""
        # Boost anime genre
        boosted = filter_service.apply_genre_boost(
            candidates,
            target_genre_ids=GenreConfig.ANIME_GENRES
        )

        # Re-rank
        ranked = scoring_service.rank_candidates(boosted)

        # Return if above threshold
        best = ranked[0] if ranked else None
        if best and best.confidence_score >= ConfidenceThresholds.MEDIUM:
            return best

        return None


class PartialMatchStrategy:
    """Apply partial substring matching."""

    @property
    def name(self) -> str:
        return "partial_match"

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
        filter_service: CandidateFilterService,
        scoring_service: CandidateScoringService
    ) -> ScoredSearchResult | None:
        """Apply partial match and re-rank."""
        # Apply partial match boost
        boosted = filter_service.apply_partial_match(
            candidates,
            query_title=query.title
        )

        # Re-rank
        ranked = scoring_service.rank_candidates(boosted)

        # Return if above threshold
        best = ranked[0] if ranked else None
        if best and best.confidence_score >= ConfidenceThresholds.LOW:
            return best

        return None
```

**Complexity**: Medium (CC ~4-5 per method)
**Lines**: ~100-120
**Dependencies**: `CandidateFilterService`, `CandidateScoringService`, `StatisticsCollector`

---

#### 2.2.6 MatchingEngine (Facade)

**Responsibility**: Orchestrate the entire matching workflow

```python
class MatchingEngine:
    """Matching engine facade (orchestrator)."""

    def __init__(
        self,
        cache: SQLiteCacheDB,
        tmdb_client: TMDBClient,
        statistics: StatisticsCollector | None = None,
    ):
        """Initialize matching engine with dependency injection."""
        # Shared dependencies
        self.statistics = statistics or StatisticsCollector()

        # Service layer
        cache_adapter = CacheAdapter(cache, tmdb_client.language)

        self.search_service = TMDBSearchService(
            tmdb_client=tmdb_client,
            cache_adapter=cache_adapter,
            statistics=self.statistics
        )

        self.scoring_service = CandidateScoringService(
            statistics=self.statistics
        )

        self.filter_service = CandidateFilterService(
            statistics=self.statistics
        )

        self.fallback_service = FallbackStrategyService(
            filter_service=self.filter_service,
            scoring_service=self.scoring_service,
            statistics=self.statistics
        )

    async def find_match(
        self,
        anitopy_result: dict[str, Any]
    ) -> MatchResult | None:
        """Find matching TMDB entry for anime file.

        Workflow:
        1. Validate & normalize input
        2. Search TMDB (with cache)
        3. Score candidates
        4. Filter by year
        5. Rank by confidence
        6. Apply fallback if needed
        7. Validate final confidence
        8. Create match result
        """
        # 1. Validate & normalize
        normalized_query = self._validate_and_normalize_input(anitopy_result)
        if not normalized_query:
            return None

        # 2. Search
        candidates = await self.search_service.search(normalized_query)
        if not candidates:
            return None

        # 3. Score
        scored_candidates = self.scoring_service.score_candidates(
            candidates=candidates,
            normalized_query=normalized_query
        )

        # 4. Filter by year
        year_filtered = self.filter_service.filter_by_year(
            scored_candidates=scored_candidates,
            query_year=normalized_query.year
        )

        # 5. Rank
        ranked = self.scoring_service.rank_candidates(year_filtered)

        # 6. Get best candidate
        best_candidate = ranked[0] if ranked else None

        # 7. Apply fallback if confidence too low
        if not best_candidate or best_candidate.confidence_score < ConfidenceThresholds.LOW:
            best_candidate = self.fallback_service.apply_fallbacks(
                candidates=scored_candidates,
                normalized_query=normalized_query
            )

        # 8. Validate final confidence
        if not best_candidate or best_candidate.confidence_score < ConfidenceThresholds.LOW:
            return None

        # 9. Create match result
        match_result = self._create_match_result(best_candidate, normalized_query)
        self._record_successful_match(match_result)

        return match_result

    def _validate_and_normalize_input(
        self,
        anitopy_result: dict[str, Any]
    ) -> NormalizedQuery | None:
        """Validate and normalize input from anitopy."""
        if not anitopy_result:
            return None

        # Delegate to existing normalization
        return normalize_query_from_anitopy(anitopy_result)

    def _create_match_result(
        self,
        best_candidate: ScoredSearchResult,
        normalized_query: NormalizedQuery
    ) -> MatchResult:
        """Create final match result."""
        confidence_level = self.scoring_service.get_confidence_level(
            best_candidate.confidence_score
        )

        return MatchResult(
            tmdb_id=best_candidate.id,
            title=best_candidate.title,
            original_title=best_candidate.original_title,
            year=best_candidate.year,
            media_type=best_candidate.media_type,
            confidence_score=best_candidate.confidence_score,
            confidence_level=confidence_level,
            query_title=normalized_query.title,
            query_year=normalized_query.year,
        )

    def _record_successful_match(self, match_result: MatchResult) -> None:
        """Record successful match in statistics."""
        self.statistics.record_match_success(
            tmdb_id=match_result.tmdb_id,
            confidence=match_result.confidence_score
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics (delegated to cache adapter)."""
        return self.search_service.cache.get_stats()
```

**Complexity**: Low (CC ~3-4 for `find_match`, ~1-2 for helpers)
**Lines**: ~120-150
**Dependencies**: All 4 services + `normalize_query_from_anitopy`

---

## 🔄 3. Data Flow

### 3.1 Main Matching Flow

```
┌─────────────────┐
│ anitopy_result  │
│ (dict)          │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ MatchingEngine.find_match()             │
│ ┌──────────────────────────────────────┐│
│ │ 1. Validate & Normalize              ││
│ │    → NormalizedQuery                 ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 2. TMDBSearchService.search()        ││
│ │    → list[TMDBSearchResult]          ││
│ │    (cache hit/miss handled inside)   ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 3. CandidateScoringService           ││
│ │    .score_candidates()               ││
│ │    → list[ScoredSearchResult]        ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 4. CandidateFilterService            ││
│ │    .filter_by_year()                 ││
│ │    → list[ScoredSearchResult]        ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 5. CandidateScoringService           ││
│ │    .rank_candidates()                ││
│ │    → list[ScoredSearchResult]        ││
│ │    (sorted by confidence desc)       ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 6. Get best candidate                ││
│ │    best = ranked[0]                  ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 7. Check confidence threshold        ││
│ │    if too low:                       ││
│ │      FallbackStrategyService         ││
│ │      .apply_fallbacks()              ││
│ │      → ScoredSearchResult | None     ││
│ └──────────────────────────────────────┘│
│                 │                        │
│                 ▼                        │
│ ┌──────────────────────────────────────┐│
│ │ 8. Create MatchResult                ││
│ │    → MatchResult                     ││
│ └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ MatchResult     │
│ (or None)       │
└─────────────────┘
```

---

### 3.2 Cache Flow

```
┌─────────────────┐
│ Normalized      │
│ Query           │
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ TMDBSearchService.search()             │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ CacheAdapter.get(title)            │ │
│ │   │                                │ │
│ │   ├─ Hit? → Deserialize            │ │
│ │   │         → record_cache_hit()   │ │
│ │   │         → return results       │ │
│ │   │                                │ │
│ │   └─ Miss? → Continue              │ │
│ └────────────────────────────────────┘ │
│                 │                      │
│                 ▼                      │
│ ┌────────────────────────────────────┐ │
│ │ Fetch from TMDB API                │ │
│ │   - search_tv()                    │ │
│ │   - search_movie()                 │ │
│ └────────────────────────────────────┘ │
│                 │                      │
│                 ▼                      │
│ ┌────────────────────────────────────┐ │
│ │ CacheAdapter.set(title, results)   │ │
│ │   - Serialize results              │ │
│ │   - Write to cache_db              │ │
│ │   - record_cache_miss()            │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

### 3.3 Fallback Flow

```
┌─────────────────────────────┐
│ Scored Candidates           │
│ (low confidence)            │
└────────┬────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ FallbackStrategyService.apply_fallbacks()│
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ Strategy 1: GenreBoostStrategy       │ │
│ │   - apply_genre_boost()              │ │
│ │   - rank_candidates()                │ │
│ │   - check threshold                  │ │
│ │   - Found? → return                  │ │
│ └──────────────────────────────────────┘ │
│                 │                        │
│                 ▼ (not found)            │
│ ┌──────────────────────────────────────┐ │
│ │ Strategy 2: PartialMatchStrategy     │ │
│ │   - apply_partial_match()            │ │
│ │   - rank_candidates()                │ │
│ │   - check threshold                  │ │
│ │   - Found? → return                  │ │
│ └──────────────────────────────────────┘ │
│                 │                        │
│                 ▼ (not found)            │
│ ┌──────────────────────────────────────┐ │
│ │ All strategies exhausted             │ │
│ │   - record_fallback_failure()        │ │
│ │   - return None                      │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

---

## 🧩 4. Dependency Injection Strategy

### 4.1 Constructor Injection (Chosen Approach)

**Rationale**: Simple, explicit, testable

```python
# Facade (MatchingEngine) constructs all services
def __init__(self, cache: SQLiteCacheDB, tmdb_client: TMDBClient, statistics: StatisticsCollector | None = None):
    self.statistics = statistics or StatisticsCollector()

    # Build dependency tree
    cache_adapter = CacheAdapter(cache, tmdb_client.language)

    self.search_service = TMDBSearchService(tmdb_client, cache_adapter, self.statistics)
    self.scoring_service = CandidateScoringService(self.statistics)
    self.filter_service = CandidateFilterService(self.statistics)
    self.fallback_service = FallbackStrategyService(
        self.filter_service,
        self.scoring_service,
        self.statistics
    )
```

**Pros**:
- ✅ No external DI framework needed
- ✅ Explicit dependency graph
- ✅ Easy to test (mock services at facade level)
- ✅ Backward compatible (existing callers unchanged)

**Cons**:
- ⚠️ Facade has construction responsibility (acceptable for this scale)

---

### 4.2 Dependency Graph

```
SQLiteCacheDB ──┐
                ├──► CacheAdapter ──┐
TMDBClient ─────┘                   │
                                    ├──► TMDBSearchService ──┐
StatisticsCollector ────────────────┤                        │
                                    │                        │
                                    ├──► CandidateScoringService ──┐
                                    │                              │
                                    ├──► CandidateFilterService ────┤
                                    │                              │
                                    └──► FallbackStrategyService ───┤
                                               │                    │
                                               └────────────────────┤
                                                                    │
                                                                    ▼
                                                            MatchingEngine
                                                            (Facade)
```

**Shared Dependencies**:
- `StatisticsCollector`: Performance tracking (injected everywhere)
- `CacheAdapter`: Database abstraction (only in `TMDBSearchService`)

**Service Dependencies**:
- `FallbackStrategyService` depends on `Filter` + `Scoring`
- All others are independent

---

## ⚠️ 5. Risk Mitigation

### 5.1 Async Event Loop Issues

**Risk**: Services call `async` methods → event loop management complex

**Mitigation**:
- ✅ Keep async at facade level only (`MatchingEngine.find_match`)
- ✅ Services are sync (except `TMDBSearchService.search`)
- ✅ Use `await` at coordination points in facade

**Example**:
```python
# Facade (async entry point)
async def find_match(self, anitopy_result: dict) -> MatchResult | None:
    normalized = self._validate_and_normalize_input(anitopy_result)  # sync
    candidates = await self.search_service.search(normalized)        # async
    scored = self.scoring_service.score_candidates(candidates, normalized)  # sync
    ...
```

---

### 5.2 Cache Key Collisions

**Risk**: Different TMDB languages cached with same key

**Mitigation**:
- ✅ `CacheAdapter` includes language in key: `"{title}:lang={language}"`
- ✅ Adapter owns key generation logic (single source of truth)

---

### 5.3 Pydantic Model Conversion

**Risk**: Cache stores dicts, services expect Pydantic models

**Mitigation**:
- ✅ `TMDBSearchService` handles serialization/deserialization:
  - `_serialize_results()`: `list[TMDBSearchResult]` → `dict`
  - `_deserialize_results()`: `dict` → `list[TMDBSearchResult]`
- ✅ Cache is dumb (stores raw dicts), service is smart

---

### 5.4 Test Compatibility

**Risk**: 14 existing tests assume monolithic `MatchingEngine`

**Mitigation**:
- ✅ Facade maintains same public API: `find_match(anitopy_result)`
- ✅ Tests mock at facade level (no internal service visibility needed)
- ✅ Add unit tests for each service (total: 30+ tests)

---

## 📝 6. Implementation Plan

### Phase 1: Infrastructure (Task 2)
- [ ] Create `CacheAdapter` (test with mock `SQLiteCacheDB`)
- [ ] Test cache key generation
- [ ] Test get/set operations

### Phase 2: Search (Task 3)
- [ ] Create `TMDBSearchService`
- [ ] Implement cache hit/miss logic
- [ ] Test serialization/deserialization

### Phase 3: Scoring & Filtering (Tasks 4, 5)
- [ ] Create `CandidateScoringService`
- [ ] Create `CandidateFilterService`
- [ ] Test scoring accuracy
- [ ] Test filter behavior

### Phase 4: Fallback (Tasks 6, 7, 8, 9)
- [ ] Create `FallbackStrategy` protocol
- [ ] Implement `GenreBoostStrategy`
- [ ] Implement `PartialMatchStrategy`
- [ ] Create `FallbackStrategyService`
- [ ] Test strategy application

### Phase 5: Facade Integration (Task 10)
- [ ] Refactor `MatchingEngine` to facade
- [ ] Wire all services via DI
- [ ] Update integration tests
- [ ] Run full test suite
- [ ] Verify 0 test failures

---

## 📊 7. Success Metrics

| Metric | Current (Baseline) | Target (Post-Refactor) |
|--------|-------------------|------------------------|
| **Lines per Class** | 873 | ≤ 150 (facade), ≤ 80 (services) |
| **Methods per Class** | 18 | ≤ 10 (any class) |
| **Cyclomatic Complexity** | avg 4.0 (4 funcs at B) | avg ≤ 3.0 (all A) |
| **Maintainability Index** | 44.99 | ≥ 55.0 |
| **Test Pass Rate** | 2/14 (14%) | 100% (0 failures) |
| **Test Coverage** | Unknown | ≥ 80% (services) |
| **New Unit Tests** | 0 | ≥ 30 (6 per service) |

---

## 🔗 8. References

- **PRD**: `.taskmaster/docs/refactor-engine-service-layer-prd.txt`
- **Task List**: `.taskmaster/tasks/tasks.json` (tag: `refactor-engine-service-layer`)
- **Current Engine**: `src/anivault/core/matching/engine.py`
- **Existing Tests**: `tests/core/matching/test_engine.py`
- **Complexity Report**: radon cc output (above)

---

**Status**: ✅ Baseline Complete, Design Approved (Pending Round 2 Consensus)

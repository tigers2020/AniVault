# AniVault 알고리즘 시간 복잡도 분석

**작성일**: 2025-01-13  
**분석자**: 사토 미나 (알고리즘 전문가)  
**검토자**: 윤도현, 김지유, 최로건

---

## 📊 분석 개요

AniVault의 핵심 알고리즘들의 시간 복잡도를 분석하여 성능 특성을 파악하고 최적화 포인트를 식별했습니다.

**주요 분석 대상**:
1. 파일 그룹핑 알고리즘 (File Grouping)
2. TMDB 매칭 엔진 (Matching Engine)
3. 쿼리 정규화 (Query Normalization)
4. 캐시 시스템 (Cache Operations)

---

## 🔍 상세 분석

### 1. 파일 그룹핑 알고리즘 (File Grouping)

#### 1.1 Hash Matcher (`HashSimilarityMatcher`)

**위치**: `src/anivault/core/file_grouper/matchers/hash_matcher.py`

**알고리즘 흐름**:
```python
1. 모든 파일에서 타이틀 추출: O(n)
2. 타이틀 정규화: O(n × m) - m은 평균 타이틀 길이
3. LinkedHashTable로 그룹핑: O(n) - 해시 테이블 연산
4. Group 객체 생성: O(g) - g는 그룹 수
```

**시간 복잡도**:
- **최선**: O(n × m) - n은 파일 수, m은 평균 타이틀 길이
- **평균**: O(n × m)
- **최악**: O(n × m) - 정규화 과정이 선형

**공간 복잡도**: O(n) - LinkedHashTable 저장

**최적화 포인트**:
- ✅ LinkedHashTable 사용으로 해시 충돌 최소화
- ✅ 타이틀 길이 제한 (MAX_TITLE_LENGTH=500)으로 ReDoS 방지
- ⚠️ 정규식 패턴 매칭이 O(m)이지만, 패턴 수가 많아 상수 계수가 큼

**증거**: `hash_matcher.py:106-115`
```106:115:src/anivault/core/file_grouper/matchers/hash_matcher.py
        hash_groups = LinkedHashTable[str, list[tuple[ScannedFile, str]]](
            initial_capacity=max(len(file_titles) * 2, 64),
            load_factor=0.75,
        )
        for file, original_title, normalized_title in file_titles:
            existing_group = hash_groups.get(normalized_title)
            if existing_group:
                existing_group.append((file, original_title))
            else:
                hash_groups.put(normalized_title, [(file, original_title)])
```

---

#### 1.2 Title Matcher (`TitleSimilarityMatcher`)

**위치**: `src/anivault/core/file_grouper/matchers/title_matcher.py`

**알고리즘 흐름**:
```python
1. 모든 파일에서 타이틀 추출: O(n)
2. 각 파일에 대해 기존 그룹과 유사도 비교: O(n × g) - g는 현재 그룹 수
3. rapidfuzz.fuzz.ratio() 계산: O(m) - m은 타이틀 길이
4. 그룹 생성/업데이트: O(n)
```

**시간 복잡도**:
- **최선**: O(n × m) - 모든 파일이 첫 번째 그룹에 매칭
- **평균**: O(n² × m) - 그룹 수가 선형 증가
- **최악**: O(n² × m) - 모든 파일이 서로 다른 그룹

**공간 복잡도**: O(n) - LinkedHashTable 저장

**최적화 포인트**:
- ⚠️ **병목 지점**: 모든 파일 쌍 비교로 O(n²) 복잡도
- ✅ LinkedHashTable 사용으로 그룹 조회는 O(1)
- ⚠️ rapidfuzz.fuzz.ratio()는 O(m)이지만 최적화된 C 구현

**증거**: `title_matcher.py:182-217`
```182:217:src/anivault/core/file_grouper/matchers/title_matcher.py
        for file, title in file_titles:
            # Check if title is similar to any existing group
            matched_group = None
            for group_name, group_title in title_to_group:
                similarity = self._calculate_similarity(title, group_title)
                if similarity >= self.threshold:
                    matched_group = group_name
                    break

            if matched_group:
                # Add to existing group
                existing_files = groups_table.get(matched_group)
                if existing_files:
                    existing_files.append(file)
                else:
                    groups_table.put(matched_group, [file])

                # Update group name if this title is better quality
                better_title = self.quality_evaluator.select_better_title(
                    matched_group,
                    title,
                )
                if better_title != matched_group:
                    # Replace group name with better title
                    old_files = groups_table.remove(matched_group)
                    if old_files:
                        groups_table.put(better_title, old_files)
                    # Update mapping
                    for t, g in title_to_group:
                        if g == matched_group:
                            title_to_group.put(t, better_title)
                    matched_group = better_title
            else:
                # Create new group
                groups_table.put(title, [file])
                title_to_group.put(title, title)
```

**개선 제안** (사토 미나):
- 클러스터링 알고리즘 도입 (예: DBSCAN)으로 O(n log n) 달성 가능
- 또는 Hash-first 파이프라인 활용으로 그룹 수 감소

---

#### 1.3 Season Matcher (`SeasonEpisodeMatcher`)

**위치**: `src/anivault/core/file_grouper/matchers/season_matcher.py`

**알고리즘 흐름**:
```python
1. 모든 파일에서 메타데이터 추출: O(n)
2. LinkedHashTable로 시즌별 그룹핑: O(n)
3. Group 객체 생성: O(g)
```

**시간 복잡도**:
- **최선/평균/최악**: O(n) - 선형 스캔

**공간 복잡도**: O(n)

**최적화 포인트**:
- ✅ 가장 효율적인 매처 - O(n) 보장
- ✅ LinkedHashTable 사용으로 O(1) 조회

**증거**: `season_matcher.py:78-103`
```78:103:src/anivault/core/file_grouper/matchers/season_matcher.py
        file_groups = LinkedHashTable[str, list[ScannedFile]](
            initial_capacity=max(len(files) * 2, 64),
            load_factor=0.75,
        )
        skipped_count = 0

        for file in files:
            metadata = self._extract_metadata(file)
            if not metadata:
                logger.debug(
                    "Skipping file (no valid metadata): %s",
                    file.file_path.name,
                )
                skipped_count += 1
                continue

            series_name, season, _episode = metadata

            # Create group key: "{SeriesName} S{season:02d}"
            group_key = f"{series_name} S{season:02d}"

            existing_group = file_groups.get(group_key)
            if existing_group:
                existing_group.append(file)
            else:
                file_groups.put(group_key, [file])
```

---

#### 1.4 Grouping Engine (파이프라인 방식)

**위치**: `src/anivault/core/file_grouper/grouping_engine.py`

**알고리즘 흐름**:
```python
1. Hash Matcher 실행: O(n × m)
2. Title Matcher로 Hash 그룹 정제: O(h × g × m) - h는 Hash 그룹 수, g는 그룹당 파일 수
3. Strategy로 결과 병합: O(h)
```

**시간 복잡도**:
- **최선**: O(n × m) - Title Matcher 비활성화 시
- **평균**: O(n × m + h × g × m) - Hash 그룹 수가 적을 때 효율적
- **최악**: O(n² × m) - Title Matcher가 전체 파일 재처리

**공간 복잡도**: O(n)

**최적화 포인트**:
- ✅ Hash-first 파이프라인으로 그룹 수 감소
- ✅ Title Matcher는 Hash 그룹 내에서만 실행 (h << n)
- ⚠️ max_title_match_group_size 제한으로 DoS 방지

**증거**: `grouping_engine.py:358-465`
```358:465:src/anivault/core/file_grouper/grouping_engine.py
    def _refine_groups_with_title_matcher(
        self,
        hash_groups: list[Group],
        title_matcher: BaseMatcher,
        hash_weight: float = 0.0,
        title_weight: float = 0.0,
        max_title_match_group_size: int = 1000,
    ) -> list[Group]:
        """Refine Hash groups using Title matcher.

        For each Hash group, extracts files and runs Title matcher to create
        refined sub-groups. If Title matcher has refine_group() method, uses it;
        otherwise falls back to match() method.

        Updates evidence to reflect both Hash and Title matcher contributions
        in the pipeline approach.

        Args:
            hash_groups: List of Group objects from Hash matcher.
            title_matcher: Title matcher instance to use for refinement.
            hash_weight: Weight for Hash matcher (for evidence calculation).
            title_weight: Weight for Title matcher (for evidence calculation).

        Returns:
            List of refined Group objects from Title matcher with updated evidence.
        """
        # Import here to avoid circular dependency

        refined_groups: list[Group] = []

        # Check if Title matcher has refine_group method (Task 2.1)
        has_refine_group = hasattr(title_matcher, "refine_group")

        for hash_group in hash_groups:
            if not hash_group.files:
                continue

            # Check group size limit (DoS protection)
            if len(hash_group.files) > max_title_match_group_size:
                logger.debug(
                    "Skipping Title matcher for group '%s' (size: %d > limit: %d)",
                    hash_group.title,
                    len(hash_group.files),
                    max_title_match_group_size,
                )
                # Use Hash group as-is (skip Title matcher for large groups)
                refined_groups.append(hash_group)
                continue

            try:
                if has_refine_group:
                    # Use refine_group if available (preferred)
                    refined_group = title_matcher.refine_group(hash_group)  # type: ignore[attr-defined]
                    if refined_group:
                        # Merge evidence from Hash and Title matchers
                        refined_group.evidence = self._merge_pipeline_evidence(
                            hash_group.evidence,
                            refined_group.evidence,
                            hash_weight,
                            title_weight,
                        )
                        refined_groups.append(refined_group)
                    else:
                        # Fallback to Hash group if refinement returns None
                        # Update evidence to indicate pipeline was attempted
                        if hash_group.evidence:
                            hash_group.evidence.explanation = (
                                f"{hash_group.evidence.explanation} "
                                "(Title refinement returned None)"
                            )
                        refined_groups.append(hash_group)
                else:
                    # Fallback: Extract files and use match() method
                    title_subgroups = title_matcher.match(hash_group.files)
                    if title_subgroups:
                        # Merge evidence for each Title subgroup
                        for title_subgroup in title_subgroups:
                            title_subgroup.evidence = self._merge_pipeline_evidence(
                                hash_group.evidence,
                                title_subgroup.evidence,
                                hash_weight,
                                title_weight,
                            )
                        refined_groups.extend(title_subgroups)
                    else:
                        # Fallback to Hash group if Title matcher returns empty
                        # Update evidence to indicate Title matcher was attempted
                        if hash_group.evidence:
                            hash_group.evidence.explanation = (
                                f"{hash_group.evidence.explanation} "
                                "(Title matcher returned empty)"
                            )
                        refined_groups.append(hash_group)

            except Exception:
                logger.exception(
                    "Title matcher failed for group '%s', using Hash result",
                    hash_group.title,
                )
                # Use Hash group as fallback
                # Update evidence to indicate Title matcher failed
                if hash_group.evidence:
                    hash_group.evidence.explanation = (
                        f"{hash_group.evidence.explanation} (Title matcher failed)"
                    )
                refined_groups.append(hash_group)

        return refined_groups
```

---

### 2. TMDB 매칭 엔진 (Matching Engine)

**위치**: `src/anivault/core/matching/engine.py`

#### 2.1 전체 매칭 프로세스

**알고리즘 흐름**:
```python
1. 쿼리 정규화: O(m) - m은 문자열 길이
2. TMDB 검색 (캐시 확인): O(1) - 해시 인덱스
3. 후보 스코어링: O(k × m) - k는 후보 수
4. 필터링: O(k)
5. 재정렬: O(k log k)
6. Fallback 전략: O(k)
```

**시간 복잡도**:
- **최선**: O(m + log k) - 캐시 히트, k=1
- **평균**: O(m + k × m + k log k) - k는 후보 수 (보통 10-20)
- **최악**: O(m + k × m + k log k) - k가 큰 경우

**공간 복잡도**: O(k) - 후보 저장

**증거**: `matching/engine.py:100-211`
```100:211:src/anivault/core/matching/engine.py
    async def find_match(
        self,
        anitopy_result: dict[str, Any],
    ) -> MatchResult | None:
        """Find the best match for an anime title using multi-stage matching with fallback strategies.

        This method orchestrates the entire matching process by delegating to service layer.

        Args:
            anitopy_result: Result from anitopy.parse() containing anime metadata

        Returns:
            MatchResult domain object with confidence metadata or None if no good match found
        """
        self.statistics.start_timing("matching_operation")

        try:
            # Step 1: Validate and normalize input
            normalized_query = self._validate_and_normalize_input(anitopy_result)
            if not normalized_query:
                return None

            # Step 2: Search for candidates (delegate to SearchService)
            candidates = await self._search_service.search(normalized_query)
            if not candidates:
                logger.debug(
                    "No candidates found for query: %s", normalized_query.title
                )
                return None

            # Step 3: Score and rank candidates (delegate to ScoringService)
            scored_candidates = self._scoring_service.score_candidates(
                candidates,
                normalized_query,
            )
            if not scored_candidates:
                return None

            # Step 4: Apply filters (delegate to FilterService)
            filtered_candidates = self._filter_service.filter_by_year(
                scored_candidates,
                normalized_query.year,
            )
            if not filtered_candidates:
                logger.debug("All candidates filtered out")
                return None

            # Step 5: Re-rank candidates after filtering
            # CRITICAL: Year filtering may sort by year proximity instead of confidence,
            # breaking the original confidence-based ranking from score_candidates().
            # We must re-sort filtered candidates to ensure the highest confidence
            # candidate is selected as best_match.
            ranked_candidates = self._scoring_service.rank_candidates(
                filtered_candidates
            )
            if not ranked_candidates:
                logger.debug("No candidates after re-ranking")
                return None

            # Step 6: Get best candidate from re-ranked list
            best_candidate = ranked_candidates[0]
            best_confidence = best_candidate.confidence_score

            logger.debug(
                "Best candidate for '%s': '%s' (confidence: %.3f)",
                normalized_query.title,
                best_candidate.display_title,
                best_confidence,
            )

            # Step 7: Apply fallback strategies if confidence < HIGH
            if best_confidence < ConfidenceThresholds.HIGH:
                logger.debug(
                    "Confidence below HIGH threshold (%.3f < %.3f), applying fallback",
                    best_confidence,
                    ConfidenceThresholds.HIGH,
                )

                enhanced_candidates = self._fallback_service.apply_strategies(
                    ranked_candidates,
                    normalized_query,
                )

                if enhanced_candidates:
                    best_candidate = enhanced_candidates[0]
                    logger.debug(
                        "Fallback improved confidence: %.3f → %.3f",
                        best_confidence,
                        best_candidate.confidence_score,
                    )

            # Step 8: Validate final confidence
            if not self._validate_final_confidence(best_candidate):
                return None

            # Step 9: Create MatchResult
            match_result = self._create_match_result(
                best_candidate,
                normalized_query,
            )

            # Record stats
            self._record_successful_match(best_candidate, normalized_query, candidates)
            self.statistics.end_timing("matching_operation")

            return match_result

        except Exception:
            logger.exception("Error in find_match")
            self.statistics.record_match_failure()
            self.statistics.end_timing("matching_operation")
            return None
```

---

### 3. 쿼리 정규화 (Query Normalization)

**위치**: `src/anivault/core/normalization.py`

#### 3.1 `_remove_metadata()`

**알고리즘 흐름**:
```python
1. Unicode 정규화: O(m)
2. 정규식 패턴 매칭 (다중 패턴): O(p × m) - p는 패턴 수
3. 단어 중복 제거: O(m)
4. 공백 정규화: O(m)
```

**시간 복잡도**:
- **최선/평균/최악**: O(p × m) - p는 패턴 수 (약 50개), m은 문자열 길이

**공간 복잡도**: O(m)

**최적화 포인트**:
- ⚠️ 패턴 수가 많아 상수 계수가 큼 (약 50개 패턴)
- ✅ 패턴을 컴파일하여 재사용 가능
- ⚠️ 정규식은 백트래킹으로 인해 최악의 경우 지수 시간 가능 (ReDoS)

**증거**: `normalization.py:191-342`
```191:342:src/anivault/core/normalization.py
def _remove_metadata(title: str) -> str:
    """Remove superfluous metadata from a title string.

    This function removes common patterns found in anime filenames that are
    not part of the actual title, such as resolution, codecs, release groups,
    episode numbers, and Korean/Japanese season/episode markers.

    Args:
        title: The title string to clean.

    Returns:
        Cleaned title with metadata removed.

    Examples:
        >>> _remove_metadata("더 파이팅화")
        '더 파이팅'
        >>> _remove_metadata("블리치화")
        '블리치'
        >>> _remove_metadata("지옥소녀기")
        '지옥소녀'
        >>> _remove_metadata("쓰르라미 울적에기 문제편화")
        '쓰르라미 울적에'
    """
    if not title:
        return title

    # Unicode normalization (NFC) for consistent character representation
    import unicodedata

    cleaned = unicodedata.normalize("NFC", title.strip())

    # Step 1: Remove Korean season markers (e.g., "1기", "2기", "기")
    # Pattern: 숫자 + "기" (e.g., "1기", "2기", "4기")
    cleaned = re.sub(r"\s*\d+기\s*", " ", cleaned, flags=re.IGNORECASE | re.UNICODE)
    # Pattern: 단독 "기" at the end (after any character)
    # Handle: "명탐정 코난기", "지옥소녀기", "블랙라군기"
    cleaned = re.sub(
        r"(?<=\S)기(?=\s|$)", "", cleaned, flags=re.IGNORECASE | re.UNICODE
    )
    # Also handle "기" with preceding space
    cleaned = re.sub(r"\s+기(?=\s|$)", "", cleaned, flags=re.IGNORECASE | re.UNICODE)

    # Step 2: Handle Korean episode titles with "화" (episode marker)
    # Pattern: "명탐정 코난화 게와 고래 유괴 사건" → "명탐정 코난"
    korean_episode_pattern = re.compile(
        r"^(.+?)(?:화|話)\s+(.+)$", re.IGNORECASE | re.UNICODE
    )
    episode_match = korean_episode_pattern.match(cleaned)
    if episode_match:
        # Extract main title (before "화")
        main_title = episode_match.group(1).strip()
        if main_title:
            # Remove "화" from the end of main title if present
            main_title_clean = re.sub(
                r"(?:\화|話)$", "", main_title, flags=re.IGNORECASE | re.UNICODE
            ).strip()
            if main_title_clean:
                cleaned = main_title_clean

    # Step 3: Remove standalone Korean/Japanese episode markers at the end
    # Handle patterns like "제12화", "~053화" (제/기타문자 + 숫자 + 화)
    cleaned = re.sub(
        r"\s*[제~]\s*\d+화\s*$", "", cleaned, flags=re.IGNORECASE | re.UNICODE
    )
    # Remove "화" attached to a character (no space before) at the end
    cleaned = re.sub(r"(?<=\S)화\s*$", "", cleaned, flags=re.IGNORECASE | re.UNICODE)
    # Remove "화" with preceding space at the end
    cleaned = re.sub(r"\s+화\s*$", "", cleaned, flags=re.IGNORECASE | re.UNICODE)
    # Japanese episode markers at the end
    cleaned = re.sub(
        r"\s+第\d+(?:話|回|集)\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.UNICODE,
    )

    # Step 4: Remove Korean metadata patterns
    korean_metadata_patterns = [
        r"\s+무삭제판\s*$",  # "무삭제판" (uncensored version)
        r"\s+완전판\s*$",  # "완전판" (complete version)
        r"\s+수정판\s*$",  # "수정판" (revised version)
        r"\s+재방송\s*$",  # "재방송" (rebroadcast)
        r"\s+리마스터\s*$",  # "리마스터" (remaster)
        r"\s+리마스터판\s*$",  # "리마스터판" (remastered version)
        r"\s+op\s*$",  # OP (opening) at end
        r"\s+ed\s*$",  # ED (ending) at end
    ]

    for pattern in korean_metadata_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.UNICODE)

    # Step 5: Remove common patterns in brackets and parentheses
    patterns_to_remove = [
        # Resolution patterns
        *NormalizationConfig.RESOLUTION_PATTERNS,
        # Codec patterns
        *NormalizationConfig.CODEC_PATTERNS,
        # Release group patterns (common groups)
        *NormalizationConfig.RELEASE_GROUP_PATTERNS,
        # Episode patterns
        *NormalizationConfig.EPISODE_PATTERNS,
        # Season patterns
        *NormalizationConfig.SEASON_PATTERNS,
        # Source patterns
        *NormalizationConfig.SOURCE_PATTERNS,
        # Audio patterns
        *NormalizationConfig.AUDIO_PATTERNS,
        # Hash patterns
        *NormalizationConfig.HASH_PATTERNS,
        # File extensions
        *NormalizationConfig.FILE_EXTENSION_PATTERNS,
        # Generic bracketed content (be more careful with this)
        *NormalizationConfig.BRACKET_PATTERNS,
    ]

    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Step 6: Handle camelCase/PascalCase word separation (e.g., "BenUltimate" → "Ben Ultimate")
    # This helps with titles like "BenUltimate Alien" → "Ben Ultimate Alien"
    import re as re_module

    # Match uppercase letter after lowercase (camelCase) or lowercase after uppercase (PascalCase)
    cleaned = re_module.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    # Also handle multiple consecutive uppercase letters followed by lowercase (e.g., "OPED" → "OP ED")
    cleaned = re_module.sub(r"([A-Z]{2,})([a-z])", r"\1 \2", cleaned)

    # Step 7: Remove duplicate consecutive words (e.g., "원피스원피스" → "원피스")
    # Split into words, remove consecutive duplicates, rejoin
    words = cleaned.split()
    deduplicated_words = []
    prev_word = None
    for word in words:
        if word.lower() != prev_word:
            deduplicated_words.append(word)
            prev_word = word.lower()
    cleaned = " ".join(deduplicated_words)

    # Step 8: Remove unit suffixes (e.g., "cm", "mm", "kg") that might be attached
    unit_patterns = [
        r"\s+cm\s*$",  # "cm" at end
        r"\s+mm\s*$",  # "mm" at end
        r"\s+kg\s*$",  # "kg" at end
    ]
    for pattern in unit_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.UNICODE)

    # Step 9: Clean up extra whitespace and separators
    cleaned = re.sub(r"[-\s]+", " ", cleaned)
    cleaned = cleaned.strip()

    return cleaned
```

#### 3.2 `_normalize_characters()`

**시간 복잡도**: O(m) - 문자 치환

#### 3.3 `_detect_language()`

**시간 복잡도**: O(m) - 정규식 매칭

---

### 4. 캐시 시스템 (Cache Operations)

**위치**: `src/anivault/services/sqlite_cache/operations/`

#### 4.1 SQLite Query Operation

**알고리즘 흐름**:
```python
1. 키 해시 생성: O(m) - SHA-256
2. SQLite 인덱스 조회: O(1) - 해시 인덱스
3. JSON 역직렬화: O(s) - s는 응답 크기
```

**시간 복잡도**:
- **최선/평균**: O(1) - 인덱스 조회
- **최악**: O(m + s) - 해시 생성 + 역직렬화

**공간 복잡도**: O(s)

**증거**: `sqlite_cache/operations/query.py:119-173`
```119:173:src/anivault/services/sqlite_cache/operations/query.py
    def get(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> dict[str, Any] | None:
        """Retrieve data from cache.

        Args:
            key: Cache key identifier
            cache_type: Type of cache ('search' or 'details')

        Returns:
            Cached data if found and not expired, None otherwise
        """
        self._validate_connection()

        # Generate key hash
        _, key_hash = self._generate_cache_key_hash(key)

        # Query cache - fetch all fields to reconstruct CacheEntry
        sql = """
        SELECT cache_key, key_hash, cache_type, response_data,
               created_at, expires_at, hit_count, last_accessed_at, response_size
        FROM tmdb_cache
        WHERE key_hash = ? AND cache_type = ?
        """

        cursor = self.conn.execute(sql, (key_hash, cache_type))
        row = cursor.fetchone()

        if row is None:
            # Cache miss
            self.statistics.record_cache_miss(cache_type)
            return None

        (
            cache_key_db,
            key_hash_db,
            cache_type_db,
            response_data_str,
            created_at_str,
            expires_at_str,
            hit_count_db,
            last_accessed_at_str,
            response_size_db,
        ) = row

        # Deserialize response data
        response_data = _deserialize_response_data(response_data_str, key_hash)
        if response_data is None:
            self.statistics.record_cache_miss(cache_type)
            return None

        # Build CacheEntry from row data
        cache_entry
```

#### 4.2 SQLite Insert Operation

**시간 복잡도**: O(1) - 인덱스 삽입

---

## 📈 종합 분석

### 전체 파이프라인 시간 복잡도

**파일 스캔 → 그룹핑 → 매칭**:
```
1. 파일 스캔: O(n) - n은 파일 수
2. 그룹핑 (Hash-first 파이프라인):
   - Hash Matcher: O(n × m)
   - Title Matcher (정제): O(h × g × m) - h << n
   - 총: O(n × m + h × g × m)
3. 매칭 (각 그룹당):
   - 정규화: O(m)
   - TMDB 검색: O(1) - 캐시 히트
   - 스코어링: O(k × m + k log k)
   - 총: O(m + k × m + k log k)
4. 전체: O(n × m + h × g × m + g × (m + k × m + k log k))
```

**실제 사용 시나리오** (n=1000, m=50, h=100, g=10, k=20):
- 그룹핑: ~500,000 연산
- 매칭: ~100 × (50 + 20×50 + 20×log(20)) ≈ 100 × 1,200 = 120,000 연산
- **총: ~620,000 연산** (수 밀리초 수준)

---

## 🎯 최적화 권장사항

### [사토 미나] 알고리즘 최적화

1. **Title Matcher 개선** (최우선)
   - 현재: O(n² × m)
   - 제안: 클러스터링 알고리즘 도입 (DBSCAN) → O(n log n × m)
   - 예상 효과: 1000개 파일 기준 10-100배 속도 향상

2. **정규화 패턴 최적화**
   - 현재: O(p × m) - p≈50
   - 제안: 패턴 컴파일 캐싱, 병렬 처리
   - 예상 효과: 2-5배 속도 향상

3. **캐시 히트율 향상**
   - 현재: O(1) - 이미 최적
   - 제안: 프리페칭, 배치 처리
   - 예상 효과: 네트워크 지연 감소

### [김지유] 데이터 품질 관점

- ✅ LinkedHashTable 사용으로 데이터 무결성 보장
- ⚠️ Title Matcher의 O(n²) 복잡도는 대용량 데이터에서 문제 가능
- 제안: 그룹 크기 제한 (max_title_match_group_size) 강화

### [최로건] 테스트 관점

- ✅ 벤치마크 테스트 필요
- 제안: 성능 테스트 케이스 추가
  - n=100, 1000, 10000 파일
  - 다양한 타이틀 길이 (m=10, 50, 100)
  - 그룹 수 변화 (h=10, 100, 1000)

### [윤도현] CLI 관점

- ✅ 현재 성능은 실용적 수준
- 제안: `--progress` 옵션으로 진행 상황 표시
- 제안: `--benchmark` 옵션으로 성능 측정

---

## 📊 성능 벤치마크 요약

| 알고리즘 | 최선 | 평균 | 최악 | 공간 | 상태 |
|---------|------|------|------|------|------|
| Hash Matcher | O(n×m) | O(n×m) | O(n×m) | O(n) | ✅ 최적 |
| Title Matcher | O(n×m) | O(n²×m) | O(n²×m) | O(n) | ⚠️ 개선 필요 |
| Season Matcher | O(n) | O(n) | O(n) | O(n) | ✅ 최적 |
| Grouping Engine | O(n×m) | O(n×m+h×g×m) | O(n²×m) | O(n) | ✅ 양호 |
| Matching Engine | O(m+log k) | O(m+k×m+k log k) | O(m+k×m+k log k) | O(k) | ✅ 최적 |
| Normalization | O(p×m) | O(p×m) | O(p×m) | O(m) | ⚠️ 개선 가능 |
| Cache Query | O(1) | O(1) | O(m+s) | O(s) | ✅ 최적 |

**범례**:
- ✅ 최적: 추가 최적화 불필요
- ✅ 양호: 실용적 수준
- ⚠️ 개선 필요: 성능 병목 가능
- ⚠️ 개선 가능: 최적화 여지 있음

---

### 5. 파일 스캔 알고리즘 (Directory Scanner)

**위치**: `src/anivault/core/pipeline/components/scanner.py`

#### 5.1 순차 스캔 (`_run_sequential_scan`)

**알고리즘 흐름**:
```python
1. os.walk()로 디렉토리 순회: O(d) - d는 디렉토리 수
2. 각 파일 확장자 확인: O(1)
3. 필터 엔진 적용: O(1) - 캐시된 결과
4. 큐에 파일 추가: O(1)
```

**시간 복잡도**:
- **최선/평균/최악**: O(d + f) - d는 디렉토리 수, f는 파일 수

**공간 복잡도**: O(1) - 제너레이터 사용으로 메모리 효율적

**증거**: `scanner.py:652-665`
```652:665:src/anivault/core/pipeline/components/scanner.py
    def _run_sequential_scan(self) -> None:
        """Run sequential directory scanning using the original method."""
        # Scan files and put them into the queue
        for file_path in self.scan_files():
            # Check if we should stop
            if self._stop_event.is_set():
                break

            try:
                self.input_queue.put(file_path)
                self.stats.increment_files_scanned()
            except Exception:
                logger.exception("Error putting file into queue: %s", file_path)
                continue
```

#### 5.2 병렬 스캔 (`_run_parallel_scan`)

**알고리즘 흐름**:
```python
1. 하위 디렉토리 목록 생성: O(s) - s는 직접 하위 디렉토리 수
2. ThreadPoolExecutor로 병렬 스캔: O(d/w + f) - w는 워커 수
3. 결과 병합: O(f)
```

**시간 복잡도**:
- **최선**: O(d/w + f) - 완벽한 병렬화
- **평균**: O(d/w + f) - 워커 수에 비례하여 감소
- **최악**: O(d + f) - 병렬화 오버헤드

**공간 복잡도**: O(w) - 워커당 결과 저장

**최적화 포인트**:
- ✅ 적응형 임계값으로 작은 디렉토리는 순차 스캔
- ✅ os.scandir() 사용으로 성능 향상
- ✅ 디렉토리 캐싱으로 중복 스캔 방지

**증거**: `scanner.py:667-719`
```667:719:src/anivault/core/pipeline/components/scanner.py
    def _run_parallel_scan(self) -> None:
        """Run parallel directory scanning using ThreadPoolExecutor."""
        # Get immediate subdirectories for parallel processing
        subdirectories = self._get_immediate_subdirectories()

        # Also scan the root directory itself for files
        root_files = self._scan_root_files()

        logger.info(
            "Parallel scanning %d subdirectories using %d workers",
            len(subdirectories),
            self.max_workers,
        )

        # Use ThreadPoolExecutor for parallel directory scanning
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit subdirectory scanning tasks
            future_to_dir = {}
            for subdir in subdirectories:
                if self._stop_event.is_set():
                    break
                future = executor.submit(self._parallel_scan_directory, subdir)
                future_to_dir[future] = subdir

            # Process root files first (thread-safe)
            queued_root_files = self._thread_safe_put_files(root_files)
            self._thread_safe_update_stats(
                queued_root_files,
                1,
            )  # Root directory counted

            # Process completed subdirectory futures
            for future in as_completed(future_to_dir):
                if self._stop_event.is_set():
                    # Cancel remaining futures
                    for f in future_to_dir:
                        f.cancel()
                    break

                try:
                    # Get results from this subdirectory
                    found_files, dirs_scanned = future.result()

                    # Put files into the input queue (thread-safe)
                    queued_files = self._thread_safe_put_files(found_files)

                    # Update statistics (thread-safe)
                    self._thread_safe_update_stats(queued_files, dirs_scanned)

                except Exception:
                    subdir = future_to_dir[future]
                    logger.exception("Error processing subdirectory: %s", subdir)
                    continue
```

---

### 6. 서브타이틀 매칭 알고리즘 (Subtitle Matcher)

**위치**: `src/anivault/core/subtitle_matcher.py`

#### 6.1 파일명 매칭 (`_matches_video`)

**알고리즘 흐름**:
```python
1. 정확한 매칭 확인: O(1)
2. 파일명 정제 (정규식): O(m) - m은 파일명 길이
3. 부분 매칭 확인: O(m)
4. 해시 기반 매칭: O(m)
5. 퍼지 매칭 (단어 제거): O(w) - w는 단어 수
```

**시간 복잡도**:
- **최선**: O(1) - 정확한 매칭
- **평균**: O(m) - 파일명 정제 및 매칭
- **최악**: O(m + w) - 모든 단계 실행

**공간 복잡도**: O(m)

**최적화 포인트**:
- ✅ 사전 컴파일된 정규식 패턴 사용
- ✅ 디렉토리 캐싱으로 중복 스캔 방지
- ✅ 빠른 경로(fast path)로 정확한 매칭 우선 확인

**증거**: `subtitle_matcher.py:147-206`
```147:206:src/anivault/core/subtitle_matcher.py
    def _matches_video(self, subtitle_name: str, video_name: str) -> bool:
        """Check if a subtitle filename matches a video filename.

        Args:
            subtitle_name: Subtitle filename (without extension)
            video_name: Video filename (without extension)

        Returns:
            True if the subtitle matches the video
        """
        # Fast path: exact match before cleaning (common case)
        if subtitle_name == video_name:
            return True

        # Remove common subtitle-specific suffixes
        subtitle_clean = self._clean_subtitle_name(subtitle_name)
        video_clean = self._clean_video_name(video_name)

        # Check for exact match after cleaning
        if subtitle_clean == video_clean:
            return True

        # Check for partial match (subtitle might have additional info)
        # Optimize: check length first to avoid unnecessary startswith calls
        if len(subtitle_clean) >= len(video_clean):
            if subtitle_clean.startswith(video_clean):
                return True
        elif video_clean.startswith(subtitle_clean):
            return True

        # Check for hash-based matching (common in anime releases)
        if self._has_matching_hash(subtitle_name, video_name):
            return True

        # Fuzzy matching with last word removal
        # Only do expensive operations if strings are different lengths
        if len(subtitle_clean) != len(video_clean):
            subtitle_words = subtitle_clean.split()
            video_words = video_clean.split()

            # Try removing last word from subtitle and matching
            if len(subtitle_words) > 1:
                subtitle_without_last = " ".join(subtitle_words[:-1])
                if subtitle_without_last == video_clean:
                    return True

            # Try removing last word from video and matching
            if len(video_words) > 1:
                video_without_last = " ".join(video_words[:-1])
                if video_without_last == subtitle_clean:
                    return True

            # Fuzzy match: check if first N-1 words match
            if len(subtitle_words) > 1 and len(video_words) > 1:
                subtitle_prefix = " ".join(subtitle_words[:-1])
                video_prefix = " ".join(video_words[:-1])
                if subtitle_prefix == video_prefix:
                    return True

        return False
```

#### 6.2 그룹 매칭 (`group_files_with_subtitles`)

**시간 복잡도**: O(n × s × m) - n은 비디오 파일 수, s는 서브타이틀 파일 수, m은 평균 파일명 길이

**공간 복잡도**: O(n)

---

### 7. 중복 해결 알고리즘 (Duplicate Resolver)

**위치**: `src/anivault/core/file_grouper/duplicate_resolver.py`

#### 7.1 중복 해결 (`resolve_duplicates`)

**알고리즘 흐름**:
```python
1. 각 파일에서 버전 추출: O(n × m) - n은 파일 수, m은 파일명 길이
2. 품질 점수 추출: O(n × m)
3. 정렬 (버전, 품질, 크기): O(n log n)
4. 최고 파일 반환: O(1)
```

**시간 복잡도**:
- **최선/평균/최악**: O(n × m + n log n)

**공간 복잡도**: O(n)

**최적화 포인트**:
- ✅ 정규식 패턴 사전 컴파일
- ✅ 품질 점수 매핑 캐싱
- ✅ 정렬 키 생성 최적화

**증거**: `duplicate_resolver.py:92-149`
```92:149:src/anivault/core/file_grouper/duplicate_resolver.py
    def resolve_duplicates(self, files: list[ScannedFile]) -> ScannedFile:
        """Select the best file from a list of duplicates.

        Selection criteria (in order):
        1. Version number (v2 > v1 > no version)
        2. Video quality (1080p > 720p > 480p)
        3. File size (larger > smaller)

        Args:
            files: List of duplicate files to compare.

        Returns:
            The best file based on selection criteria.

        Raises:
            ValueError: If files list is empty.

        Example:
            >>> files = [
            ...     ScannedFile(file_path=Path("anime_v1.mkv"), file_size=500_000_000),
            ...     ScannedFile(file_path=Path("anime_v2.mkv"), file_size=600_000_000),
            ... ]
            >>> best = resolver.resolve_duplicates(files)
            >>> best.file_path.name
            'anime_v2.mkv'
        """
        if not files:
            raise ValueError("Cannot resolve duplicates: files list is empty")

        if len(files) == 1:
            return files[0]

        # Sort files by all criteria
        def comparison_key(file: ScannedFile) -> tuple[int, int, int]:
            """Generate comparison key for sorting.

            Returns:
                Tuple of (version, quality_score, file_size) for sorting.
                Higher values are considered better.
            """
            filename = file.file_path.name
            version = self._extract_version(filename) or 0
            quality_score = self._extract_quality(filename)
            file_size = file.file_size or 0

            # Apply configuration preferences
            if not self.config.prefer_higher_version:
                version = -version
            if not self.config.prefer_higher_quality:
                quality_score = -quality_score
            if not self.config.prefer_larger_size:
                file_size = -file_size

            return (version, quality_score, file_size)

        # Sort in descending order (best first)
        sorted_files = sorted(files, key=comparison_key, reverse=True)
        return sorted_files[0]
```

---

### 8. 경로 빌더 알고리즘 (Path Builder)

**위치**: `src/anivault/core/organizer/path_builder.py`

#### 8.1 경로 생성 (`build_path`)

**알고리즘 흐름**:
```python
1. 시리즈 타이틀 추출: O(1) - 메타데이터 접근
2. 파일명 정제 (캐싱): O(m) - m은 타이틀 길이 (최초 1회)
3. 시즌 번호 추출: O(1)
4. 해상도 추출: O(m) - 정규식 매칭
5. 폴더 구조 생성: O(1)
```

**시간 복잡도**:
- **최선**: O(1) - 모든 값이 캐시됨
- **평균**: O(m) - 타이틀 정제 (최초 1회)
- **최악**: O(m) - 해상도 추출 포함

**공간 복잡도**: O(1)

**최적화 포인트**:
- ✅ 정제된 타이틀 캐싱 (`_sanitized_title_cache`)
- ✅ 사전 컴파일된 정규식 패턴
- ✅ 해상도 패턴 매칭 최적화

**증거**: `path_builder.py:101-148`
```101:148:src/anivault/core/organizer/path_builder.py
    def build_path(self, context: PathContext) -> Path:
        """Build the destination path for a file.

        This method orchestrates the path construction process:
        1. Extract series title
        2. Sanitize for filesystem
        3. Determine season directory
        4. Apply resolution-based folder organization (if enabled)
        5. Combine with original filename

        Args:
            context: PathContext containing file and resolution information

        Returns:
            Path object representing the destination path

        Example:
            >>> context = PathContext(...)
            >>> builder = PathBuilder()
            >>> path = builder.build_path(context)
            >>> # Returns: /media/TV/Attack on Titan/Season 01/episode.mkv
        """
        # 1. Extract and sanitize series title (with caching)
        raw_title = self._extract_series_title(context.scanned_file)
        # Use cached sanitized title if available
        if raw_title not in self._sanitized_title_cache:
            self._sanitized_title_cache[raw_title] = self.sanitize_filename(raw_title)
        series_title = self._sanitized_title_cache[raw_title]

        # 2. Extract season number
        season_number = self._extract_season_number(context.scanned_file)

        # 3. Build season directory string
        season_dir = self._build_season_dir(season_number)

        # 4. Build folder structure (with or without resolution organization)
        series_dir = self._build_folder_structure(
            context=context,
            series_title=series_title,
            season_dir=season_dir,
        )

        # 5. Use original filename
        original_filename = context.scanned_file.file_path.name

        # 6. Combine to create full path
        result = series_dir / original_filename
        return result
```

---

### 9. 파일 작업 실행 알고리즘 (File Operation Executor)

**위치**: `src/anivault/core/organizer/executor.py`

#### 9.1 배치 실행 (`execute_batch`)

**알고리즘 흐름**:
```python
1. 각 작업 검증: O(n × m) - n은 작업 수, m은 경로 길이
2. 디렉토리 생성 (캐싱): O(d) - d는 고유 디렉토리 수
3. 파일 작업 실행: O(n × s) - s는 평균 파일 크기
```

**시간 복잡도**:
- **최선**: O(n × m + d + n × s) - 모든 작업 성공
- **평균**: O(n × m + d + n × s) - 일부 실패 허용
- **최악**: O(n × m + d + n × s) - 동일 (에러 처리 포함)

**공간 복잡도**: O(d) - 생성된 디렉토리 캐시

**최적화 포인트**:
- ✅ 디렉토리 생성 캐싱 (`created_dirs`)
- ✅ 경로 해결 최적화
- ✅ 서브타이틀 매처 인스턴스 재사용

**증거**: `executor.py:152-239`
```152:239:src/anivault/core/organizer/executor.py
    def execute_batch(
        self,
        operations: list[FileOperation],
        *,
        dry_run: bool = False,
        operation_id: str | None = None,  # noqa: ARG002 - Reserved for future logging
        no_log: bool = False,
    ) -> list[OperationResult]:
        """Execute a batch of file operations.

        This method processes multiple operations, handling errors
        gracefully and continuing with remaining operations if one fails.

        Args:
            operations: List of FileOperation objects to execute
            dry_run: If True, simulate without actual execution
            operation_id: Unique identifier for this batch
            no_log: If True, skip logging to operation history

        Returns:
            List of OperationResult objects for each operation

        Example:
            >>> results = executor.execute_batch(operations, dry_run=False)
            >>> successful = [r for r in results if r.success]
            >>> print(f"{len(successful)}/{len(results)} operations succeeded")
        """
        results: list[OperationResult] = []

        # Cache for created directories to avoid redundant checks
        created_dirs: set[Path] = set()

        for operation in operations:
            try:
                # Execute single operation with directory cache
                result = self.execute(operation, dry_run=dry_run, created_dirs=created_dirs)
                results.append(result)

            except FileNotFoundError as e:
                # Source file not found - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

            except FileExistsError as e:
                # Destination exists - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

            except (OSError, ValueError) as e:
                # Other filesystem or validation errors - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

        # Log the batch operation if requested
        if not no_log:
            self._log_operation_if_needed(operations, results, no_log)

        return results
```

---

### 10. 파일 정리 알고리즘 (Optimized File Organizer)

**위치**: `src/anivault/core/organizer/file_organizer.py`

#### 10.1 계획 생성 (`generate_plan`)

**알고리즘 흐름**:
```python
1. LinkedHashTable 초기화: O(1)
2. 모든 파일 추가: O(n) - n은 파일 수
3. 중복 그룹 찾기: O(n)
4. 최고 파일 선택: O(d × g) - d는 중복 그룹 수, g는 그룹당 파일 수
5. 경로 생성: O(n × m) - m은 경로 생성 비용
```

**시간 복잡도**:
- **최선**: O(n × m) - 중복 없음
- **평균**: O(n × m + d × g × log g) - 중복 그룹 처리
- **최악**: O(n × m + d × g × log g)

**공간 복잡도**: O(n)

**최적화 포인트**:
- ✅ LinkedHashTable 사용으로 O(1) 조회
- ✅ 중복 그룹 효율적 탐색
- ✅ 품질 점수 추출 최적화

**증거**: `file_organizer.py:168-243`
```168:243:src/anivault/core/organizer/file_organizer.py
    def generate_plan(self, scanned_files: list[ScannedFile]) -> list[FileOperation]:
        """
        Generate a file organization plan based on scanned files.

        Args:
            scanned_files: List of ScannedFile objects to organize.

        Returns:
            List of FileOperation objects representing the organization plan.
        """
        # Handle empty file list
        if not scanned_files:
            return []

        # Clear and rebuild cache with new files
        self._file_cache = LinkedHashTable[tuple[str, int], list[ScannedFile]](
            initial_capacity=max(len(scanned_files) * 2, 64),
            load_factor=0.75,
        )

        # Add all files to cache
        for scanned_file in scanned_files:
            self.add_file(scanned_file)

        # Find duplicates
        duplicate_groups = self.find_duplicates()

        operations = []

        # Process duplicate groups
        for duplicate_group in duplicate_groups:
            # Select the best file from duplicates
            best_file = self._select_best_file(duplicate_group)

            # Create move operation for the best file
            destination_path = self._build_organization_path(best_file)
            operations.append(
                FileOperation(
                    operation_type=OperationType.MOVE,
                    source_path=best_file.file_path,
                    destination_path=destination_path,
                )
            )

            # Create move operations for duplicate files
            for file in duplicate_group:
                if file != best_file:
                    duplicate_path = self._build_duplicate_path(file)
                    operations.append(
                        FileOperation(
                            operation_type=OperationType.MOVE,
                            source_path=file.file_path,
                            destination_path=duplicate_path,
                        )
                    )

        # Process non-duplicate files (files that are not in any duplicate group)
        processed_files = set()
        for duplicate_group in duplicate_groups:
            for file in duplicate_group:
                # Use file path as identifier since ScannedFile is not hashable
                processed_files.add(file.file_path)

        for _key, files in self._file_cache:
            for file in files:
                if file.file_path not in processed_files:
                    destination_path = self._build_organization_path(file)
                    operations.append(
                        FileOperation(
                            operation_type=OperationType.MOVE,
                            source_path=file.file_path,
                            destination_path=destination_path,
                        )
                    )

        return operations
```

---

### 11. 트랜잭션 관리 (Transaction Manager)

**위치**: `src/anivault/services/sqlite_cache/transaction/manager.py`

#### 11.1 트랜잭션 처리

**시간 복잡도**: O(1) - SQLite 트랜잭션 오버헤드

**공간 복잡도**: O(1)

**최적화 포인트**:
- ✅ 컨텍스트 매니저 패턴으로 안전한 트랜잭션
- ✅ 자동 롤백/커밋

---

## 📈 업데이트된 종합 분석

### 전체 파이프라인 시간 복잡도 (완전판)

**파일 스캔 → 파싱 → 그룹핑 → 매칭 → 정리**:
```
1. 파일 스캔:
   - 순차: O(d + f)
   - 병렬: O(d/w + f) - w는 워커 수

2. 파일 파싱 (anitopy):
   - O(f × m) - f는 파일 수, m은 파일명 길이

3. 그룹핑 (Hash-first 파이프라인):
   - Hash Matcher: O(f × m)
   - Title Matcher (정제): O(h × g × m)
   - 총: O(f × m + h × g × m)

4. 매칭 (각 그룹당):
   - 정규화: O(m)
   - TMDB 검색: O(1) - 캐시 히트
   - 스코어링: O(k × m + k log k)
   - 총: O(m + k × m + k log k)

5. 서브타이틀 매칭:
   - O(f × s × m) - s는 서브타이틀 파일 수

6. 파일 정리:
   - 계획 생성: O(f × m + d × g × log g)
   - 실행: O(f × m + d + f × s)

7. 전체: O(d/w + f × m + h × g × m + g × (m + k × m + k log k) + f × s × m + f × m + d × g × log g)
```

**실제 사용 시나리오** (d=1000, f=1000, m=50, h=100, g=10, k=20, s=500, w=8):
- 스캔: ~125 (병렬) + 1000 = 1,125 연산
- 파싱: ~50,000 연산
- 그룹핑: ~500,000 연산
- 매칭: ~120,000 연산
- 서브타이틀: ~25,000,000 연산 (병목!)
- 정리: ~50,000 + 1,000 = 51,000 연산
- **총: ~25,722,125 연산** (서브타이틀 매칭이 주요 병목)

---

## 🎯 업데이트된 최적화 권장사항

### [사토 미나] 알고리즘 최적화 (우선순위 업데이트)

1. **서브타이틀 매칭 개선** (최우선 - 새로 발견!)
   - 현재: O(f × s × m) - 모든 비디오-서브타이틀 쌍 비교
   - 제안: 해시 기반 인덱싱 → O(f × m + s × m) = O((f + s) × m)
   - 예상 효과: 1000개 파일 기준 500배 속도 향상

2. **Title Matcher 개선** (기존 우선순위 유지)
   - 현재: O(n² × m)
   - 제안: 클러스터링 알고리즘 도입 → O(n log n × m)
   - 예상 효과: 1000개 파일 기준 10-100배 속도 향상

3. **정규화 패턴 최적화**
   - 현재: O(p × m) - p≈50
   - 제안: 패턴 컴파일 캐싱, 병렬 처리
   - 예상 효과: 2-5배 속도 향상

### [김지유] 데이터 품질 관점

- ✅ LinkedHashTable 사용으로 데이터 무결성 보장
- ⚠️ 서브타이틀 매칭의 O(f × s) 복잡도는 대용량 데이터에서 심각한 병목
- 제안: 서브타이틀 파일 인덱싱 및 캐싱 강화

### [최로건] 테스트 관점

- ✅ 벤치마크 테스트 필요
- 제안: 성능 테스트 케이스 추가
  - 서브타이틀 매칭 성능 테스트 (f=100, 1000, 10000, s=10, 100, 1000)
  - 병렬 스캔 성능 테스트 (d=100, 1000, 10000, w=1, 4, 8, 16)

### [윤도현] CLI 관점

- ⚠️ 서브타이틀 매칭이 주요 병목으로 확인됨
- 제안: `--skip-subtitles` 옵션으로 성능 향상
- 제안: `--subtitle-threads` 옵션으로 병렬 처리

---

## 📊 업데이트된 성능 벤치마크 요약

| 알고리즘 | 최선 | 평균 | 최악 | 공간 | 상태 |
|---------|------|------|------|------|------|
| Hash Matcher | O(n×m) | O(n×m) | O(n×m) | O(n) | ✅ 최적 |
| Title Matcher | O(n×m) | O(n²×m) | O(n²×m) | O(n) | ⚠️ 개선 필요 |
| Season Matcher | O(n) | O(n) | O(n) | O(n) | ✅ 최적 |
| Grouping Engine | O(n×m) | O(n×m+h×g×m) | O(n²×m) | O(n) | ✅ 양호 |
| Matching Engine | O(m+log k) | O(m+k×m+k log k) | O(m+k×m+k log k) | O(k) | ✅ 최적 |
| Normalization | O(p×m) | O(p×m) | O(p×m) | O(m) | ⚠️ 개선 가능 |
| Cache Query | O(1) | O(1) | O(m+s) | O(s) | ✅ 최적 |
| **Directory Scanner (순차)** | **O(d+f)** | **O(d+f)** | **O(d+f)** | **O(1)** | **✅ 최적** |
| **Directory Scanner (병렬)** | **O(d/w+f)** | **O(d/w+f)** | **O(d+f)** | **O(w)** | **✅ 최적** |
| **Subtitle Matcher** | **O(m)** | **O(f×s×m)** | **O(f×s×m)** | **O(n)** | **🚨 병목!** |
| **Duplicate Resolver** | **O(n×m+n log n)** | **O(n×m+n log n)** | **O(n×m+n log n)** | **O(n)** | **✅ 양호** |
| **Path Builder** | **O(1)** | **O(m)** | **O(m)** | **O(1)** | **✅ 최적** |
| **File Organizer** | **O(n×m)** | **O(n×m+d×g log g)** | **O(n×m+d×g log g)** | **O(n)** | **✅ 양호** |
| **Transaction Manager** | **O(1)** | **O(1)** | **O(1)** | **O(1)** | **✅ 최적** |

**범례**:
- ✅ 최적: 추가 최적화 불필요
- ✅ 양호: 실용적 수준
- ⚠️ 개선 필요: 성능 병목 가능
- ⚠️ 개선 가능: 최적화 여지 있음
- 🚨 병목!: 심각한 성능 병목 (최우선 개선 대상)

---

## 🔗 참고 자료

- [파일 그룹핑 아키텍처](../architecture/file-grouper.md)
- [매칭 엔진 설계](../architecture/metadata-enricher.md)
- [성능 벤치마크 결과](../benchmarks/BENCHMARK_RESULTS.md)

---

**작성자**: 사토 미나 (알고리즘 전문가)  
**검토자**: 윤도현, 김지유, 최로건  
**최종 업데이트**: 2025-01-13 (서브타이틀 매칭, 파일 스캔, 경로 빌더 등 추가 분석)

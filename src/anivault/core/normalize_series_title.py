"""Series title normalization for grouping and TMDB search deduplication.

Strips episode/season information from titles so that all episodes of the same
series share one key (e.g. "명탐정 코난 001화 제트 코스터 살인사건" -> "명탐정 코난").
Used by MatchWorker and GroupsBuildWorker to ensure one TMDB search per series
and consistent group keys.
"""

from __future__ import annotations

import re


# End-only patterns (existing behavior): strip suffix from title end
_END_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s*-\s*\d+.*$"), ""),  # "Title - 30" or "Title - 30화"
    (re.compile(r"\s*e\d+.*$", re.IGNORECASE), ""),  # E30, e12
    (re.compile(r"\s*episode\s*\d+.*$", re.IGNORECASE), ""),
    (re.compile(r"\s*\d+\s*[화話]\s*$"), ""),  # "30화", "31話" at end
    (re.compile(r"\s+\d+\s*$"), ""),  # trailing " 30"
]

# Middle-to-end patterns: strip from first " N화" / " N話" / " 第N話" to end of string
# So "명탐정 코난 001화 제트 코스터 살인사건" -> "명탐정 코난"
_MIDDLE_TO_END_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s+\d{1,4}\s*[화話]\s*.*$"), ""),  # " 001화 ..." or " 31話 ..."
    (re.compile(r"\s*第\d+\s*話\s*.*$"), ""),  # Japanese " 第1話 ..."
]


def normalize_series_title(title: str) -> str:
    """Strip episode/season information from title to get canonical series name.

    Ensures all episodes of the same series map to one key for TMDB search
    deduplication and group merging. Handles both suffix-only patterns
    (e.g. "더 파이팅 30화") and middle-to-end patterns (e.g. "명탐정 코난 001화 제트...").

    Args:
        title: Raw title or group title (e.g. from filename or FileGrouper).

    Returns:
        Series name with episode/season stripped; or original if result too short.

    Examples:
        >>> normalize_series_title("더 파이팅 30화")
        '더 파이팅'
        >>> normalize_series_title("명탐정 코난 001화 제트 코스터 살인사건")
        '명탐정 코난'
        >>> normalize_series_title("명탐정 코난 극장판 02기 CD1")
        '명탐정 코난 극장판'
    """
    if not title or not (raw := title.strip()):
        return title

    cleaned = raw
    for pattern, repl in _MIDDLE_TO_END_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    for pattern, repl in _END_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    cleaned = re.sub(r"[-\s]+", " ", cleaned).strip()
    return cleaned if cleaned and len(cleaned) >= 2 else raw

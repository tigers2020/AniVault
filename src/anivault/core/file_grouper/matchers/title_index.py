"""Title index for efficient matching using keyword indexing and LSH.

Extracted from title_matcher.py for better code organization.
Provides O(1) lookup for exact matches and LSH-based similarity search.
"""

from __future__ import annotations

import logging
import re

from datasketch import MinHash, MinHashLSH

logger = logging.getLogger(__name__)

# Security: Maximum title length to prevent ReDoS attacks
MAX_TITLE_LENGTH = 500

# Precompiled patterns for _normalize_title (compile once at module load)
_BRACKET_PATTERNS = [
    re.compile(r"\[[^\]]*\]"),
    re.compile(r"\([^)]*\)"),
    re.compile(r"【[^】]*】"),
    re.compile(r"「[^」]*」"),
    re.compile(r"『[^』]*』"),
]
_VERSION_PATTERNS = [
    re.compile(r"_v\d+(?:\.\d+)?", re.IGNORECASE),
    re.compile(r"_ver\d+", re.IGNORECASE),
    re.compile(r"\(v\d+\)", re.IGNORECASE),
    re.compile(r"\[v\d+\]", re.IGNORECASE),
]
_PATTERN_EXT = re.compile(r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v|m2ts|ts|srt|ass|ssa|sub)$")
_PATTERN_HYPHEN_UNDERSCORE = re.compile(r"[-_]")
_PATTERN_NONWORD = re.compile(r"[^\w\s]")
_PATTERN_WHITESPACE = re.compile(r"\s+")


class TitleIndex:
    """Index for efficient title matching using keyword indexing and normalized hashing.

    This class provides O(1) lookup for exact matches and efficient filtering
    for similar titles using keyword-based indexing.

    Attributes:
        keyword_index: Dictionary mapping keywords to sets of file IDs.
        normalized_hash: Dictionary mapping normalized titles to sets of file IDs (O(1) add/remove/lookup).

    Example:
        >>> index = TitleIndex()
        >>> index.add_title(1, "Attack on Titan - S01E01")
        >>> index.add_title(2, "Attack on Titan - S01E02")
        >>> matches = index.get_exact_matches("Attack on Titan - S01E01")
        >>> len(matches)
        1
    """

    def __init__(self, lsh_threshold: float = 0.5, num_perm: int = 128) -> None:
        """Initialize an empty TitleIndex.

        Args:
            lsh_threshold: Jaccard similarity threshold for LSH (0.0-1.0). Default 0.5.
            num_perm: Number of permutations for MinHash. Higher = more accurate but slower.
                     Default 128 (good balance). Will be adjusted dynamically based on title length.
        """
        self.keyword_index: dict[str, set[int]] = {}
        self.normalized_hash: dict[str, set[int]] = {}
        # Reverse index: file_id -> set of keywords (for efficient removal)
        self.reverse_keyword_index: dict[int, set[str]] = {}
        # Reverse index: file_id -> normalized title (for efficient removal)
        self.file_id_to_normalized: dict[int, str] = {}
        # LSH index for approximate similarity search
        self.lsh_index: MinHashLSH = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)
        # Store MinHash objects for each file_id (for querying)
        self.file_id_to_minhash: dict[int, MinHash] = {}
        # Soft-deleted keys (for incremental updates)
        self.deleted_keys: set[int] = set()
        # Base num_perm for dynamic adjustment
        self.base_num_perm = num_perm

    def _normalize_title(self, title: str) -> str:
        """Normalize title for indexing and matching."""
        if not title:
            return ""

        # Security: Truncate to prevent ReDoS attacks with malicious input
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                "Title exceeds maximum length (%d), truncating: %s",
                MAX_TITLE_LENGTH,
                title[:50] + "...",
            )
            title = title[:MAX_TITLE_LENGTH]

        normalized = title.lower()
        normalized = _PATTERN_EXT.sub("", normalized)

        for _ in range(5):
            changed = False
            for pattern in _BRACKET_PATTERNS:
                new_normalized = pattern.sub("", normalized)
                if new_normalized != normalized:
                    changed = True
                    normalized = new_normalized
            if not changed:
                break

        for pattern in _VERSION_PATTERNS:
            normalized = pattern.sub("", normalized)

        normalized = _PATTERN_HYPHEN_UNDERSCORE.sub(" ", normalized)
        normalized = _PATTERN_NONWORD.sub("", normalized)
        normalized = _PATTERN_WHITESPACE.sub(" ", normalized)

        return normalized.strip()

    def add_title(self, file_id: int, title: str) -> None:
        """Add a title to the index."""
        if not title:
            return

        normalized = self._normalize_title(title)
        if not normalized:
            return

        self.normalized_hash.setdefault(normalized, set()).add(file_id)

        self.file_id_to_normalized[file_id] = normalized

        keyword_set: set[str] = set()
        for keyword in normalized.split():
            if keyword:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = set()
                self.keyword_index[keyword].add(file_id)
                keyword_set.add(keyword)

        self.reverse_keyword_index[file_id] = keyword_set

        minhash = self._create_minhash_from_title(normalized)
        if minhash is not None:
            if file_id in self.file_id_to_minhash:
                self.deleted_keys.add(file_id)
                logger.debug("File ID %d already in LSH, soft-deleting old entry", file_id)

            self.file_id_to_minhash[file_id] = minhash
            self.deleted_keys.discard(file_id)

            try:
                self.lsh_index.insert(file_id, minhash)
            except ValueError:
                logger.debug(
                    "LSH key %d already exists in index, will use soft-delete filtering",
                    file_id,
                )

    def _create_minhash_from_title(self, normalized_title: str, num_perm: int | None = None) -> MinHash | None:
        """Create MinHash signature from normalized title using shingling."""
        if not normalized_title:
            return None

        if num_perm is None:
            num_perm = self.lsh_index.h

        shingles: set[str] = set()
        n = 3

        for i in range(len(normalized_title) - n + 1):
            shingle = normalized_title[i : i + n]
            shingles.add(shingle)

        if len(shingles) < 3:
            words = normalized_title.split()
            for word in words:
                if len(word) >= 2:
                    for j in range(len(word) - 1):
                        shingles.add(word[j : j + 2])

        if not shingles:
            return None

        minhash = MinHash(num_perm=num_perm)
        for shingle in shingles:
            minhash.update(shingle.encode("utf-8"))

        return minhash

    def query_similar_titles(self, title: str) -> list[int]:
        """Query LSH index for titles similar to the given title."""
        if not title:
            return []

        normalized = self._normalize_title(title)
        if not normalized:
            return []

        query_minhash = self._create_minhash_from_title(normalized)
        if query_minhash is None:
            return []

        candidate_ids = self.lsh_index.query(query_minhash)
        return [file_id for file_id in candidate_ids if file_id not in self.deleted_keys]

    def get_exact_matches(self, title: str) -> list[int]:
        """Get all file IDs with titles that normalize to the same string."""
        if not title:
            return []

        normalized = self._normalize_title(title)
        if not normalized:
            return []

        return list(self.normalized_hash.get(normalized, set()))

    def add_file(self, file_id: int, title: str) -> None:
        """Add a file to the index (public API for incremental updates)."""
        self.deleted_keys.discard(file_id)
        self.add_title(file_id, title)

    def remove_file(self, file_id: int, title: str | None = None) -> None:  # noqa: ARG002
        """Remove a file from the index."""
        normalized = self.file_id_to_normalized.get(file_id)

        if normalized is None:
            return

        if normalized in self.normalized_hash:
            self.normalized_hash[normalized].discard(file_id)
            if not self.normalized_hash[normalized]:
                del self.normalized_hash[normalized]

        keywords = self.reverse_keyword_index.get(file_id, set())
        for keyword in keywords:
            if keyword in self.keyword_index:
                self.keyword_index[keyword].discard(file_id)
                if not self.keyword_index[keyword]:
                    del self.keyword_index[keyword]

        self.reverse_keyword_index.pop(file_id, None)
        self.file_id_to_normalized.pop(file_id, None)

        self.deleted_keys.add(file_id)
        self.file_id_to_minhash.pop(file_id, None)

    def update_file(self, file_id: int, old_title: str, new_title: str) -> None:
        """Update a file's title in the index."""
        self.remove_file(file_id, old_title)
        self.add_file(file_id, new_title)


__all__ = ["MAX_TITLE_LENGTH", "TitleIndex"]

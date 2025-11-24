"""Data models for file grouping operations.

This module defines data structures for representing file groups
and grouping evidence, providing transparency in the grouping process.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from anivault.core.models import ScannedFile


@dataclass
class GroupingEvidence:
    """Evidence for why files were grouped together.

    This dataclass provides transparency by tracking how files were grouped,
    which matchers contributed, and the confidence of the grouping decision.

    Attributes:
        match_scores: Dictionary mapping matcher names to their scores (0.0-1.0).
                     Example: {"title": 0.92, "hash": 0.85, "season": 0.0}
        selected_matcher: Name of the matcher that was primarily used for grouping.
                         Example: "title" or "hash"
        explanation: User-facing explanation of why files were grouped.
                    Example: "Grouped by title similarity (92%)"
        confidence: Overall confidence score for this grouping (0.0-1.0).
                   Higher values indicate stronger evidence for grouping.

    Example:
        >>> evidence = GroupingEvidence(
        ...     match_scores={"title": 0.92, "hash": 0.85},
        ...     selected_matcher="title",
        ...     explanation="Grouped by title similarity (92%)",
        ...     confidence=0.92
        ... )
        >>> evidence.match_scores["title"]
        0.92
    """

    match_scores: dict[str, float]
    selected_matcher: str
    explanation: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        """Convert evidence to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the evidence.

        Example:
            >>> evidence = GroupingEvidence(
            ...     match_scores={"title": 0.92},
            ...     selected_matcher="title",
            ...     explanation="Title match",
            ...     confidence=0.92
            ... )
            >>> result = evidence.to_dict()
            >>> result["confidence"]
            0.92
        """
        return {
            "match_scores": self.match_scores,
            "selected_matcher": self.selected_matcher,
            "explanation": self.explanation,
            "confidence": self.confidence,
        }


@dataclass
class Group:
    """A group of similar files.

    Represents a collection of files that have been grouped together
    based on similarity criteria (title, season, hash, etc.).

    Attributes:
        title: The group name/title (typically derived from filenames).
              Example: "Attack on Titan" or "Shingeki no Kyojin S01"
        files: List of ScannedFile objects in this group.
        evidence: Optional evidence explaining why these files were grouped.
                 None if grouping was done without evidence tracking.

    Example:
        >>> from pathlib import Path
        >>> from anivault.core.models import ScannedFile
        >>> files = [
        ...     ScannedFile(file_path=Path("aot_01.mkv"), ...),
        ...     ScannedFile(file_path=Path("aot_02.mkv"), ...)
        ... ]
        >>> evidence = GroupingEvidence(
        ...     match_scores={"title": 0.95},
        ...     selected_matcher="title",
        ...     explanation="High title similarity",
        ...     confidence=0.95
        ... )
        >>> group = Group(
        ...     title="Attack on Titan",
        ...     files=files,
        ...     evidence=evidence
        ... )
        >>> len(group.files)
        2
    """

    title: str
    files: list[ScannedFile] = field(default_factory=list)
    evidence: GroupingEvidence | None = None

    def add_file(self, file: ScannedFile) -> None:
        """Add a file to this group.

        Args:
            file: ScannedFile to add to the group.

        Example:
            >>> from pathlib import Path
            >>> from anivault.core.models import ScannedFile
            >>> group = Group(title="Test Group")
            >>> file = ScannedFile(file_path=Path("test.mkv"), ...)
            >>> group.add_file(file)
            >>> len(group.files)
            1
        """
        self.files.append(file)

    def has_duplicates(self) -> bool:
        """Check if this group contains duplicate files.

        Duplicates are defined as multiple files representing the same
        episode/content (e.g., different versions or qualities).

        Returns:
            True if the group contains duplicates, False otherwise.

        Example:
            >>> from pathlib import Path
            >>> from anivault.core.models import ScannedFile
            >>> group = Group(title="Test")
            >>> # Assuming files with metadata indicating same episode
            >>> # group.has_duplicates() would return True
        """
        # Simple heuristic: if we have multiple files, check if they
        # represent the same content (would need episode metadata)
        if len(self.files) <= 1:
            return False

        # Check if files have same episode numbers (requires metadata)
        episodes = set()
        for file in self.files:
            if hasattr(file, "metadata") and file.metadata and hasattr(file.metadata, "episode"):
                episode = file.metadata.episode
                if episode is not None:
                    if episode in episodes:
                        return True
                    episodes.add(episode)

        # If no episode metadata, can't determine duplicates reliably
        return False

    def to_dict(self) -> dict[str, object]:
        """Convert group to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the group.

        Example:
            >>> group = Group(title="Test", files=[])
            >>> result = group.to_dict()
            >>> result["title"]
            'Test'
        """
        return {
            "title": self.title,
            "file_count": len(self.files),
            "files": [str(f.file_path) for f in self.files],
            "evidence": self.evidence.to_dict() if self.evidence else None,
        }


__all__ = ["Group", "GroupingEvidence"]

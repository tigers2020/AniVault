"""Data models for file grouping operations."""

from __future__ import annotations

from dataclasses import dataclass, field

from .file import ScannedFile


@dataclass
class GroupingEvidence:
    """Evidence for why files were grouped together."""

    match_scores: dict[str, float]
    selected_matcher: str
    explanation: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        """Convert evidence to dictionary for logging/serialization."""
        return {
            "match_scores": self.match_scores,
            "selected_matcher": self.selected_matcher,
            "explanation": self.explanation,
            "confidence": self.confidence,
        }


@dataclass
class Group:
    """A group of similar files."""

    title: str
    files: list[ScannedFile] = field(default_factory=list)
    evidence: GroupingEvidence | None = None

    def add_file(self, file: ScannedFile) -> None:
        """Add a file to this group."""
        self.files.append(file)

    def has_duplicates(self) -> bool:
        """Check if this group contains duplicate files."""
        if len(self.files) <= 1:
            return False

        episodes = set()
        for file in self.files:
            if hasattr(file, "metadata") and file.metadata and hasattr(file.metadata, "episode"):
                episode = file.metadata.episode
                if episode is not None:
                    if episode in episodes:
                        return True
                    episodes.add(episode)

        return False

    def to_dict(self) -> dict[str, object]:
        """Convert group to dictionary for logging/serialization."""
        return {
            "title": self.title,
            "file_count": len(self.files),
            "files": [str(f.file_path) for f in self.files],
            "evidence": self.evidence.to_dict() if self.evidence else None,
        }


__all__ = ["Group", "GroupingEvidence"]

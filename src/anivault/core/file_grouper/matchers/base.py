"""Base protocol for file matching strategies.

This module defines the BaseMatcher Protocol that all matchers must implement.
The Protocol enables duck-typing and extensibility, allowing new matching
strategies to be added without modifying the core grouping logic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile


@runtime_checkable
class BaseMatcher(Protocol):
    """Protocol for file matching strategies.

    This Protocol defines the interface that all matcher implementations must follow.
    Matchers are responsible for grouping files based on specific similarity criteria
    (e.g., title similarity, hash matching, season/episode patterns).

    The Protocol approach enables:
    - Duck-typing: Any class with the correct signature can be used
    - Extensibility: New matchers can be added without modifying core code
    - Type safety: isinstance() checks and type hints work correctly
    - No inheritance: Matchers don't need to inherit from a base class

    Attributes:
        component_name: Unique identifier for this matcher (e.g., "title", "hash", "season").
                       Used for logging, evidence tracking, and weighted scoring.

    Example:
        >>> class CustomMatcher:
        ...     component_name = "custom"
        ...
        ...     def match(self, files):
        ...         # Custom matching logic
        ...         return {"group1": files}
        ...
        >>> matcher = CustomMatcher()
        >>> isinstance(matcher, BaseMatcher)  # Protocol check
        True

    Usage in GroupingEngine:
        >>> from anivault.core.file_grouper.grouping_engine import GroupingEngine
        >>> matchers = [TitleMatcher(), HashMatcher(), CustomMatcher()]
        >>> engine = GroupingEngine(matchers=matchers)
        >>> groups = engine.group_files(scanned_files)
    """

    component_name: str

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files based on this matcher's similarity criteria.

        This method analyzes the provided files and groups them according to
        the matcher's specific algorithm (title similarity, hash matching, etc.).

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects containing similar files.
            Each Group has a title, files list, and optional evidence.

        Example:
            >>> matcher = TitleSimilarityMatcher()
            >>> files = [
            ...     ScannedFile(file_path=Path("aot_01.mkv"), ...),
            ...     ScannedFile(file_path=Path("aot_02.mkv"), ...)
            ... ]
            >>> groups = matcher.match(files)
            >>> groups[0].title
            'Attack on Titan'
            >>> len(groups[0].files)
            2

        Implementation Notes:
            - Return empty list if no groups can be formed
            - Each file should appear in at most one group
            - Group titles should be stable across multiple calls
            - Handle edge cases (empty input, single file, etc.)
            - Log warnings for files that couldn't be grouped
            - Optionally attach GroupingEvidence to each Group
        """


__all__ = ["BaseMatcher"]

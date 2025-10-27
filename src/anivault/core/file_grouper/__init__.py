"""File grouper module for AniVault.

This module provides functionality to group similar anime files based on
filename similarity, season/episode patterns, and other matching strategies.

Public API (Stable):
    - FileGrouper: Main facade for file grouping operations
    - group_similar_files: Convenience function for simple grouping
    - Group, GroupingEvidence: Data models

Advanced API (For custom implementations):
    - GroupingEngine: Orchestrates multiple matching strategies
    - BaseMatcher: Protocol for custom matchers
    - DuplicateResolver: Selects best file from duplicates
    - TitleExtractor, TitleQualityEvaluator, GroupNameManager: Helper classes
"""

from __future__ import annotations

# Advanced API - Strategy pattern components
from anivault.core.file_grouper.duplicate_resolver import (
    DuplicateResolver,
    ResolutionConfig,
)

# Public API - Main facade and convenience function
# Advanced API - Helper classes (used by matchers)
from anivault.core.file_grouper.grouper import (
    FileGrouper,
    GroupNameManager,
    TitleExtractor,
    TitleQualityEvaluator,
    group_similar_files,
)
from anivault.core.file_grouper.grouping_engine import (
    DEFAULT_WEIGHTS,
    GroupingEngine,
)

# Advanced API - Matcher protocol and implementations
from anivault.core.file_grouper.matchers.base import BaseMatcher

# Public API - Data models
from anivault.core.file_grouper.models import (
    Group,
    GroupingEvidence,
)

# Advanced API - Grouping strategies
from anivault.core.file_grouper.strategies import (
    BestMatcherStrategy,
    ConsensusStrategy,
    GroupingStrategy,
    WeightedMergeStrategy,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "BaseMatcher",
    "BestMatcherStrategy",
    "ConsensusStrategy",
    "DuplicateResolver",
    "FileGrouper",
    "Group",
    "GroupNameManager",
    "GroupingEngine",
    "GroupingEvidence",
    "GroupingStrategy",
    "ResolutionConfig",
    "TitleExtractor",
    "TitleQualityEvaluator",
    "WeightedMergeStrategy",
    "group_similar_files",
]

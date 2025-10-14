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

# Note: Specific matchers are available but not exported by default
# Import them explicitly if needed:
#   from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
#   from anivault.core.file_grouper.matchers.hash_matcher import HashSimilarityMatcher
#   from anivault.core.file_grouper.matchers.season_matcher import SeasonEpisodeMatcher

__all__ = [
    # Public API - Main
    "FileGrouper",
    "group_similar_files",
    # Public API - Models
    "Group",
    "GroupingEvidence",
    # Advanced API - Engine & Resolver
    "GroupingEngine",
    "DEFAULT_WEIGHTS",
    "DuplicateResolver",
    "ResolutionConfig",
    # Advanced API - Helpers
    "TitleExtractor",
    "TitleQualityEvaluator",
    "GroupNameManager",
    # Advanced API - Protocol
    "BaseMatcher",
]

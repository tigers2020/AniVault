"""Season/episode-based matcher for file grouping.

This module implements grouping based on season and episode metadata.
Files from the same series and season are grouped together.
"""

from __future__ import annotations

import logging

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)


class SeasonEpisodeMatcher:
    """Groups files by series name and season number.

    This matcher uses parsed metadata (season, episode) to group files.
    Files from the same series and season are grouped together, regardless
    of episode numbers.

    Group names follow the format: "{SeriesName} S{season:02d}"
    Example: "Attack on Titan S01"

    Attributes:
        component_name: Identifier for this matcher ("season").

    Example:
        >>> matcher = SeasonEpisodeMatcher()
        >>> groups = matcher.match(scanned_files)
        >>> groups[0].title
        'Attack on Titan S01'
        >>> len(groups[0].files)
        12
    """

    def __init__(self) -> None:
        """Initialize the season/episode matcher."""
        self.component_name = "season"

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files by series name and season number.

        Files are grouped using the format: "{SeriesName} S{season:02d}"
        Files without valid metadata are skipped with a warning.

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects grouped by series + season.
            Returns empty list if input is empty or no valid files found.

        Example:
            >>> files = [
            ...     ScannedFile(file_path=Path("anime_S01E01.mkv"), metadata=...),
            ...     ScannedFile(file_path=Path("anime_S01E02.mkv"), metadata=...),
            ...     ScannedFile(file_path=Path("anime_S02E01.mkv"), metadata=...),
            ... ]
            >>> groups = matcher.match(files)
            >>> len(groups)
            2
            >>> groups[0].title
            'Anime S01'
            >>> groups[1].title
            'Anime S02'
        """
        if not files:
            return []

        # Step 1: Extract metadata and create group keys using LinkedHashTable for O(1) operations
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

        if skipped_count > 0:
            logger.info(
                "Skipped %d file(s) due to missing metadata",
                skipped_count,
            )

        # Step 2: Convert to Group objects
        result = [
            Group(title=group_name, files=group_files)
            for group_name, group_files in file_groups
        ]

        logger.info(
            "Season matcher grouped %d files into %d groups",
            len(files) - skipped_count,
            len(result),
        )

        return result

    def _extract_metadata(
        self,
        file: ScannedFile,
    ) -> tuple[str, int, int | None] | None:
        """Extract series name, season, and episode from file metadata.

        Args:
            file: ScannedFile to extract metadata from.

        Returns:
            Tuple of (series_name, season, episode) or None if extraction failed.
            Season defaults to 1 if not found.
            Episode can be None.

        Example:
            >>> metadata = matcher._extract_metadata(file)
            >>> metadata
            ('Attack on Titan', 1, 5)
        """
        # Check if file has valid metadata
        if not hasattr(file, "metadata") or file.metadata is None:
            return None

        metadata = file.metadata

        # Extract series name
        series_name = None
        if hasattr(metadata, "title") and metadata.title:
            series_name = metadata.title

        if not series_name:
            # Cannot group without series name
            return None

        # Extract season (default to 1 if not found)
        season = 1
        if hasattr(metadata, "season") and metadata.season is not None:
            try:
                season = int(metadata.season)
            except (ValueError, TypeError):
                logger.debug(
                    "Invalid season value '%s', defaulting to 1: %s",
                    metadata.season,
                    file.file_path.name,
                )
                season = 1

        # Extract episode (optional)
        episode = None
        if hasattr(metadata, "episode") and metadata.episode is not None:
            try:
                episode = int(metadata.episode)
            except (ValueError, TypeError):
                logger.debug(
                    "Invalid episode value '%s': %s",
                    metadata.episode,
                    file.file_path.name,
                )
                episode = None

        return (series_name, season, episode)


__all__ = ["SeasonEpisodeMatcher"]

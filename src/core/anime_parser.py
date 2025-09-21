"""Anime filename parsing using anitopy library.

This module provides functionality to parse anime filenames and extract
structured information like title, season, episode, resolution, etc.
"""

from typing import Any

import anitopy

from src.core.fallback_parser import FallbackAnimeParser
from src.core.models import AnimeFile, ParsedAnimeInfo
from src.core.validation import AnimeDataValidator
from src.utils.logger import get_logger
from src.utils.parsing_utils import (
    normalize_title,
    parse_resolution_string,
    validate_episode_number,
    validate_season_number,
    validate_year,
)

logger = get_logger(__name__)


class AnimeParser:
    """Wraps anitopy functionality for parsing anime filenames.

    Handles normalization, validation, and fallback mechanisms for
    extracting structured information from anime filenames.
    """

    def __init__(self) -> None:
        """Initialize the anime parser."""
        # anitopy.Anitopy() can be initialized here if custom rules are needed.
        # For now, using the module-level parse functions is sufficient.
        self.validator = AnimeDataValidator()
        self.fallback_parser = FallbackAnimeParser()

    def _map_anitopy_to_model(self, parsed_data: dict[str, Any]) -> ParsedAnimeInfo | None:
        """Maps the raw dictionary output from anitopy to a ParsedAnimeInfo dataclass.

        Includes normalization and validation of the parsed data.

        Args:
            parsed_data: Raw dictionary from anitopy.parse()

        Returns:
            ParsedAnimeInfo object if successful, None if parsing failed
        """
        # Critical check: If anitopy couldn't find a title, it's likely not a valid anime filename.
        title = parsed_data.get("anime_title")
        if not title:
            return None

        try:
            # Normalize title
            title = normalize_title(title)
            if not title:  # Ensure title is not just an empty string after normalization
                return None

            # Safely convert season and episode to int with validation
            season_str = parsed_data.get("season_number") or parsed_data.get("anime_season")
            episode_str = parsed_data.get("episode_number")
            season = validate_season_number(
                int(season_str) if season_str and season_str.isdigit() else None
            )
            episode = validate_episode_number(
                int(episode_str) if episode_str and episode_str.isdigit() else None
            )

            # Parse resolution string into width and height
            resolution_str = parsed_data.get("video_resolution")
            width, height = parse_resolution_string(resolution_str)

            # Safely convert year to int with validation
            year_str = parsed_data.get("release_year")
            year = validate_year(int(year_str) if year_str and year_str.isdigit() else None)

            # Clean up episode title
            episode_title = parsed_data.get("episode_title")
            if episode_title:
                episode_title = episode_title.strip()

            parsed_info = ParsedAnimeInfo(
                title=title,
                season=season,
                episode=episode,
                episode_title=episode_title,
                resolution=resolution_str,
                resolution_width=width,
                resolution_height=height,
                video_codec=parsed_data.get("video_codec"),
                audio_codec=parsed_data.get("audio_codec"),
                release_group=parsed_data.get("release_group"),
                file_extension=parsed_data.get("file_extension"),
                year=year,
                source=parsed_data.get("source"),
                raw_data=parsed_data,  # Store raw data for debugging/future use
            )

            # Validate and normalize the parsed info
            return self.validator.normalize_parsed_info(parsed_info)
        except Exception as e:
            # Catch any unexpected errors during mapping/conversion
            logger.error(
                f"Error mapping anitopy data to ParsedAnimeInfo: {e}. Raw data: {parsed_data}"
            )
            return None

    def parse_filename(self, filename: str, use_fallback: bool = True) -> ParsedAnimeInfo | None:
        """Parses a single anime filename using anitopy with fallback support.

        Args:
            filename: The filename to parse
            use_fallback: Whether to use fallback parsing if anitopy fails

        Returns:
            ParsedAnimeInfo if successful, None otherwise
        """
        if not filename or not filename.strip():
            logger.warning("Empty filename provided for parsing")
            return None

        # Try anitopy first
        try:
            parsed_data = anitopy.parse(filename)
            parsed_info = self._map_anitopy_to_model(parsed_data)

            # If anitopy succeeded and found a title, return the result
            if parsed_info and parsed_info.title:
                return parsed_info
        except Exception as e:
            logger.error(f"Anitopy parsing failed for filename '{filename}': {e}")

        # If anitopy failed or didn't find meaningful data, try fallback
        if use_fallback:
            logger.info(f"Attempting fallback parsing for '{filename}'")
            fallback_info = self.fallback_parser.create_fallback_parsed_info(filename)
            if fallback_info:
                logger.info(f"Fallback parsing succeeded for '{filename}'")
                return fallback_info
            else:
                logger.warning(f"Both anitopy and fallback parsing failed for '{filename}'")

        return None

    def parse_anime_file(self, anime_file: AnimeFile) -> ParsedAnimeInfo | None:
        """Parses the filename from an AnimeFile object.

        Updates the AnimeFile's processing_errors if parsing fails.

        Args:
            anime_file: AnimeFile object to parse

        Returns:
            ParsedAnimeInfo if successful, None otherwise
        """
        parsed_info = self.parse_filename(anime_file.filename)
        if parsed_info is None:
            error_msg = f"Failed to parse filename: '{anime_file.filename}'. No meaningful anime info extracted."
            anime_file.processing_errors.append(error_msg)
            logger.warning(error_msg)
        return parsed_info

    def parse_filenames_batch(self, filenames: list[str]) -> list[ParsedAnimeInfo | None]:
        """Parses a list of anime filenames using individual parsing.

        Args:
            filenames: List of filenames to parse

        Returns:
            List of ParsedAnimeInfo objects (or None for failures)
        """
        if not filenames:
            return []

        results = []
        for filename in filenames:
            try:
                result = self.parse_filename(filename)
                results.append(result)
            except Exception as e:
                logger.error(f"Error parsing filename '{filename}': {e}")
                results.append(None)
        return results

    def parse_anime_files_batch(self, anime_files: list[AnimeFile]) -> list[ParsedAnimeInfo | None]:
        """Parses a list of AnimeFile objects in batch.

        Updates each AnimeFile's processing_errors if parsing fails.

        Args:
            anime_files: List of AnimeFile objects to parse

        Returns:
            List of ParsedAnimeInfo objects (or None for failures)
        """
        if not anime_files:
            return []

        filenames = [af.filename for af in anime_files]
        parsed_infos = self.parse_filenames_batch(filenames)

        for i, parsed_info in enumerate(parsed_infos):
            if parsed_info is None:
                error_msg = f"Failed to parse filename: '{anime_files[i].filename}'. No meaningful anime info extracted."
                anime_files[i].processing_errors.append(error_msg)
                logger.warning(error_msg)
        return parsed_infos

    def get_parsing_statistics(
        self, parsed_results: list[ParsedAnimeInfo | None]
    ) -> dict[str, Any]:
        """Generates statistics about parsing results.

        Args:
            parsed_results: List of parsing results

        Returns:
            Dictionary containing parsing statistics
        """
        total_files = len(parsed_results)
        successful_parses = sum(1 for result in parsed_results if result is not None)
        failed_parses = total_files - successful_parses

        # Count different types of content
        movies = sum(1 for result in parsed_results if result and result.is_movie)
        tv_series = sum(1 for result in parsed_results if result and result.is_tv_series)

        # Count resolution types
        resolutions: dict[str, int] = {}
        for result in parsed_results:
            if result and result.resolution:
                resolutions[result.resolution] = resolutions.get(result.resolution, 0) + 1

        # Count parsing methods used
        anitopy_parses = sum(
            1
            for result in parsed_results
            if result and not result.raw_data.get("fallback_parsing", False)
        )
        fallback_parses = sum(
            1
            for result in parsed_results
            if result and result.raw_data.get("fallback_parsing", False)
        )

        return {
            "total_files": total_files,
            "successful_parses": successful_parses,
            "failed_parses": failed_parses,
            "success_rate": (successful_parses / total_files * 100) if total_files > 0 else 0,
            "anitopy_parses": anitopy_parses,
            "fallback_parses": fallback_parses,
            "movies": movies,
            "tv_series": tv_series,
            "resolutions": resolutions,
        }

    def get_parsing_failures(self, anime_files: list[AnimeFile]) -> list[dict[str, Any]]:
        """Get detailed information about parsing failures.

        Args:
            anime_files: List of AnimeFile objects that were processed

        Returns:
            List of dictionaries containing failure information
        """
        failures = []

        for anime_file in anime_files:
            if anime_file.processing_errors:
                failure_info = {
                    "filename": anime_file.filename,
                    "file_path": str(anime_file.file_path),
                    "errors": anime_file.processing_errors.copy(),
                    "is_likely_anime": self.fallback_parser.is_likely_anime_file(
                        anime_file.filename
                    ),
                    "file_extension": anime_file.file_extension,
                }
                failures.append(failure_info)

        return failures

    def suggest_manual_input(self, failed_filename: str) -> dict[str, Any]:
        """Suggest manual input fields for a failed parsing attempt.

        Args:
            failed_filename: Filename that failed to parse

        Returns:
            Dictionary with suggested manual input fields
        """
        suggestions = {
            "title": "",
            "season": None,
            "episode": None,
            "resolution": None,
            "year": None,
            "source": None,
            "confidence": "low",
        }

        # Try to extract basic info for suggestions
        basic_info = self.fallback_parser.extract_basic_info(failed_filename)

        if basic_info["title"]:
            suggestions["title"] = basic_info["title"]
            suggestions["confidence"] = "medium"

        if basic_info["episode"]:
            suggestions["episode"] = basic_info["episode"]

        if basic_info["season"]:
            suggestions["season"] = basic_info["season"]

        if basic_info["resolution"]:
            suggestions["resolution"] = basic_info["resolution"]

        if basic_info["year"]:
            suggestions["year"] = basic_info["year"]

        if basic_info["source"]:
            suggestions["source"] = basic_info["source"]

        return suggestions

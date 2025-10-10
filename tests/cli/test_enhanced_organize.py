"""Tests for enhanced organize command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.cli.helpers.organize import generate_enhanced_organization_plan
from anivault.core.models import ParsingResult, ScannedFile


class TestEnhancedOrganize:
    """Test cases for enhanced organize command."""

    def testgenerate_enhanced_organization_plan_empty(self) -> None:
        """Test enhanced organization plan with empty file list."""
        result = generate_enhanced_organization_plan([], Mock())
        assert result == []

    def testgenerate_enhanced_organization_plan_single_file(self) -> None:
        """Test enhanced organization plan with single file."""
        # Create a proper ParsingResult object instead of using Mock
        metadata = ParsingResult(title="Attack on Titan", season=1, episode=1)
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=metadata,
        )
        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with (
            patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper,
            patch(
                "anivault.cli.helpers.organize.ResolutionDetector"
            ) as mock_resolution,
            patch("anivault.cli.helpers.organize.SubtitleMatcher") as mock_subtitle,
        ):
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [file]
            }
            # Mock find_highest_resolution to return the actual file object
            mock_resolution.return_value.find_highest_resolution.return_value = file
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            result = generate_enhanced_organization_plan([file], args)
            assert len(result) == 1

    def testgenerate_enhanced_organization_plan_multiple_files(self) -> None:
        """Test enhanced organization plan with multiple files."""
        files = [
            ScannedFile(
                file_path=Path("Attack on Titan - 01.mkv"),
                metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
            ),
            ScannedFile(
                file_path=Path("Attack on Titan - 02.mkv"),
                metadata=ParsingResult(title="Attack on Titan", season=1, episode=2),
            ),
        ]
        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with (
            patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper,
            patch(
                "anivault.cli.helpers.organize.ResolutionDetector"
            ) as mock_resolution,
            patch("anivault.cli.helpers.organize.SubtitleMatcher") as mock_subtitle,
        ):
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": files
            }
            # Mock find_highest_resolution to return the first file (highest resolution)
            mock_resolution.return_value.find_highest_resolution.return_value = files[0]
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": files
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            result = generate_enhanced_organization_plan(files, args)
            assert len(result) == 2

    def testgenerate_enhanced_organization_plan_with_subtitles(self) -> None:
        """Test enhanced organization plan with subtitle files."""
        video_file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )
        subtitle_file = Path("Attack on Titan - 01.srt")

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with (
            patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper,
            patch(
                "anivault.cli.helpers.organize.ResolutionDetector"
            ) as mock_resolution,
            patch("anivault.cli.helpers.organize.SubtitleMatcher") as mock_subtitle,
        ):
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [video_file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [video_file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = [
                subtitle_file
            ]

            # Mock the resolution detector's find_highest_resolution method
            mock_resolution.return_value.find_highest_resolution.return_value = (
                video_file
            )

            result = generate_enhanced_organization_plan([video_file], args)
            assert len(result) == 2  # Video + subtitle

    def testgenerate_enhanced_organization_plan_resolution_sorting(self) -> None:
        """Test enhanced organization plan with resolution-based sorting."""
        high_res_file = ScannedFile(
            file_path=Path("Attack on Titan - 01 (1080p).mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )
        low_res_file = ScannedFile(
            file_path=Path("Attack on Titan - 01 (720p).mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with (
            patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper,
            patch(
                "anivault.cli.helpers.organize.ResolutionDetector"
            ) as mock_resolution,
            patch("anivault.cli.helpers.organize.SubtitleMatcher") as mock_subtitle,
        ):
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [high_res_file, low_res_file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [high_res_file],
                "720p": [low_res_file],
            }
            mock_resolution.return_value.find_highest_resolution.return_value = (
                high_res_file
            )
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            result = generate_enhanced_organization_plan(
                [high_res_file, low_res_file], args
            )
            assert len(result) == 2

    def testgenerate_enhanced_organization_plan_korean_titles(self) -> None:
        """Test enhanced organization plan with Korean titles."""
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with (
            patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper,
            patch(
                "anivault.cli.helpers.organize.ResolutionDetector"
            ) as mock_resolution,
            patch("anivault.cli.helpers.organize.SubtitleMatcher") as mock_subtitle,
            patch(
                "anivault.services.metadata_enricher.MetadataEnricher"
            ) as mock_enricher,
        ):
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            # Mock the resolution detector's find_highest_resolution method
            mock_resolution.return_value.find_highest_resolution.return_value = file

            # Mock Korean title enrichment
            mock_enriched = Mock()
            mock_enriched.korean_title = "진격의 거인"
            mock_enricher.return_value.enrich_metadata.return_value = mock_enriched

            result = generate_enhanced_organization_plan([file], args)
            assert len(result) == 1

    def testgenerate_enhanced_organization_plan_error_handling(self) -> None:
        """Test enhanced organization plan error handling."""
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        # NOTE: Function now uses @handle_cli_errors decorator
        # Exceptions are converted to ApplicationError and re-raised
        from anivault.shared.errors import ApplicationError

        with patch("anivault.cli.helpers.organize.FileGrouper") as mock_grouper:
            mock_grouper.return_value.group_files.side_effect = Exception("Test error")

            # Decorator converts Exception to ApplicationError
            with pytest.raises(ApplicationError):
                generate_enhanced_organization_plan([file], args)

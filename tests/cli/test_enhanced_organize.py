"""Tests for enhanced organize command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.cli.organize_handler import _generate_enhanced_organization_plan
from anivault.core.models import ScannedFile, ParsingResult


class TestEnhancedOrganize:
    """Test cases for enhanced organize command."""

    def test_generate_enhanced_organization_plan_empty(self):
        """Test enhanced organization plan with empty file list."""
        result = _generate_enhanced_organization_plan([], Mock())
        assert result == []

    def test_generate_enhanced_organization_plan_single_file(self):
        """Test enhanced organization plan with single file."""
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )
        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with patch("anivault.core.file_grouper.FileGrouper") as mock_grouper, patch(
            "anivault.core.resolution_detector.ResolutionDetector"
        ) as mock_resolution, patch(
            "anivault.core.subtitle_matcher.SubtitleMatcher"
        ) as mock_subtitle:
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            result = _generate_enhanced_organization_plan([file], args)
            assert len(result) == 1

    def test_generate_enhanced_organization_plan_multiple_files(self):
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

        with patch("anivault.core.file_grouper.FileGrouper") as mock_grouper, patch(
            "anivault.core.resolution_detector.ResolutionDetector"
        ) as mock_resolution, patch(
            "anivault.core.subtitle_matcher.SubtitleMatcher"
        ) as mock_subtitle:
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": files
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": files
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            result = _generate_enhanced_organization_plan(files, args)
            assert len(result) == 2

    def test_generate_enhanced_organization_plan_with_subtitles(self):
        """Test enhanced organization plan with subtitle files."""
        video_file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )
        subtitle_file = Path("Attack on Titan - 01.srt")

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with patch("anivault.core.file_grouper.FileGrouper") as mock_grouper, patch(
            "anivault.core.resolution_detector.ResolutionDetector"
        ) as mock_resolution, patch(
            "anivault.core.subtitle_matcher.SubtitleMatcher"
        ) as mock_subtitle:
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [video_file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [video_file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = [
                subtitle_file
            ]

            result = _generate_enhanced_organization_plan([video_file], args)
            assert len(result) == 2  # Video + subtitle

    def test_generate_enhanced_organization_plan_resolution_sorting(self):
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

        with patch("anivault.core.file_grouper.FileGrouper") as mock_grouper, patch(
            "anivault.core.resolution_detector.ResolutionDetector"
        ) as mock_resolution, patch(
            "anivault.core.subtitle_matcher.SubtitleMatcher"
        ) as mock_subtitle:
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

            result = _generate_enhanced_organization_plan(
                [high_res_file, low_res_file], args
            )
            assert len(result) == 2

    def test_generate_enhanced_organization_plan_korean_titles(self):
        """Test enhanced organization plan with Korean titles."""
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with patch("anivault.cli.organize_handler.FileGrouper") as mock_grouper, patch(
            "anivault.cli.organize_handler.ResolutionDetector"
        ) as mock_resolution, patch(
            "anivault.cli.organize_handler.SubtitleMatcher"
        ) as mock_subtitle, patch(
            "anivault.services.metadata_enricher.MetadataEnricher"
        ) as mock_enricher:
            mock_grouper.return_value.group_files.return_value = {
                "Attack on Titan": [file]
            }
            mock_resolution.return_value.group_by_resolution.return_value = {
                "1080p": [file]
            }
            mock_subtitle.return_value.find_matching_subtitles.return_value = []

            # Mock Korean title enrichment
            mock_enriched = Mock()
            mock_enriched.korean_title = "진격의 거인"
            mock_enricher.return_value.enrich_metadata.return_value = mock_enriched

            result = _generate_enhanced_organization_plan([file], args)
            assert len(result) == 1

    def test_generate_enhanced_organization_plan_error_handling(self):
        """Test enhanced organization plan error handling."""
        file = ScannedFile(
            file_path=Path("Attack on Titan - 01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", season=1, episode=1),
        )

        args = Mock()
        args.destination = "Anime"
        args.similarity_threshold = 0.7

        with patch("anivault.core.file_grouper.FileGrouper") as mock_grouper:
            mock_grouper.return_value.group_files.side_effect = Exception("Test error")

            with pytest.raises(Exception):
                _generate_enhanced_organization_plan([file], args)

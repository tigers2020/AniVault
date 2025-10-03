"""Tests for resolution detector module."""

import pytest
from pathlib import Path

from anivault.core.resolution_detector import ResolutionDetector, ResolutionInfo, detect_file_resolution
from anivault.core.models import ScannedFile, ParsingResult


class TestResolutionDetector:
    """Test cases for ResolutionDetector class."""

    def test_detect_resolution_1080p(self):
        """Test 1080p resolution detection."""
        detector = ResolutionDetector()
        file_path = Path("[SubsPlease] Attack on Titan - 01 (1080p).mkv")
        result = detector.detect_resolution(file_path)
        
        assert result.width == 1920
        assert result.height == 1080
        assert result.quality == "1080p"
        assert result.confidence > 0.8

    def test_detect_resolution_720p(self):
        """Test 720p resolution detection."""
        detector = ResolutionDetector()
        file_path = Path("[SubsPlease] Attack on Titan - 01 (720p).mkv")
        result = detector.detect_resolution(file_path)
        
        assert result.width == 1280
        assert result.height == 720
        assert result.quality == "720p"
        assert result.confidence > 0.8

    def test_detect_resolution_4k(self):
        """Test 4K resolution detection."""
        detector = ResolutionDetector()
        file_path = Path("[SubsPlease] Attack on Titan - 01 (4K).mkv")
        result = detector.detect_resolution(file_path)
        
        assert result.width == 3840
        assert result.height == 2160
        assert result.quality == "4K"
        assert result.confidence > 0.8

    def test_detect_resolution_custom(self):
        """Test custom resolution detection."""
        detector = ResolutionDetector()
        file_path = Path("Attack on Titan - 01 (1920x1080).mkv")
        result = detector.detect_resolution(file_path)
        
        assert result.width == 1920
        assert result.height == 1080
        assert result.quality == "1080p"
        assert result.confidence > 0.7

    def test_detect_resolution_unknown(self):
        """Test unknown resolution detection."""
        detector = ResolutionDetector()
        file_path = Path("Attack on Titan - 01.mkv")
        result = detector.detect_resolution(file_path)
        
        assert result.quality is None
        assert result.confidence == 0.0

    def test_classify_resolution(self):
        """Test resolution classification."""
        detector = ResolutionDetector()
        
        # Test 4K
        quality = detector._classify_resolution(3840, 2160)
        assert quality == "4K"
        
        # Test 1080p
        quality = detector._classify_resolution(1920, 1080)
        assert quality == "1080p"
        
        # Test 720p
        quality = detector._classify_resolution(1280, 720)
        assert quality == "720p"
        
        # Test 480p
        quality = detector._classify_resolution(854, 480)
        assert quality == "480p"

    def test_group_by_resolution(self):
        """Test grouping files by resolution."""
        detector = ResolutionDetector()
        files = [
            ScannedFile(
                file_path=Path("test1_1080p.mkv"),
                metadata=ParsingResult(title="Test", season=1, episode=1)
            ),
            ScannedFile(
                file_path=Path("test2_720p.mkv"),
                metadata=ParsingResult(title="Test", season=1, episode=2)
            ),
        ]
        result = detector.group_by_resolution(files)
        assert "1080p" in result
        assert "720p" in result

    def test_find_highest_resolution(self):
        """Test finding highest resolution file."""
        detector = ResolutionDetector()
        files = [
            ScannedFile(
                file_path=Path("test1_720p.mkv"),
                metadata=ParsingResult(title="Test", season=1, episode=1)
            ),
            ScannedFile(
                file_path=Path("test2_1080p.mkv"),
                metadata=ParsingResult(title="Test", season=1, episode=2)
            ),
        ]
        result = detector.find_highest_resolution(files)
        assert result is not None
        assert "1080p" in result.file_path.name

    def test_find_highest_resolution_empty(self):
        """Test finding highest resolution with empty list."""
        detector = ResolutionDetector()
        result = detector.find_highest_resolution([])
        assert result is None

    def test_is_better_resolution(self):
        """Test resolution comparison."""
        detector = ResolutionDetector()
        
        # 1080p is better than 720p
        current = ResolutionInfo(width=1920, height=1080, quality="1080p", confidence=0.9)
        best = ResolutionInfo(width=1280, height=720, quality="720p", confidence=0.8)
        assert detector._is_better_resolution(current, best)
        
        # 720p is not better than 1080p
        current = ResolutionInfo(width=1280, height=720, quality="720p", confidence=0.9)
        best = ResolutionInfo(width=1920, height=1080, quality="1080p", confidence=0.8)
        assert not detector._is_better_resolution(current, best)

    def test_convenience_function(self):
        """Test convenience function."""
        file_path = Path("test_1080p.mkv")
        result = detect_file_resolution(file_path)
        assert isinstance(result, ResolutionInfo)

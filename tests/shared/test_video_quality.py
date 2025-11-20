"""Tests for VideoQuality classification."""

from anivault.shared.constants import VideoQuality


class TestVideoQualityClassification:
    """Test VideoQuality resolution classification."""

    def test_high_resolution_1080p(self):
        """Test 1080p is classified as high resolution."""
        assert VideoQuality.is_high_resolution("1080p") is True

    def test_high_resolution_2160p(self):
        """Test 2160p (4K) is classified as high resolution."""
        assert VideoQuality.is_high_resolution("2160p") is True

    def test_high_resolution_4k(self):
        """Test 4K is classified as high resolution."""
        assert VideoQuality.is_high_resolution("4K") is True

    def test_high_resolution_uhd(self):
        """Test UHD is classified as high resolution."""
        assert VideoQuality.is_high_resolution("UHD") is True

    def test_low_resolution_720p(self):
        """Test 720p is classified as low resolution."""
        assert VideoQuality.is_high_resolution("720p") is False

    def test_low_resolution_480p(self):
        """Test 480p is classified as low resolution."""
        assert VideoQuality.is_high_resolution("480p") is False

    def test_low_resolution_sd(self):
        """Test SD is classified as low resolution."""
        assert VideoQuality.is_high_resolution("SD") is False

    def test_case_insensitive_high(self):
        """Test case insensitive matching for high resolution."""
        assert VideoQuality.is_high_resolution("1080P") is True
        assert VideoQuality.is_high_resolution("4k") is True
        assert VideoQuality.is_high_resolution("uhd") is True

    def test_case_insensitive_low(self):
        """Test case insensitive matching for low resolution."""
        assert VideoQuality.is_high_resolution("720P") is False
        assert VideoQuality.is_high_resolution("sd") is False

    def test_unknown_resolution_defaults_to_high(self):
        """Test unknown resolution defaults to high resolution."""
        assert VideoQuality.is_high_resolution("Unknown") is True
        assert VideoQuality.is_high_resolution("9999p") is True

    def test_none_quality_defaults_to_high(self):
        """Test None quality defaults to high resolution."""
        assert VideoQuality.is_high_resolution(None) is True

    def test_empty_string_defaults_to_high(self):
        """Test empty string defaults to high resolution."""
        assert VideoQuality.is_high_resolution("") is True

    def test_low_res_folder_constant(self):
        """Test LOW_RES_FOLDER constant is defined."""
        assert VideoQuality.LOW_RES_FOLDER == "low_res"

    def test_high_resolution_list(self):
        """Test HIGH_RESOLUTION list is properly defined."""
        assert isinstance(VideoQuality.HIGH_RESOLUTION, list)
        assert "1080p" in VideoQuality.HIGH_RESOLUTION
        assert "2160p" in VideoQuality.HIGH_RESOLUTION
        assert "4K" in VideoQuality.HIGH_RESOLUTION

    def test_low_resolution_list(self):
        """Test LOW_RESOLUTION list is properly defined."""
        assert isinstance(VideoQuality.LOW_RESOLUTION, list)
        assert "720p" in VideoQuality.LOW_RESOLUTION
        assert "480p" in VideoQuality.LOW_RESOLUTION
        assert "SD" in VideoQuality.LOW_RESOLUTION

    def test_complex_quality_string_high(self):
        """Test complex quality string with high resolution."""
        assert VideoQuality.is_high_resolution("1080p HEVC AAC") is True
        assert VideoQuality.is_high_resolution("[1080p] x264") is True

    def test_complex_quality_string_low(self):
        """Test complex quality string with low resolution."""
        assert VideoQuality.is_high_resolution("720p HEVC AAC") is False
        assert VideoQuality.is_high_resolution("[720p] x264") is False

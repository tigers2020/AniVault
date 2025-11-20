"""
Tests for encoding utilities error handling improvements.

This module tests the structured error handling implemented in the
encoding utilities, ensuring that file system errors are properly
handled with appropriate logging and fallbacks.
"""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from anivault.utils.encoding import get_file_encoding


class TestEncodingErrorHandling:
    """Test error handling in encoding utilities."""

    def test_detect_encoding_permission_error(self):
        """Test that PermissionError is handled gracefully with fallback."""
        file_path = "/test/file.txt"

        with patch("pathlib.Path.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")

            # Should not raise exception, should fallback to UTF-8
            encoding = get_file_encoding(file_path)
            assert encoding == "utf-8"

    def test_detect_encoding_os_error(self):
        """Test that OSError is handled gracefully with fallback."""
        file_path = "/test/file.txt"

        with patch("pathlib.Path.open", mock_open()) as mock_file:
            mock_file.side_effect = OSError("File not found")

            # Should not raise exception, should fallback to UTF-8
            encoding = get_file_encoding(file_path)
            assert encoding == "utf-8"

    def test_detect_encoding_unicode_decode_error(self):
        """Test that UnicodeDecodeError is handled gracefully with fallback."""
        file_path = "/test/file.txt"

        with patch("pathlib.Path.open", mock_open()) as mock_file:
            mock_file.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

            # Should not raise exception, should fallback to UTF-8
            encoding = get_file_encoding(file_path)
            assert encoding == "utf-8"

    def test_detect_encoding_value_error(self):
        """Test that ValueError is handled gracefully with fallback."""
        file_path = "/test/file.txt"

        with patch("chardet.detect") as mock_detect:
            mock_detect.side_effect = ValueError("Invalid data")

            # Should not raise exception, should fallback to UTF-8
            encoding = get_file_encoding(file_path)
            assert encoding == "utf-8"

    def test_detect_encoding_import_error_fallback(self):
        """Test that ImportError for chardet is handled with fallback."""
        file_path = "/test/file.txt"

        with patch("chardet.detect", side_effect=ImportError("chardet not available")):
            # Should not raise exception, should fallback to UTF-8
            encoding = get_file_encoding(file_path)
            assert encoding == "utf-8"

    def test_detect_encoding_success(self):
        """Test successful encoding detection."""
        file_path = "/test/file.txt"

        with patch("pathlib.Path.open", mock_open(read_data=b"test content")):
            with patch("chardet.detect") as mock_detect:
                mock_detect.return_value = {"encoding": "iso-8859-1", "confidence": 0.8}

                encoding = get_file_encoding(file_path)
                assert encoding == "iso-8859-1"

    def test_detect_encoding_no_encoding_detected_fallback(self):
        """Test fallback when no encoding is detected."""
        file_path = "/test/file.txt"

        with patch("pathlib.Path.open", mock_open(read_data=b"test content")):
            with patch("chardet.detect") as mock_detect:
                mock_detect.return_value = {"encoding": None, "confidence": 0.0}

                encoding = get_file_encoding(file_path)
                assert encoding == "utf-8"

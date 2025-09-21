"""Tests for improved compression serialization/deserialization system."""

import base64
import json
import zlib
from unittest.mock import patch

import pytest

from src.core.compression import (
    CacheDeserializationError,
    CompressionManager,
    CompressionStats,
    VersionedDataWrapper,
)


class TestVersionedDataWrapper:
    """Test the VersionedDataWrapper class."""

    def test_to_dict(self):
        """Test converting wrapper to dictionary."""
        wrapper = VersionedDataWrapper(
            version=1,
            data_type="dict",
            compressed=True,
            data="dGVzdA=="  # base64 for "test"
        )

        result = wrapper.to_dict()
        expected = {
            "v": 1,
            "type": "dict",
            "compressed": True,
            "data": "dGVzdA=="
        }

        assert result == expected

    def test_from_dict(self):
        """Test creating wrapper from dictionary."""
        data = {
            "v": 1,
            "type": "str",
            "compressed": False,
            "data": "dGVzdA=="
        }

        wrapper = VersionedDataWrapper.from_dict(data)

        assert wrapper.version == 1
        assert wrapper.data_type == "str"
        assert wrapper.compressed is False
        assert wrapper.data == "dGVzdA=="


class TestCompressionManagerSerialization:
    """Test the improved serialization/deserialization methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.compression_manager = CompressionManager(
            compression_level=6,
            min_size_threshold=10,  # Lower threshold for testing
            max_compression_ratio=0.8
        )

    def test_compress_for_storage_dict(self):
        """Test compressing dictionary data for storage."""
        test_data = {"key": "value", "nested": {"inner": "data"}}

        result = self.compression_manager.compress_for_storage(test_data)

        # Should be JSON string
        assert isinstance(result, str)

        # Parse and validate structure
        wrapper_dict = json.loads(result)
        assert "v" in wrapper_dict
        assert "type" in wrapper_dict
        assert "compressed" in wrapper_dict
        assert "data" in wrapper_dict
        assert wrapper_dict["type"] == "dict"

    def test_compress_for_storage_string(self):
        """Test compressing string data for storage."""
        test_data = "This is a test string"

        result = self.compression_manager.compress_for_storage(test_data)

        # Should be JSON string
        assert isinstance(result, str)

        # Parse and validate structure
        wrapper_dict = json.loads(result)
        assert wrapper_dict["type"] == "str"

    def test_compress_for_storage_bytes(self):
        """Test compressing bytes data for storage."""
        test_data = b"This is test bytes data"

        result = self.compression_manager.compress_for_storage(test_data)

        # Should be JSON string
        assert isinstance(result, str)

        # Parse and validate structure
        wrapper_dict = json.loads(result)
        assert wrapper_dict["type"] == "bytes"

    def test_compress_for_storage_small_data(self):
        """Test that small data is stored uncompressed."""
        test_data = "small"  # Less than min_size_threshold

        result = self.compression_manager.compress_for_storage(test_data)
        wrapper_dict = json.loads(result)

        # Should not be compressed
        assert wrapper_dict["compressed"] is False

    def test_compress_for_storage_large_data(self):
        """Test that large data is compressed when beneficial."""
        # Create data larger than threshold
        test_data = {"large": "x" * 1000}  # Large enough to trigger compression

        result = self.compression_manager.compress_for_storage(test_data)
        wrapper_dict = json.loads(result)

        # Should be compressed
        assert wrapper_dict["compressed"] is True

    def test_compress_for_storage_none(self):
        """Test handling of None data."""
        result = self.compression_manager.compress_for_storage(None)
        assert result is None

    def test_decompress_from_storage_versioned_format(self):
        """Test decompressing versioned format data."""
        # First compress some data
        original_data = {"test": "data", "number": 42}
        compressed = self.compression_manager.compress_for_storage(original_data)

        # Then decompress it
        decompressed = self.compression_manager.decompress_from_storage(compressed)

        assert decompressed == original_data

    def test_decompress_from_storage_legacy_format(self):
        """Test decompressing legacy format data for backward compatibility."""
        # Simulate legacy format (just base64 encoded compressed data)
        import base64

        original_data = {"legacy": "data"}
        json_data = json.dumps(original_data, ensure_ascii=False)
        compressed_bytes = zlib.compress(json_data.encode("utf-8"))
        legacy_data = base64.b64encode(compressed_bytes).decode("ascii")

        # Decompress using legacy format
        decompressed = self.compression_manager.decompress_from_storage(
            legacy_data, expected_type="dict"
        )

        assert decompressed == original_data

    def test_decompress_from_storage_legacy_json(self):
        """Test decompressing legacy JSON format data."""
        original_data = {"legacy": "json"}
        legacy_json = json.dumps(original_data, ensure_ascii=False)

        # Decompress using legacy format
        decompressed = self.compression_manager.decompress_from_storage(
            legacy_json, expected_type="dict"
        )

        assert decompressed == original_data

    def test_decompress_from_storage_empty_string(self):
        """Test handling of empty string."""
        result = self.compression_manager.decompress_from_storage("")
        assert result is None

    def test_decompress_from_storage_invalid_json(self):
        """Test handling of invalid JSON data."""
        with pytest.raises(CacheDeserializationError):
            self.compression_manager.decompress_from_storage("invalid json data")

    def test_decompress_from_storage_invalid_wrapper_structure(self):
        """Test handling of invalid wrapper structure."""
        # Test with missing required fields - should fallback to legacy format
        invalid_wrapper = {"v": 1, "type": "dict"}  # Missing required fields

        # This should fallback to legacy format and try to parse as JSON
        # Since the invalid wrapper is valid JSON, it should be parsed as dict
        result = self.compression_manager.decompress_from_storage(
            json.dumps(invalid_wrapper), expected_type="dict"
        )
        assert result == invalid_wrapper

    def test_decompress_from_storage_invalid_base64(self):
        """Test handling of invalid base64 data in wrapper."""
        invalid_wrapper = {
            "v": 1,
            "type": "dict",
            "compressed": False,
            "data": "invalid base64 data!"
        }

        with pytest.raises(CacheDeserializationError):
            self.compression_manager.decompress_from_storage(
                json.dumps(invalid_wrapper)
            )

    def test_decompress_from_storage_unknown_data_type(self):
        """Test handling of unknown data type in wrapper."""
        wrapper = {
            "v": 1,
            "type": "unknown_type",
            "compressed": False,
            "data": "dGVzdA=="
        }

        with pytest.raises(CacheDeserializationError):
            self.compression_manager.decompress_from_storage(json.dumps(wrapper))

    def test_decompress_from_storage_decompression_failure(self):
        """Test handling of decompression failure."""
        # Create wrapper with compressed data but invalid compressed bytes
        wrapper = {
            "v": 1,
            "type": "dict",
            "compressed": True,
            "data": "dGVzdA=="  # Valid base64 but not valid compressed data
        }

        with pytest.raises(CacheDeserializationError):
            self.compression_manager.decompress_from_storage(json.dumps(wrapper))

    def test_round_trip_dict(self):
        """Test complete round trip for dictionary data."""
        original_data = {"key": "value", "nested": {"inner": "data"}, "list": [1, 2, 3]}

        compressed = self.compression_manager.compress_for_storage(original_data)
        decompressed = self.compression_manager.decompress_from_storage(compressed)

        assert decompressed == original_data

    def test_round_trip_string(self):
        """Test complete round trip for string data."""
        original_data = "This is a test string with special chars: àáâãäå"

        compressed = self.compression_manager.compress_for_storage(original_data)
        decompressed = self.compression_manager.decompress_from_storage(compressed)

        assert decompressed == original_data

    def test_round_trip_bytes(self):
        """Test complete round trip for bytes data."""
        original_data = b"This is test bytes data with \x00\x01\x02"

        compressed = self.compression_manager.compress_for_storage(original_data)
        decompressed = self.compression_manager.decompress_from_storage(compressed)

        assert decompressed == original_data

    def test_round_trip_large_data(self):
        """Test complete round trip for large data that gets compressed."""
        original_data = {
            "large_string": "x" * 2000,
            "nested": {
                "inner": "y" * 1000,
                "list": list(range(100))
            }
        }

        compressed = self.compression_manager.compress_for_storage(original_data)
        decompressed = self.compression_manager.decompress_from_storage(compressed)

        assert decompressed == original_data

    def test_compression_efficiency_threshold(self):
        """Test that compression is only applied when efficient."""
        # Create data that compresses poorly
        test_data = "a" * 1000  # Repetitive data that compresses well

        result = self.compression_manager.compress_for_storage(test_data)
        wrapper_dict = json.loads(result)

        # Should be compressed due to good compression ratio
        assert wrapper_dict["compressed"] is True

    def test_compression_inefficiency_fallback(self):
        """Test fallback when compression is not efficient."""
        # Mock the compression to always fail efficiency check
        with patch.object(self.compression_manager, 'compress_data') as mock_compress:
            mock_compress.side_effect = ValueError("Compression not efficient")

            test_data = {"key": "value"}
            result = self.compression_manager.compress_for_storage(test_data)
            wrapper_dict = json.loads(result)

            # Should not be compressed
            assert wrapper_dict["compressed"] is False

    def test_schema_version_handling(self):
        """Test handling of different schema versions."""
        # Test with version 1 (current) - create valid data
        test_data = {"key": "value"}
        json_data = json.dumps(test_data)
        encoded_data = base64.b64encode(json_data.encode("utf-8")).decode("ascii")

        wrapper = {
            "v": 1,
            "type": "dict",
            "compressed": False,
            "data": encoded_data
        }

        result = self.compression_manager.decompress_from_storage(json.dumps(wrapper))
        assert result == test_data

    def test_error_handling_with_original_error(self):
        """Test that CacheDeserializationError preserves original error."""
        try:
            self.compression_manager.decompress_from_storage("invalid data")
        except CacheDeserializationError as e:
            assert e.original_error is not None
            # Check for any of the possible error messages
            error_msg = str(e)
            assert any(msg in error_msg for msg in [
                "Failed to deserialize data",
                "Failed to parse legacy data as JSON"
            ])


class TestCompressionStats:
    """Test the CompressionStats class."""

    def test_space_saved_calculation(self):
        """Test space saved calculation."""
        stats = CompressionStats(
            original_size=1000,
            compressed_size=500,
            compression_ratio=0.5,
            compression_time_ms=10.0,
            decompression_time_ms=5.0
        )

        assert stats.space_saved == 500
        assert stats.space_saved_percent == 50.0

    def test_space_saved_percent_zero_original(self):
        """Test space saved percentage with zero original size."""
        stats = CompressionStats(
            original_size=0,
            compressed_size=0,
            compression_ratio=0.0,
            compression_time_ms=0.0,
            decompression_time_ms=0.0
        )

        assert stats.space_saved_percent == 0.0

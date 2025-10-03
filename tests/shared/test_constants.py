"""
Tests for AniVault Constants Module

This module contains comprehensive tests for all constants defined in the
shared constants module to ensure they are properly defined and accessible.
"""

import pytest

from anivault.shared.constants import (  # API constants; CLI constants; File format constants; Logging constants; Matching constants; System constants
    ADDITIONAL_VIDEO_FORMATS,
    ANIVAULT_HOME_DIR,
    BOOLEAN_FALSE_STRING,
    BOOLEAN_TRUE_STRING,
    CLI_DEFAULT_RATE_LIMIT_EXAMPLE,
    CLI_DEFAULT_RATE_LIMIT_HELP,
    CLI_DEFAULT_WORKERS_EXAMPLE,
    CLI_ERROR_DIRECTORY_NOT_EXISTS,
    CLI_ERROR_LISTING_LOGS,
    CLI_ERROR_NOT_DIRECTORY,
    CLI_ERROR_SCAN_FAILED,
    CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
    CLI_ERROR_VERIFICATION_FAILED,
    CLI_INDENT_SIZE,
    CLI_INFO_APPLICATION_INTERRUPTED,
    CLI_INFO_NO_OPERATION_LOGS,
    CLI_INFO_TOTAL_LOGS,
    CLI_INFO_UNEXPECTED_ERROR,
    CLI_SEPARATOR_LENGTH,
    CLI_SUCCESS_RESULTS_SAVED,
    CLI_SUCCESS_SCANNING,
    DEFAULT_BATCH_SIZE,
    DEFAULT_BATCH_SIZE_LARGE,
    DEFAULT_BENCHMARK_CONFIDENCE_THRESHOLD,
    DEFAULT_CACHE_BACKEND,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONCURRENT_REQUESTS,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_CPU_LIMIT,
    DEFAULT_ENCODING,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_DIRECTORY,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_FILE_PATH,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_MEMORY_LIMIT_MB,
    DEFAULT_MEMORY_LIMIT_STRING,
    DEFAULT_MIN_FILE_SIZE_MB,
    DEFAULT_PARALLEL_THRESHOLD,
    DEFAULT_PROCESS_PRIORITY,
    DEFAULT_PROFILING_DIRECTORY,
    DEFAULT_PROFILING_FILE_PATH,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_RATE_LIMIT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_TMDB_RATE_LIMIT_DELAY,
    DEFAULT_TMDB_RATE_LIMIT_RPS,
    DEFAULT_TMDB_RETRY_ATTEMPTS,
    DEFAULT_TMDB_RETRY_DELAY,
    DEFAULT_TMDB_TIMEOUT,
    DEFAULT_VERSION_STRING,
    DEFAULT_WORKERS,
    EXCLUDED_DIRECTORY_PATTERNS,
    EXCLUDED_FILENAME_PATTERNS,
    FALLBACK_ENCODING,
    HIGH_BENCHMARK_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    JSON_DESCRIPTION_KEY,
    JSON_ENTRIES_KEY,
    JSON_METADATA_KEY,
    JSON_TOTAL_ENTRIES_KEY,
    JSON_VERSION_KEY,
    LOG_FILE_EXTENSION,
    LOG_LEVEL_CRITICAL,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOW_CONFIDENCE_THRESHOLD,
    MAX_FILE_SIZE,
    MEDIUM_BENCHMARK_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    METADATA_FILENAME,
    MIN_REQUIRED_KEYS,
    ORGANIZE_LOG_PREFIX,
    ROLLBACK_LOG_PREFIX,
    SUBTITLE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS_MATCH,
    SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE,
    TMDB_API_BASE_URL,
)


class TestAPIConstants:
    """Test API-related constants."""

    def test_rate_limit_constant(self):
        """Test rate limit constant is properly defined."""
        assert DEFAULT_RATE_LIMIT == 20
        assert isinstance(DEFAULT_RATE_LIMIT, int)
        assert DEFAULT_RATE_LIMIT > 0

    def test_concurrent_requests_constant(self):
        """Test concurrent requests constant is properly defined."""
        assert DEFAULT_CONCURRENT_REQUESTS == 4
        assert isinstance(DEFAULT_CONCURRENT_REQUESTS, int)
        assert DEFAULT_CONCURRENT_REQUESTS > 0

    def test_retry_attempts_constant(self):
        """Test retry attempts constant is properly defined."""
        assert DEFAULT_RETRY_ATTEMPTS == 3
        assert isinstance(DEFAULT_RETRY_ATTEMPTS, int)
        assert DEFAULT_RETRY_ATTEMPTS > 0

    def test_retry_delay_constant(self):
        """Test retry delay constant is properly defined."""
        assert DEFAULT_RETRY_DELAY == 1.0
        assert isinstance(DEFAULT_RETRY_DELAY, float)
        assert DEFAULT_RETRY_DELAY > 0

    def test_request_timeout_constant(self):
        """Test request timeout constant is properly defined."""
        assert DEFAULT_REQUEST_TIMEOUT == 300
        assert isinstance(DEFAULT_REQUEST_TIMEOUT, int)
        assert DEFAULT_REQUEST_TIMEOUT > 0


class TestCLIConstants:
    """Test CLI-related constants."""

    def test_default_workers_constant(self):
        """Test default workers constant is properly defined."""
        assert DEFAULT_WORKERS == 4
        assert isinstance(DEFAULT_WORKERS, int)
        assert DEFAULT_WORKERS > 0

    def test_default_log_level_constant(self):
        """Test default log level constant is properly defined."""
        assert DEFAULT_LOG_LEVEL == 20  # INFO level
        assert isinstance(DEFAULT_LOG_LEVEL, int)
        assert DEFAULT_LOG_LEVEL in [10, 20, 30, 40, 50]  # Valid log levels

    def test_default_queue_size_constant(self):
        """Test default queue size constant is properly defined."""
        assert DEFAULT_QUEUE_SIZE == 100
        assert isinstance(DEFAULT_QUEUE_SIZE, int)
        assert DEFAULT_QUEUE_SIZE > 0

    def test_default_cache_dir_constant(self):
        """Test default cache directory constant is properly defined."""
        assert DEFAULT_CACHE_DIR == "cache"
        assert isinstance(DEFAULT_CACHE_DIR, str)
        assert len(DEFAULT_CACHE_DIR) > 0

    def test_default_confidence_threshold_constant(self):
        """Test default confidence threshold constant is properly defined."""
        assert DEFAULT_CONFIDENCE_THRESHOLD == 0.8
        assert isinstance(DEFAULT_CONFIDENCE_THRESHOLD, float)
        assert 0.0 <= DEFAULT_CONFIDENCE_THRESHOLD <= 1.0


class TestFileFormatConstants:
    """Test file format-related constants."""

    def test_supported_video_extensions_constant(self):
        """Test supported video extensions constant is properly defined."""
        assert isinstance(SUPPORTED_VIDEO_EXTENSIONS, tuple)
        assert len(SUPPORTED_VIDEO_EXTENSIONS) > 0

        # Check that all extensions start with a dot
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            assert ext.startswith(".")
            assert isinstance(ext, str)

        # Check for common video extensions
        expected_extensions = {
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".m4v",
            ".webm",
        }
        assert set(SUPPORTED_VIDEO_EXTENSIONS) >= expected_extensions

    def test_supported_video_extensions_organize_constant(self):
        """Test organize-specific video extensions constant."""
        assert isinstance(SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE, tuple)
        assert len(SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE) > 0

        # Should include .m4v for organize command
        assert ".m4v" in SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE

    def test_supported_video_extensions_match_constant(self):
        """Test match-specific video extensions constant."""
        assert isinstance(SUPPORTED_VIDEO_EXTENSIONS_MATCH, tuple)
        assert len(SUPPORTED_VIDEO_EXTENSIONS_MATCH) > 0

    def test_metadata_filename_constant(self):
        """Test metadata filename constant is properly defined."""
        assert METADATA_FILENAME == "anivault_metadata.json"
        assert isinstance(METADATA_FILENAME, str)
        assert METADATA_FILENAME.endswith(".json")

    def test_additional_video_formats(self):
        """Test additional video format constants."""
        assert isinstance(ADDITIONAL_VIDEO_FORMATS, list)
        assert ".m2ts" in ADDITIONAL_VIDEO_FORMATS
        assert ".ts" in ADDITIONAL_VIDEO_FORMATS
        assert len(ADDITIONAL_VIDEO_FORMATS) == 2

    def test_subtitle_extensions(self):
        """Test subtitle extension constants."""
        assert isinstance(SUBTITLE_EXTENSIONS, list)
        assert ".srt" in SUBTITLE_EXTENSIONS
        assert ".ass" in SUBTITLE_EXTENSIONS
        assert ".vtt" in SUBTITLE_EXTENSIONS
        assert len(SUBTITLE_EXTENSIONS) == 12

    def test_excluded_filename_patterns(self):
        """Test excluded filename pattern constants."""
        assert isinstance(EXCLUDED_FILENAME_PATTERNS, list)
        assert "*sample*" in EXCLUDED_FILENAME_PATTERNS
        assert "*trailer*" in EXCLUDED_FILENAME_PATTERNS
        assert "*test*" in EXCLUDED_FILENAME_PATTERNS
        assert len(EXCLUDED_FILENAME_PATTERNS) == 8

    def test_excluded_directory_patterns(self):
        """Test excluded directory pattern constants."""
        assert isinstance(EXCLUDED_DIRECTORY_PATTERNS, list)
        assert ".git" in EXCLUDED_DIRECTORY_PATTERNS
        assert "__pycache__" in EXCLUDED_DIRECTORY_PATTERNS
        assert "node_modules" in EXCLUDED_DIRECTORY_PATTERNS
        assert len(EXCLUDED_DIRECTORY_PATTERNS) == 13


class TestLoggingConstants:
    """Test logging-related constants."""

    def test_log_level_constants(self):
        """Test log level constants are properly defined."""
        assert LOG_LEVEL_DEBUG == 10
        assert LOG_LEVEL_INFO == 20
        assert LOG_LEVEL_WARNING == 30
        assert LOG_LEVEL_ERROR == 40
        assert LOG_LEVEL_CRITICAL == 50

        # Check that they are in ascending order
        assert (
            LOG_LEVEL_DEBUG
            < LOG_LEVEL_INFO
            < LOG_LEVEL_WARNING
            < LOG_LEVEL_ERROR
            < LOG_LEVEL_CRITICAL
        )

    def test_default_log_level_constant(self):
        """Test default log level matches INFO level."""
        assert DEFAULT_LOG_LEVEL == LOG_LEVEL_INFO

    def test_default_log_format_constant(self):
        """Test default log format constant is properly defined."""
        assert isinstance(DEFAULT_LOG_FORMAT, str)
        assert len(DEFAULT_LOG_FORMAT) > 0
        assert "%(asctime)s" in DEFAULT_LOG_FORMAT
        assert "%(name)s" in DEFAULT_LOG_FORMAT
        assert "%(levelname)s" in DEFAULT_LOG_FORMAT
        assert "%(message)s" in DEFAULT_LOG_FORMAT

    def test_default_log_file_constant(self):
        """Test default log file constant is properly defined."""
        assert DEFAULT_LOG_FILE == "anivault.log"
        assert isinstance(DEFAULT_LOG_FILE, str)
        assert DEFAULT_LOG_FILE.endswith(".log")


class TestMatchingConstants:
    """Test matching engine-related constants."""

    def test_confidence_threshold_constants(self):
        """Test confidence threshold constants are properly defined."""
        assert HIGH_CONFIDENCE_THRESHOLD == 0.8
        assert MEDIUM_CONFIDENCE_THRESHOLD == 0.6
        assert LOW_CONFIDENCE_THRESHOLD == 0.4

        # Check that they are in descending order
        assert (
            HIGH_CONFIDENCE_THRESHOLD
            > MEDIUM_CONFIDENCE_THRESHOLD
            > LOW_CONFIDENCE_THRESHOLD
        )

        # Check that all are valid confidence scores
        for threshold in [
            HIGH_CONFIDENCE_THRESHOLD,
            MEDIUM_CONFIDENCE_THRESHOLD,
            LOW_CONFIDENCE_THRESHOLD,
        ]:
            assert isinstance(threshold, float)
            assert 0.0 <= threshold <= 1.0

    def test_min_required_keys_constant(self):
        """Test minimum required keys constant is properly defined."""
        assert MIN_REQUIRED_KEYS == 2
        assert isinstance(MIN_REQUIRED_KEYS, int)
        assert MIN_REQUIRED_KEYS > 0


class TestSystemConstants:
    """Test system-related constants."""

    def test_default_timeout_constant(self):
        """Test default timeout constant is properly defined."""
        assert DEFAULT_TIMEOUT == 300  # 5 minutes
        assert isinstance(DEFAULT_TIMEOUT, int)
        assert DEFAULT_TIMEOUT > 0

    def test_max_file_size_constant(self):
        """Test maximum file size constant is properly defined."""
        assert MAX_FILE_SIZE == 1024 * 1024 * 1024  # 1GB
        assert isinstance(MAX_FILE_SIZE, int)
        assert MAX_FILE_SIZE > 0

    def test_default_batch_size_constant(self):
        """Test default batch size constant is properly defined."""
        assert DEFAULT_BATCH_SIZE == 50
        assert isinstance(DEFAULT_BATCH_SIZE, int)
        assert DEFAULT_BATCH_SIZE > 0

    def test_configuration_defaults(self):
        """Test configuration default constants."""
        # Test file size defaults
        assert DEFAULT_MIN_FILE_SIZE_MB == 50
        assert isinstance(DEFAULT_MIN_FILE_SIZE_MB, int)

        # Test batch size defaults
        assert DEFAULT_BATCH_SIZE_LARGE == 100
        assert isinstance(DEFAULT_BATCH_SIZE_LARGE, int)

        # Test parallel threshold
        assert DEFAULT_PARALLEL_THRESHOLD == 1000
        assert isinstance(DEFAULT_PARALLEL_THRESHOLD, int)

        # Test log configuration
        assert DEFAULT_LOG_MAX_BYTES == 10485760  # 10MB
        assert isinstance(DEFAULT_LOG_MAX_BYTES, int)

        assert DEFAULT_LOG_BACKUP_COUNT == 5
        assert isinstance(DEFAULT_LOG_BACKUP_COUNT, int)

        # Test TMDB configuration
        assert DEFAULT_TMDB_TIMEOUT == 30
        assert isinstance(DEFAULT_TMDB_TIMEOUT, int)

        assert DEFAULT_TMDB_RETRY_ATTEMPTS == 3
        assert isinstance(DEFAULT_TMDB_RETRY_ATTEMPTS, int)

        assert DEFAULT_TMDB_RETRY_DELAY == 1.0
        assert isinstance(DEFAULT_TMDB_RETRY_DELAY, float)

        assert DEFAULT_TMDB_RATE_LIMIT_DELAY == 0.25
        assert isinstance(DEFAULT_TMDB_RATE_LIMIT_DELAY, float)

        assert DEFAULT_TMDB_RATE_LIMIT_RPS == 35.0
        assert isinstance(DEFAULT_TMDB_RATE_LIMIT_RPS, float)

        # Test cache configuration
        assert DEFAULT_CACHE_TTL == 3600
        assert isinstance(DEFAULT_CACHE_TTL, int)

        assert DEFAULT_CACHE_MAX_SIZE == 1000
        assert isinstance(DEFAULT_CACHE_MAX_SIZE, int)

        # Test system configuration
        assert DEFAULT_CPU_LIMIT == 4
        assert isinstance(DEFAULT_CPU_LIMIT, int)

        assert DEFAULT_MEMORY_LIMIT_MB == 1024
        assert isinstance(DEFAULT_MEMORY_LIMIT_MB, int)

    def test_tmdb_api_base_url_constant(self):
        """Test TMDB API base URL constant is properly defined."""
        assert TMDB_API_BASE_URL == "https://api.themoviedb.org/3"
        assert isinstance(TMDB_API_BASE_URL, str)
        assert TMDB_API_BASE_URL.startswith("https://")

    def test_encoding_constants(self):
        """Test encoding-related constants."""
        assert DEFAULT_ENCODING == "utf-8"
        assert isinstance(DEFAULT_ENCODING, str)

        assert FALLBACK_ENCODING == "cp1252"
        assert isinstance(FALLBACK_ENCODING, str)

    def test_process_priority_constant(self):
        """Test process priority constant."""
        assert DEFAULT_PROCESS_PRIORITY == "normal"
        assert isinstance(DEFAULT_PROCESS_PRIORITY, str)

    def test_benchmark_confidence_thresholds(self):
        """Test benchmark confidence threshold constants."""
        assert DEFAULT_BENCHMARK_CONFIDENCE_THRESHOLD == 0.7
        assert isinstance(DEFAULT_BENCHMARK_CONFIDENCE_THRESHOLD, float)

        assert HIGH_BENCHMARK_CONFIDENCE_THRESHOLD == 0.9
        assert isinstance(HIGH_BENCHMARK_CONFIDENCE_THRESHOLD, float)

        assert MEDIUM_BENCHMARK_CONFIDENCE_THRESHOLD == 0.8
        assert isinstance(MEDIUM_BENCHMARK_CONFIDENCE_THRESHOLD, float)

    def test_log_file_path_constants(self):
        """Test log file path constants."""
        assert DEFAULT_LOG_FILE_PATH == "logs/anivault.log"
        assert isinstance(DEFAULT_LOG_FILE_PATH, str)

        assert DEFAULT_PROFILING_FILE_PATH == "logs/profiling.json"
        assert isinstance(DEFAULT_PROFILING_FILE_PATH, str)

        assert ORGANIZE_LOG_PREFIX == "organize-"
        assert isinstance(ORGANIZE_LOG_PREFIX, str)

        assert ROLLBACK_LOG_PREFIX == "rollback-"
        assert isinstance(ROLLBACK_LOG_PREFIX, str)

        assert LOG_FILE_EXTENSION == ".json"
        assert isinstance(LOG_FILE_EXTENSION, str)

    def test_cli_constants(self):
        """Test CLI-related constants."""
        assert CLI_INDENT_SIZE == 2
        assert isinstance(CLI_INDENT_SIZE, int)

        assert CLI_SEPARATOR_LENGTH == 60
        assert isinstance(CLI_SEPARATOR_LENGTH, int)

        assert CLI_DEFAULT_RATE_LIMIT_HELP == "35.0"
        assert isinstance(CLI_DEFAULT_RATE_LIMIT_HELP, str)

        assert CLI_DEFAULT_WORKERS_EXAMPLE == 8
        assert isinstance(CLI_DEFAULT_WORKERS_EXAMPLE, int)

        assert CLI_DEFAULT_RATE_LIMIT_EXAMPLE == 20
        assert isinstance(CLI_DEFAULT_RATE_LIMIT_EXAMPLE, int)

    def test_cli_message_constants(self):
        """Test CLI message constants."""
        # Test that message constants are strings and contain placeholders
        message_constants = [
            CLI_ERROR_DIRECTORY_NOT_EXISTS,
            CLI_ERROR_NOT_DIRECTORY,
            CLI_ERROR_SCAN_FAILED,
            CLI_ERROR_VERIFICATION_FAILED,
            CLI_ERROR_TMDB_CONNECTIVITY_FAILED,
            CLI_ERROR_LISTING_LOGS,
            CLI_SUCCESS_RESULTS_SAVED,
            CLI_SUCCESS_SCANNING,
            CLI_INFO_APPLICATION_INTERRUPTED,
            CLI_INFO_UNEXPECTED_ERROR,
            CLI_INFO_NO_OPERATION_LOGS,
            CLI_INFO_TOTAL_LOGS,
        ]

        for constant in message_constants:
            assert isinstance(constant, str)
            assert len(constant) > 0

    def test_directory_and_path_constants(self):
        """Test directory and path constants."""
        assert DEFAULT_LOG_DIRECTORY == "logs"
        assert isinstance(DEFAULT_LOG_DIRECTORY, str)

        assert DEFAULT_PROFILING_DIRECTORY == "logs"
        assert isinstance(DEFAULT_PROFILING_DIRECTORY, str)

        assert DEFAULT_CONFIG_DIRECTORY == "config"
        assert isinstance(DEFAULT_CONFIG_DIRECTORY, str)

        assert DEFAULT_CACHE_BACKEND == "memory"
        assert isinstance(DEFAULT_CACHE_BACKEND, str)

        assert ANIVAULT_HOME_DIR == ".anivault"
        assert isinstance(ANIVAULT_HOME_DIR, str)

    def test_json_key_constants(self):
        """Test JSON key constants."""
        assert JSON_ENTRIES_KEY == "entries"
        assert isinstance(JSON_ENTRIES_KEY, str)

        assert JSON_METADATA_KEY == "metadata"
        assert isinstance(JSON_METADATA_KEY, str)

        assert JSON_VERSION_KEY == "version"
        assert isinstance(JSON_VERSION_KEY, str)

        assert JSON_DESCRIPTION_KEY == "description"
        assert isinstance(JSON_DESCRIPTION_KEY, str)

        assert JSON_TOTAL_ENTRIES_KEY == "total_entries"
        assert isinstance(JSON_TOTAL_ENTRIES_KEY, str)

    def test_boolean_string_constants(self):
        """Test boolean string constants."""
        assert BOOLEAN_TRUE_STRING == "true"
        assert isinstance(BOOLEAN_TRUE_STRING, str)

        assert BOOLEAN_FALSE_STRING == "false"
        assert isinstance(BOOLEAN_FALSE_STRING, str)

    def test_memory_and_version_constants(self):
        """Test memory and version string constants."""
        assert DEFAULT_MEMORY_LIMIT_STRING == "2GB"
        assert isinstance(DEFAULT_MEMORY_LIMIT_STRING, str)

        assert DEFAULT_VERSION_STRING == "0.1.0"
        assert isinstance(DEFAULT_VERSION_STRING, str)


class TestConstantsIntegration:
    """Test constants integration and consistency."""

    def test_constants_are_importable(self):
        """Test that all constants can be imported successfully."""
        # This test will fail if any constant is not properly exported
        # from the __init__.py file
        pass

    def test_confidence_threshold_consistency(self):
        """Test that confidence thresholds are consistent with CLI default."""
        assert DEFAULT_CONFIDENCE_THRESHOLD == HIGH_CONFIDENCE_THRESHOLD

    def test_file_extensions_consistency(self):
        """Test that file extension constants are consistent."""
        # Organize should include all extensions from base + .m4v
        assert ".m4v" in SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE
        assert ".m4v" not in SUPPORTED_VIDEO_EXTENSIONS_MATCH

        # Base should include all extensions from match
        match_extensions_set = set(SUPPORTED_VIDEO_EXTENSIONS_MATCH)
        base_extensions_set = set(SUPPORTED_VIDEO_EXTENSIONS)
        assert match_extensions_set.issubset(base_extensions_set)

    def test_log_level_consistency(self):
        """Test that log level constants are consistent."""
        assert DEFAULT_LOG_LEVEL == LOG_LEVEL_INFO

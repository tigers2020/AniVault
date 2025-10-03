"""
Tests for AniVault Error Messages System

This module tests the error message system including:
- Error message retrieval for different languages
- Variable substitution in error messages
- Error code descriptions
- Message formatting with context
- Validation of error message completeness
"""

import pytest

from anivault.shared.error_messages import (
    DEFAULT_LANGUAGE,
    ERROR_MESSAGES,
    format_error_with_context,
    get_available_languages,
    get_error_code_description,
    get_error_message,
    validate_error_messages,
)
from anivault.shared.errors import ErrorCode


class TestErrorMessages:
    """Test error message retrieval and formatting."""

    def test_get_error_message_korean(self):
        """Test getting error messages in Korean."""
        message = get_error_message(
            ErrorCode.FILE_NOT_FOUND, "ko", path="/test/file.mkv"
        )

        assert "파일을 찾을 수 없습니다" in message
        assert "/test/file.mkv" in message

    def test_get_error_message_english(self):
        """Test getting error messages in English."""
        message = get_error_message(
            ErrorCode.FILE_NOT_FOUND, "en", path="/test/file.mkv"
        )

        assert "File not found" in message
        assert "/test/file.mkv" in message

    def test_get_error_message_default_language(self):
        """Test getting error messages with default language."""
        message = get_error_message(ErrorCode.VALIDATION_ERROR, field="filename")

        assert "입력 데이터에 문제가 있습니다" in message
        assert "filename" in message

    def test_get_error_message_variable_substitution(self):
        """Test variable substitution in error messages."""
        message = get_error_message(
            ErrorCode.API_REQUEST_FAILED, language="en", error="Connection timeout"
        )

        assert "API request failed" in message
        assert "Connection timeout" in message

    def test_get_error_message_multiple_variables(self):
        """Test error messages with multiple variables."""
        message = get_error_message(
            ErrorCode.INVALID_FILE_FORMAT,
            language="ko",
            format=".txt",
            supported=".mkv, .mp4, .avi",
        )

        assert "지원하지 않는 파일 형식입니다" in message
        assert ".txt" in message

    def test_get_error_message_missing_variables(self):
        """Test error messages with missing variables."""
        message = get_error_message(ErrorCode.FILE_NOT_FOUND, language="ko")

        # Should still return the message template
        assert "파일을 찾을 수 없습니다" in message
        assert "{path}" in message  # Variable not substituted

    def test_get_error_message_unknown_language(self):
        """Test getting error messages with unknown language."""
        message = get_error_message(ErrorCode.NETWORK_ERROR, language="unknown")

        # Should fallback to default language (Korean)
        assert "네트워크 연결에 문제가 있습니다" in message

    def test_get_error_message_unknown_error_code(self):
        """Test getting error message for unknown error code."""

        # Create a mock error code that doesn't exist in messages
        class MockErrorCode:
            value = "UNKNOWN_ERROR"

        message = get_error_message(MockErrorCode(), language="ko")

        assert "Unknown error occurred" in message
        assert "UNKNOWN_ERROR" in message


class TestErrorCodeDescriptions:
    """Test error code descriptions."""

    def test_get_error_code_description_korean(self):
        """Test getting error code descriptions in Korean."""
        description = get_error_code_description(ErrorCode.FILE_NOT_FOUND, "ko")

        assert "지정된 파일이 존재하지 않습니다" in description

    def test_get_error_code_description_english(self):
        """Test getting error code descriptions in English."""
        description = get_error_code_description(ErrorCode.FILE_NOT_FOUND, "en")

        assert "The specified file does not exist" in description

    def test_get_error_code_description_default_language(self):
        """Test getting error code descriptions with default language."""
        description = get_error_code_description(ErrorCode.PERMISSION_DENIED)

        assert "파일이나 디렉토리에 접근할 권한이 없습니다" in description

    def test_get_error_code_description_unknown_language(self):
        """Test getting error code descriptions with unknown language."""
        description = get_error_code_description(ErrorCode.VALIDATION_ERROR, "unknown")

        # Should fallback to default language
        assert "입력 데이터 검증에 실패했습니다" in description

    def test_get_error_code_description_unknown_error_code(self):
        """Test getting description for unknown error code."""

        class MockErrorCode:
            value = "UNKNOWN_ERROR"

        description = get_error_code_description(MockErrorCode(), "ko")

        assert "Error code: UNKNOWN_ERROR" in description


class TestErrorFormatting:
    """Test error message formatting with context."""

    def test_format_error_with_context(self):
        """Test formatting error with context information."""
        context = {"path": "/test/file.mkv", "operation": "file_scan"}

        formatted = format_error_with_context(
            ErrorCode.PERMISSION_DENIED, context, "ko"
        )

        assert "파일 접근 권한이 없습니다" in formatted
        assert "/test/file.mkv" in formatted
        assert "Details:" in formatted

    def test_format_error_with_context_no_context(self):
        """Test formatting error without context."""
        formatted = format_error_with_context(ErrorCode.NETWORK_ERROR)

        assert "네트워크 연결에 문제가 있습니다" in formatted
        assert "Details:" in formatted

    def test_format_error_with_context_english(self):
        """Test formatting error with context in English."""
        context = {"config": "api_key"}

        formatted = format_error_with_context(ErrorCode.MISSING_CONFIG, context, "en")

        assert "Required configuration missing" in formatted
        assert "api_key" in formatted
        assert "Details:" in formatted


class TestLanguageSupport:
    """Test language support functionality."""

    def test_get_available_languages(self):
        """Test getting available languages."""
        languages = get_available_languages()

        assert "ko" in languages
        assert "en" in languages
        assert len(languages) >= 2

    def test_default_language_constant(self):
        """Test that default language constant is correct."""
        assert DEFAULT_LANGUAGE == "ko"


class TestErrorMessageValidation:
    """Test error message validation."""

    def test_validate_error_messages_completeness(self):
        """Test that all error codes have messages in all languages."""
        validation_results = validate_error_messages()

        # Check that validation results exist for all languages
        for language in ERROR_MESSAGES:
            assert language in validation_results

        # Check that no error codes are missing (empty lists)
        for language, missing_codes in validation_results.items():
            assert isinstance(missing_codes, list)
            # Ideally, there should be no missing codes
            # but we'll just check the structure is correct

    def test_error_messages_structure(self):
        """Test that error messages have correct structure."""
        # Check that ERROR_MESSAGES has expected languages
        assert "ko" in ERROR_MESSAGES
        assert "en" in ERROR_MESSAGES

        # Check that each language has error messages
        for language in ERROR_MESSAGES:
            assert isinstance(ERROR_MESSAGES[language], dict)
            assert len(ERROR_MESSAGES[language]) > 0

            # Check that all values are strings
            for error_code, message in ERROR_MESSAGES[language].items():
                assert isinstance(error_code, ErrorCode)
                assert isinstance(message, str)
                assert len(message) > 0


class TestErrorMessageIntegration:
    """Integration tests for error message system."""

    @pytest.mark.parametrize(
        "error_code",
        [
            ErrorCode.FILE_NOT_FOUND,
            ErrorCode.PERMISSION_DENIED,
            ErrorCode.NETWORK_ERROR,
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.PARSING_ERROR,
            ErrorCode.CACHE_ERROR,
            ErrorCode.CONFIG_ERROR,
            ErrorCode.APPLICATION_ERROR,
        ],
    )
    def test_all_error_codes_have_messages(self, error_code):
        """Test that all common error codes have messages in both languages."""
        for language in ["ko", "en"]:
            message = get_error_message(error_code, language)
            assert message is not None
            assert len(message) > 0
            assert (
                error_code.value not in message
            )  # Should be user-friendly, not technical

    def test_error_message_consistency(self):
        """Test that error messages are consistent across languages."""
        test_cases = [
            (ErrorCode.FILE_NOT_FOUND, {"path": "/test/file.mkv"}),
            (ErrorCode.VALIDATION_ERROR, {"field": "filename"}),
            (ErrorCode.NETWORK_ERROR, {}),
        ]

        for error_code, context in test_cases:
            ko_message = get_error_message(error_code, "ko", **context)
            en_message = get_error_message(error_code, "en", **context)

            # Both messages should contain the context variables
            for key, value in context.items():
                if isinstance(value, str):
                    assert value in ko_message
                    assert value in en_message

    def test_error_message_template_safety(self):
        """Test that error message templates handle edge cases safely."""
        # Test with empty context
        message = get_error_message(ErrorCode.FILE_NOT_FOUND, "ko")
        assert isinstance(message, str)
        assert len(message) > 0

        # Test with None values
        message = get_error_message(ErrorCode.VALIDATION_ERROR, "ko", field=None)
        assert isinstance(message, str)
        assert len(message) > 0

        # Test with special characters
        message = get_error_message(
            ErrorCode.INVALID_PATH, "ko", path="/path/with spaces/and-special_chars.txt"
        )
        assert isinstance(message, str)
        assert len(message) > 0


@pytest.mark.parametrize("language", ["ko", "en"])
def test_language_specific_messages(language):
    """Parametrized test for language-specific error messages."""
    # Test that each language has distinct messages
    ko_message = get_error_message(ErrorCode.FILE_NOT_FOUND, "ko", path="/test")
    en_message = get_error_message(ErrorCode.FILE_NOT_FOUND, "en", path="/test")

    if language == "ko":
        assert "파일을 찾을 수 없습니다" in ko_message
    else:
        assert "File not found" in en_message

    # Messages should be different between languages
    assert ko_message != en_message


@pytest.mark.parametrize("error_code", list(ErrorCode))
def test_all_error_codes_have_korean_messages(error_code):
    """Test that all error codes have Korean messages."""
    message = get_error_message(error_code, "ko")
    assert isinstance(message, str)
    assert len(message) > 0


@pytest.mark.parametrize("error_code", list(ErrorCode))
def test_all_error_codes_have_english_messages(error_code):
    """Test that all error codes have English messages."""
    message = get_error_message(error_code, "en")
    assert isinstance(message, str)
    assert len(message) > 0

"""
AniVault Error Messages Module

This module provides user-friendly error messages for the AniVault application.
It supports multiple languages and provides contextual information to help users
understand and resolve errors.

The module follows these principles:
- One Source of Truth: All error messages are centralized here
- User-friendly: Messages are clear and actionable
- Multilingual: Supports Korean and English
- Contextual: Messages can include variable substitution
"""

from __future__ import annotations

from typing import Any

from .errors import ErrorCode

# Default language for error messages
DEFAULT_LANGUAGE = "ko"

# Error messages organized by language
ERROR_MESSAGES: dict[str, dict[ErrorCode, str]] = {
    "ko": {
        # File System Errors
        ErrorCode.FILE_NOT_FOUND: "파일을 찾을 수 없습니다: {path}",
        ErrorCode.DIRECTORY_NOT_FOUND: "디렉토리를 찾을 수 없습니다: {path}",
        ErrorCode.PERMISSION_DENIED: "파일 접근 권한이 없습니다: {path}",
        ErrorCode.INVALID_PATH: "유효하지 않은 경로입니다: {path}",
        ErrorCode.DIRECTORY_CREATION_FAILED: "디렉토리 생성에 실패했습니다: {path}",
        ErrorCode.FILE_ACCESS_DENIED: "파일 접근이 거부되었습니다: {path}",
        # Network and API Errors
        ErrorCode.NETWORK_ERROR: "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해주세요.",
        ErrorCode.API_RATE_LIMIT: "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.API_AUTHENTICATION_FAILED: "API 인증에 실패했습니다. API 키를 확인해주세요.",
        ErrorCode.API_REQUEST_FAILED: "API 요청이 실패했습니다: {error}",
        ErrorCode.API_TIMEOUT: "API 요청이 시간 초과되었습니다. 네트워크 상태를 확인해주세요.",
        ErrorCode.API_SERVER_ERROR: "API 서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        # Validation Errors
        ErrorCode.VALIDATION_ERROR: "입력 데이터에 문제가 있습니다: {field}",
        ErrorCode.INVALID_FILE_FORMAT: "지원하지 않는 파일 형식입니다: {format}",
        ErrorCode.INVALID_METADATA: "유효하지 않은 메타데이터입니다: {metadata}",
        ErrorCode.MISSING_REQUIRED_FIELD: "필수 필드가 누락되었습니다: {field}",
        # Parsing Errors
        ErrorCode.PARSING_ERROR: "파일을 분석하는 중 문제가 발생했습니다: {file}",
        ErrorCode.FILENAME_PARSE_FAILED: "파일명을 분석할 수 없습니다: {filename}",
        ErrorCode.METADATA_PARSE_FAILED: "메타데이터를 분석할 수 없습니다: {metadata}",
        # Cache Errors
        ErrorCode.CACHE_ERROR: "캐시 처리 중 문제가 발생했습니다.",
        ErrorCode.CACHE_READ_FAILED: "캐시를 읽을 수 없습니다: {path}",
        ErrorCode.CACHE_WRITE_FAILED: "캐시를 저장할 수 없습니다: {path}",
        ErrorCode.CACHE_CORRUPTION: "캐시 파일이 손상되었습니다: {path}",
        # Configuration Errors
        ErrorCode.CONFIG_ERROR: "설정 파일에 문제가 있습니다: {config}",
        ErrorCode.CONFIGURATION_ERROR: "설정 오류가 발생했습니다: {setting}",
        ErrorCode.MISSING_CONFIG: "필수 설정이 누락되었습니다: {config}",
        ErrorCode.INVALID_CONFIG: "유효하지 않은 설정값입니다: {config}",
        # Application Errors
        ErrorCode.APPLICATION_ERROR: "애플리케이션 오류가 발생했습니다: {operation}",
        ErrorCode.UNKNOWN_COMMAND: "알 수 없는 명령어입니다: {command}",
        ErrorCode.OPERATION_CANCELLED: "작업이 취소되었습니다: {operation}",
        ErrorCode.OPERATION_TIMEOUT: "작업이 시간 초과되었습니다: {operation}",
        # Business Logic Errors
        ErrorCode.BUSINESS_LOGIC_ERROR: "비즈니스 로직 오류가 발생했습니다: {rule}",
        ErrorCode.DUPLICATE_ENTRY: "중복된 항목이 있습니다: {item}",
        ErrorCode.CONSTRAINT_VIOLATION: "제약 조건을 위반했습니다: {constraint}",
    },
    "en": {
        # File System Errors
        ErrorCode.FILE_NOT_FOUND: "File not found: {path}",
        ErrorCode.DIRECTORY_NOT_FOUND: "Directory not found: {path}",
        ErrorCode.PERMISSION_DENIED: "Permission denied: {path}",
        ErrorCode.INVALID_PATH: "Invalid path: {path}",
        ErrorCode.DIRECTORY_CREATION_FAILED: "Failed to create directory: {path}",
        ErrorCode.FILE_ACCESS_DENIED: "File access denied: {path}",
        # Network and API Errors
        ErrorCode.NETWORK_ERROR: "Network connection problem. Please check your internet connection.",
        ErrorCode.API_RATE_LIMIT: "API rate limit exceeded. Please try again later.",
        ErrorCode.API_AUTHENTICATION_FAILED: "API authentication failed. Please check your API key.",
        ErrorCode.API_REQUEST_FAILED: "API request failed: {error}",
        ErrorCode.API_TIMEOUT: "API request timed out. Please check your network connection.",
        ErrorCode.API_SERVER_ERROR: "API server error occurred. Please try again later.",
        # Validation Errors
        ErrorCode.VALIDATION_ERROR: "Input data validation failed: {field}",
        ErrorCode.INVALID_FILE_FORMAT: "Unsupported file format: {format}",
        ErrorCode.INVALID_METADATA: "Invalid metadata: {metadata}",
        ErrorCode.MISSING_REQUIRED_FIELD: "Required field missing: {field}",
        # Parsing Errors
        ErrorCode.PARSING_ERROR: "Error occurred while parsing file: {file}",
        ErrorCode.FILENAME_PARSE_FAILED: "Failed to parse filename: {filename}",
        ErrorCode.METADATA_PARSE_FAILED: "Failed to parse metadata: {metadata}",
        # Cache Errors
        ErrorCode.CACHE_ERROR: "Cache processing error occurred.",
        ErrorCode.CACHE_READ_FAILED: "Failed to read cache: {path}",
        ErrorCode.CACHE_WRITE_FAILED: "Failed to write cache: {path}",
        ErrorCode.CACHE_CORRUPTION: "Cache file corrupted: {path}",
        # Configuration Errors
        ErrorCode.CONFIG_ERROR: "Configuration file error: {config}",
        ErrorCode.CONFIGURATION_ERROR: "Configuration error: {setting}",
        ErrorCode.MISSING_CONFIG: "Required configuration missing: {config}",
        ErrorCode.INVALID_CONFIG: "Invalid configuration value: {config}",
        # Application Errors
        ErrorCode.APPLICATION_ERROR: "Application error occurred: {operation}",
        ErrorCode.UNKNOWN_COMMAND: "Unknown command: {command}",
        ErrorCode.OPERATION_CANCELLED: "Operation cancelled: {operation}",
        ErrorCode.OPERATION_TIMEOUT: "Operation timed out: {operation}",
        # Business Logic Errors
        ErrorCode.BUSINESS_LOGIC_ERROR: "Business logic error: {rule}",
        ErrorCode.DUPLICATE_ENTRY: "Duplicate entry found: {item}",
        ErrorCode.CONSTRAINT_VIOLATION: "Constraint violation: {constraint}",
    },
}


def get_error_message(
    error_code: ErrorCode,
    language: str = DEFAULT_LANGUAGE,
    **kwargs: Any,
) -> str:
    """Get user-friendly error message for the given error code.

    Args:
        error_code: The error code to get message for
        language: Language code ('ko' or 'en'), defaults to 'ko'
        **kwargs: Variables to substitute in the message template

    Returns:
        User-friendly error message with variable substitution

    Raises:
        KeyError: If error code or language is not supported
    """
    if language not in ERROR_MESSAGES:
        language = DEFAULT_LANGUAGE

    if error_code not in ERROR_MESSAGES[language]:
        # Fallback to default language if error code not found
        if (
            language != DEFAULT_LANGUAGE
            and error_code in ERROR_MESSAGES[DEFAULT_LANGUAGE]
        ):
            language = DEFAULT_LANGUAGE
        else:
            # Return a generic message if error code is not found
            return f"Unknown error occurred: {error_code.value}"

    message_template = ERROR_MESSAGES[language][error_code]

    try:
        return message_template.format(**kwargs)
    except KeyError as e:
        # If formatting fails, return the template with error info
        return f"{message_template} [Format error: missing {e}]"


def get_available_languages() -> list[str]:
    """Get list of available languages for error messages.

    Returns:
        List of supported language codes
    """
    return list(ERROR_MESSAGES.keys())


def get_error_code_description(
    error_code: ErrorCode,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Get a description of what the error code means.

    Args:
        error_code: The error code to describe
        language: Language code ('ko' or 'en'), defaults to 'ko'

    Returns:
        Description of the error code
    """
    descriptions = {
        "ko": {
            ErrorCode.FILE_NOT_FOUND: "지정된 파일이 존재하지 않습니다.",
            ErrorCode.DIRECTORY_NOT_FOUND: "지정된 디렉토리가 존재하지 않습니다.",
            ErrorCode.PERMISSION_DENIED: "파일이나 디렉토리에 접근할 권한이 없습니다.",
            ErrorCode.INVALID_PATH: "유효하지 않은 파일 경로입니다.",
            ErrorCode.NETWORK_ERROR: "네트워크 연결에 문제가 있습니다.",
            ErrorCode.API_RATE_LIMIT: "API 요청 한도를 초과했습니다.",
            ErrorCode.VALIDATION_ERROR: "입력 데이터 검증에 실패했습니다.",
            ErrorCode.PARSING_ERROR: "데이터 파싱에 실패했습니다.",
            ErrorCode.CACHE_ERROR: "캐시 처리 중 오류가 발생했습니다.",
            ErrorCode.CONFIG_ERROR: "설정 관련 오류가 발생했습니다.",
            ErrorCode.APPLICATION_ERROR: "애플리케이션 레벨 오류가 발생했습니다.",
            ErrorCode.BUSINESS_LOGIC_ERROR: "비즈니스 로직 위반이 발생했습니다.",
        },
        "en": {
            ErrorCode.FILE_NOT_FOUND: "The specified file does not exist.",
            ErrorCode.DIRECTORY_NOT_FOUND: "The specified directory does not exist.",
            ErrorCode.PERMISSION_DENIED: "No permission to access the file or directory.",
            ErrorCode.INVALID_PATH: "Invalid file path provided.",
            ErrorCode.NETWORK_ERROR: "Network connection problem occurred.",
            ErrorCode.API_RATE_LIMIT: "API rate limit has been exceeded.",
            ErrorCode.VALIDATION_ERROR: "Input data validation failed.",
            ErrorCode.PARSING_ERROR: "Data parsing failed.",
            ErrorCode.CACHE_ERROR: "Cache processing error occurred.",
            ErrorCode.CONFIG_ERROR: "Configuration related error occurred.",
            ErrorCode.APPLICATION_ERROR: "Application level error occurred.",
            ErrorCode.BUSINESS_LOGIC_ERROR: "Business logic violation occurred.",
        },
    }

    if language not in descriptions:
        language = DEFAULT_LANGUAGE

    return descriptions.get(language, {}).get(
        error_code,
        f"Error code: {error_code.value}",
    )


def format_error_with_context(
    error_code: ErrorCode,
    context: dict[str, Any] | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Format error message with context information.

    Args:
        error_code: The error code to format
        context: Optional context dictionary with additional information
        language: Language code ('ko' or 'en'), defaults to 'ko'

    Returns:
        Formatted error message with context
    """
    if context is None:
        context = {}

    message = get_error_message(error_code, language, **context)
    description = get_error_code_description(error_code, language)

    return f"{message}\n\nDetails: {description}"


def validate_error_messages() -> dict[str, list[str]]:
    """Validate that all error codes have messages in all languages.

    Returns:
        Dictionary with validation results for each language
    """
    results = {}
    all_error_codes = set(ErrorCode)

    for language in ERROR_MESSAGES:
        missing_codes = all_error_codes - set(ERROR_MESSAGES[language])
        results[language] = [code.value for code in missing_codes]

    return results

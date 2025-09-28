"""Extension filtering module for AniVault.

This module provides configuration-driven file extension filtering functionality
for processing only relevant media files during directory scanning.
"""

from pathlib import Path
from typing import Callable, Optional

from anivault.core.config import APP_CONFIG
from anivault.core.logging import get_logger

logger = get_logger(__name__)


def create_media_extension_filter(
    extensions: Optional[list[str]] = None,
    case_sensitive: bool = False,
) -> Callable[[str], bool]:
    """Create a media file extension filter function.

    This function creates a filter that checks if a file path has one of the
    specified media extensions. The filter is optimized for performance and
    can handle both case-sensitive and case-insensitive matching.

    Args:
        extensions: List of file extensions to filter for. If None, uses
            APP_CONFIG.media_extensions. Extensions should include the dot
            (e.g., ['.mkv', '.mp4', '.avi']).
        case_sensitive: Whether to perform case-sensitive matching.

    Returns:
        A filter function that takes a file path and returns True if the file
        has a whitelisted extension.

    Example:
        >>> filter_func = create_media_extension_filter()
        >>> filter_func('/path/to/movie.mkv')  # True
        >>> filter_func('/path/to/document.txt')  # False

        >>> custom_filter = create_media_extension_filter(['.mp4', '.avi'])
        >>> custom_filter('/path/to/video.mp4')  # True
        >>> custom_filter('/path/to/movie.mkv')  # False
    """
    if extensions is None:
        extensions = APP_CONFIG.media_extensions

    if not extensions:
        logger.warning("No media extensions provided, filter will reject all files")
        return lambda _: False

    # Normalize extensions
    if case_sensitive:
        ext_set = set(extensions)
    else:
        ext_set = set(ext.lower() for ext in extensions)

    logger.info(
        f"Created extension filter with {len(extensions)} extensions: {extensions}, "
        f"case_sensitive={case_sensitive}",
    )

    def filter_func(file_path: str) -> bool:
        """Filter function that checks file extension.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file has a whitelisted extension, False otherwise.
        """
        try:
            file_path_obj = Path(file_path)
            extension = file_path_obj.suffix

            if not extension:
                return False

            if case_sensitive:
                return extension in ext_set
            return extension.lower() in ext_set

        except Exception as e:
            logger.warning(f"Error checking extension for {file_path}: {e}")
            return False

    return filter_func


def create_custom_extension_filter(
    extensions: list[str],
    case_sensitive: bool = False,
    include_patterns: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
) -> Callable[[str], bool]:
    """Create a custom extension filter with additional pattern matching.

    This function creates a more sophisticated filter that can handle both
    extension matching and pattern-based inclusion/exclusion rules.

    Args:
        extensions: List of file extensions to filter for (must include dots).
        case_sensitive: Whether to perform case-sensitive matching.
        include_patterns: Optional list of glob patterns for additional inclusion.
            Files matching these patterns will be included even if they don't
            have the specified extensions.
        exclude_patterns: Optional list of glob patterns for exclusion.
            Files matching these patterns will be excluded even if they have
            the specified extensions.

    Returns:
        A filter function that takes a file path and returns True if the file
        should be processed.

    Example:
        >>> filter_func = create_custom_extension_filter(
        ...     extensions=['.mkv', '.mp4'],
        ...     include_patterns=['*.sample.mkv'],
        ...     exclude_patterns=['*.tmp']
        ... )
    """
    # Start with basic extension filter
    base_filter = create_media_extension_filter(extensions, case_sensitive)

    # Import fnmatch for pattern matching
    import fnmatch

    def filter_func(file_path: str) -> bool:
        """Advanced filter function with pattern matching.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file should be processed, False otherwise.
        """
        file_path_obj = Path(file_path)
        filename = file_path_obj.name

        # Check exclusion patterns first
        if exclude_patterns:
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(filename, pattern):
                    logger.debug(f"Excluded {file_path} by pattern {pattern}")
                    return False

        # Check inclusion patterns
        if include_patterns:
            for pattern in include_patterns:
                if fnmatch.fnmatch(filename, pattern):
                    logger.debug(f"Included {file_path} by pattern {pattern}")
                    return True

        # Fall back to extension filter
        return base_filter(file_path)

    return filter_func


def get_default_media_filter() -> Callable[[str], bool]:
    """Get the default media file filter using application configuration.

    This is a convenience function that creates a filter using the default
    media extensions from the application configuration.

    Returns:
        A filter function configured with APP_CONFIG.media_extensions.
    """
    return create_media_extension_filter()


def validate_extension_filter(
    filter_func: Callable[[str], bool],
    test_files: list[str],
) -> dict[str, bool]:
    """Validate an extension filter function with test files.

    This function is useful for testing and debugging extension filters.

    Args:
        filter_func: The filter function to test.
        test_files: List of file paths to test.

    Returns:
        Dictionary mapping file paths to their filter results.
    """
    results = {}
    for file_path in test_files:
        try:
            results[file_path] = filter_func(file_path)
        except Exception as e:
            logger.error(f"Error testing filter with {file_path}: {e}")
            results[file_path] = False

    return results


# Convenience function for common use cases
def is_media_file(file_path: str) -> bool:
    """Check if a file is a media file using the default configuration.

    This is a simple convenience function for quick media file checks.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file is a media file, False otherwise.
    """
    filter_func = get_default_media_filter()
    return filter_func(file_path)

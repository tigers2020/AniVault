"""File naming and conflict resolution system.

This module provides functionality to handle filename conflicts and generate
safe, unique filenames while preserving the original base name.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .exceptions import FileNamingError


class NamingStrategy(Enum):
    """Strategies for handling filename conflicts."""

    SUFFIX_NUMERIC = "suffix_numeric"  # _001, _002, etc.
    SUFFIX_TIMESTAMP = "suffix_timestamp"  # _20240127_143022
    SUFFIX_HASH = "suffix_hash"  # _a1b2c3d4
    PARENTHESES = "parentheses"  # (1), (2), etc.


@dataclass
class NamingResult:
    """Result of a file naming operation."""

    original_name: str
    new_name: str
    strategy_used: NamingStrategy
    conflict_resolved: bool
    reason: str


class FileNamer:
    """Handles file naming and conflict resolution.

    This class provides methods to:
    - Generate safe filenames
    - Resolve naming conflicts
    - Preserve original base names
    - Handle various file naming scenarios
    """

    # Maximum filename length (Windows limit is 255, but we use 200 for safety)
    MAX_FILENAME_LENGTH = 200

    # Characters that are not allowed in filenames on Windows
    INVALID_CHARS = r'[<>:"/\\|?*]'

    # Reserved names on Windows
    RESERVED_NAMES = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    def __init__(self, strategy: NamingStrategy = NamingStrategy.SUFFIX_NUMERIC) -> None:
        """Initialize the file namer.

        Args:
            strategy: Default strategy for handling conflicts
        """
        self.strategy = strategy
        self._invalid_chars_pattern = re.compile(self.INVALID_CHARS)

    def generate_safe_filename(self, filename: str) -> str:
        """Generate a safe filename by removing or replacing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Safe filename with invalid characters replaced

        Raises:
            FileNamingError: If filename cannot be made safe
        """
        if not filename or not filename.strip():
            raise FileNamingError(
                "Empty filename provided", filename, "", "Filename cannot be empty"
            )

        # Remove leading/trailing whitespace and dots
        safe_name = filename.strip().rstrip(".")

        if not safe_name:
            raise FileNamingError(
                "Filename becomes empty after cleaning",
                filename,
                "",
                "Filename contains only whitespace and dots",
            )

        # Replace invalid characters with underscores
        safe_name = self._invalid_chars_pattern.sub("_", safe_name)

        # Remove multiple consecutive underscores
        safe_name = re.sub(r"_+", "_", safe_name)

        # Remove leading/trailing underscores
        safe_name = safe_name.strip("_")

        # Check for reserved names
        name_without_ext = Path(safe_name).stem.upper()
        if name_without_ext in self.RESERVED_NAMES:
            safe_name = f"_{safe_name}"

        # Ensure filename is not too long
        if len(safe_name) > self.MAX_FILENAME_LENGTH:
            name_part, ext_part = self._split_filename(safe_name)
            max_name_length = self.MAX_FILENAME_LENGTH - len(ext_part) - 1
            safe_name = name_part[:max_name_length] + ext_part

        if not safe_name:
            raise FileNamingError(
                "Filename becomes empty after processing",
                filename,
                safe_name,
                "All characters were invalid",
            )

        return safe_name

    def resolve_conflict(
        self, target_path: Path, strategy: NamingStrategy | None = None
    ) -> NamingResult:
        """Resolve a filename conflict by generating a unique name.

        Args:
            target_path: The target path where conflict occurs
            strategy: Strategy to use (uses default if None)

        Returns:
            NamingResult with the new filename

        Raises:
            FileNamingError: If conflict cannot be resolved
        """
        if not target_path.exists():
            return NamingResult(
                original_name=target_path.name,
                new_name=target_path.name,
                strategy_used=NamingStrategy.SUFFIX_NUMERIC,
                conflict_resolved=False,
                reason="No conflict - file does not exist",
            )

        strategy = strategy or self.strategy
        original_name = target_path.name
        base_name, extension = self._split_filename(original_name)

        try:
            if strategy == NamingStrategy.SUFFIX_NUMERIC:
                new_name = self._resolve_with_numeric_suffix(target_path, base_name, extension)
            elif strategy == NamingStrategy.SUFFIX_TIMESTAMP:
                new_name = self._resolve_with_timestamp_suffix(target_path, base_name, extension)
            elif strategy == NamingStrategy.SUFFIX_HASH:
                new_name = self._resolve_with_hash_suffix(target_path, base_name, extension)
            elif strategy == NamingStrategy.PARENTHESES:
                new_name = self._resolve_with_parentheses(target_path, base_name, extension)
            else:
                raise FileNamingError(
                    f"Unknown naming strategy: {strategy}",
                    original_name,
                    "",
                    f"Strategy {strategy} is not supported",
                )

            return NamingResult(
                original_name=original_name,
                new_name=new_name,
                strategy_used=strategy,
                conflict_resolved=True,
                reason=f"Conflict resolved using {strategy.value} strategy",
            )

        except Exception as e:
            raise FileNamingError(
                f"Failed to resolve filename conflict: {e!s}", original_name, "", str(e)
            ) from e

    def get_available_filename(
        self, target_path: Path, strategy: NamingStrategy | None = None
    ) -> Path:
        """Get an available filename for the target path.

        Args:
            target_path: The target path
            strategy: Strategy to use for conflict resolution

        Returns:
            Path with an available filename
        """
        if not target_path.exists():
            return target_path

        result = self.resolve_conflict(target_path, strategy)
        return target_path.parent / result.new_name

    def _split_filename(self, filename: str) -> tuple[str, str]:
        """Split filename into name and extension parts.

        Args:
            filename: The filename to split

        Returns:
            Tuple of (name_part, extension_part)
        """
        path = Path(filename)
        if path.suffix:
            return str(path.with_suffix("")), path.suffix
        return filename, ""

    def _resolve_with_numeric_suffix(
        self, target_path: Path, base_name: str, extension: str
    ) -> str:
        """Resolve conflict using numeric suffix (_001, _002, etc.)."""
        counter = 1
        while True:
            suffix = f"_{counter:03d}"
            new_name = f"{base_name}{suffix}{extension}"
            new_path = target_path.parent / new_name

            if not new_path.exists():
                return new_name

            counter += 1

            # Prevent infinite loop
            if counter > 9999:
                raise FileNamingError(
                    "Too many numeric suffixes generated",
                    target_path.name,
                    new_name,
                    "Maximum numeric suffix limit reached",
                )

    def _resolve_with_timestamp_suffix(
        self, target_path: Path, base_name: str, extension: str
    ) -> str:
        """Resolve conflict using timestamp suffix."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{timestamp}"
        new_name = f"{base_name}{suffix}{extension}"

        # If timestamp collision, add microseconds
        new_path = target_path.parent / new_name
        if new_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            suffix = f"_{timestamp}"
            new_name = f"{base_name}{suffix}{extension}"

        return new_name

    def _resolve_with_hash_suffix(self, target_path: Path, base_name: str, extension: str) -> str:
        """Resolve conflict using hash suffix."""
        import hashlib
        import time

        # Use current time and path for hash generation
        hash_input = f"{target_path}{time.time()}".encode()
        hash_value = hashlib.md5(hash_input).hexdigest()[:8]
        suffix = f"_{hash_value}"
        new_name = f"{base_name}{suffix}{extension}"

        return new_name

    def _resolve_with_parentheses(self, target_path: Path, base_name: str, extension: str) -> str:
        """Resolve conflict using parentheses (1), (2), etc."""
        counter = 1
        while True:
            suffix = f"({counter})"
            new_name = f"{base_name}{suffix}{extension}"
            new_path = target_path.parent / new_name

            if not new_path.exists():
                return new_name

            counter += 1

            # Prevent infinite loop
            if counter > 9999:
                raise FileNamingError(
                    "Too many parentheses suffixes generated",
                    target_path.name,
                    new_name,
                    "Maximum parentheses suffix limit reached",
                )

    def validate_filename(self, filename: str) -> bool:
        """Validate if a filename is safe to use.

        Args:
            filename: The filename to validate

        Returns:
            True if filename is valid, False otherwise
        """
        try:
            safe_name = self.generate_safe_filename(filename)
            return safe_name == filename
        except FileNamingError:
            return False

    def get_filename_suggestions(self, original_filename: str, count: int = 5) -> list[str]:
        """Get filename suggestions for conflict resolution.

        Args:
            original_filename: The original filename
            count: Number of suggestions to generate

        Returns:
            List of suggested filenames
        """
        suggestions = []
        base_name, extension = self._split_filename(original_filename)

        # Generate suggestions using different strategies
        strategies = [
            NamingStrategy.SUFFIX_NUMERIC,
            NamingStrategy.SUFFIX_TIMESTAMP,
            NamingStrategy.SUFFIX_HASH,
            NamingStrategy.PARENTHESES,
        ]

        for i, strategy in enumerate(strategies[:count]):
            try:
                if strategy == NamingStrategy.SUFFIX_NUMERIC:
                    suffix = f"_{i+1:03d}"
                elif strategy == NamingStrategy.SUFFIX_TIMESTAMP:
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    suffix = f"_{timestamp}"
                elif strategy == NamingStrategy.SUFFIX_HASH:
                    import hashlib

                    hash_input = f"{original_filename}{i}".encode()
                    hash_value = hashlib.md5(hash_input).hexdigest()[:8]
                    suffix = f"_{hash_value}"
                elif strategy == NamingStrategy.PARENTHESES:
                    suffix = f"({i+1})"

                suggestion = f"{base_name}{suffix}{extension}"
                suggestions.append(suggestion)

            except Exception:
                continue

        return suggestions[:count]

"""File I/O utilities with UTF-8 encoding enforcement.

This module provides utilities for safe file operations that enforce
UTF-8 encoding for text files while allowing binary operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, TextIO


@contextmanager
def safe_open(
    file: str | Path | int,
    mode: str = "r",
    buffering: int = -1,
    encoding: str = "utf-8",
    errors: str = "strict",
    newline: str | None = None,
    *,
    closefd: bool = True,  # noqa: ARG001
    opener: Any | None = None,  # noqa: ARG001
) -> Generator[TextIO | BinaryIO, None, None]:
    """Context manager for safe file operations with UTF-8 encoding.

    This function wraps the built-in open() function and enforces UTF-8
    encoding for text modes while allowing binary modes to pass through
    unchanged.

    Args:
        file: File path, file descriptor, or Path object.
        mode: File mode ('r', 'w', 'a', 'r+', 'rb', 'wb', etc.).
        buffering: Buffer size for I/O operations.
        encoding: Text encoding. Defaults to 'utf-8' for text modes.
        errors: How to handle encoding errors.
        newline: Line ending handling.
        closefd: Whether to close file descriptor.
        opener: Custom opener function.

    Yields:
        File object (TextIO or BinaryIO).

    Raises:
        UnicodeError: If encoding/decoding fails.
        OSError: If file operations fail.
    """
    # Determine if this is a text or binary mode
    is_text_mode = any(mode.startswith(prefix) for prefix in ["r", "w", "a", "x"])
    is_binary_mode = "b" in mode

    # For text modes, enforce UTF-8 encoding
    if is_text_mode and not is_binary_mode:
        # Override encoding to UTF-8 for text modes
        file_obj = Path(file).open(  # noqa: SIM115
            mode=mode,
            buffering=buffering,
            encoding="utf-8",  # Force UTF-8
            errors=errors,
            newline=newline,
        )
    else:
        # For binary modes, use the original parameters
        file_obj = Path(file).open(  # noqa: SIM115
            mode=mode,
            buffering=buffering,
            encoding=encoding if not is_binary_mode else None,
            errors=errors if not is_binary_mode else None,
            newline=newline if not is_binary_mode else None,
        )

    try:
        yield file_obj
    finally:
        file_obj.close()


def ensure_utf8_path(path: str | Path) -> Path:
    """Ensure a path is properly encoded for UTF-8.

    Args:
        path: Path to normalize.

    Returns:
        Path object with proper UTF-8 encoding.

    Raises:
        UnicodeError: If the path contains invalid UTF-8 characters.
    """
    if isinstance(path, str):
        # Validate that the string is valid UTF-8
        path.encode("utf-8")
        return Path(path)
    if isinstance(path, Path):
        # Path objects should already be properly encoded
        return path
    msg = f"Expected str or Path, got {type(path)}"
    raise TypeError(msg)


def safe_write_text(
    path: str | Path,
    content: str,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> None:
    """Safely write text content to a file with UTF-8 encoding.

    Args:
        path: File path to write to.
        content: Text content to write.
        encoding: Text encoding. Defaults to 'utf-8'.
        errors: How to handle encoding errors.

    Raises:
        UnicodeError: If encoding fails.
        OSError: If file operations fail.
    """
    path = ensure_utf8_path(path)
    with safe_open(path, "w", encoding=encoding, errors=errors) as f:
        f.write(content)


def safe_read_text(
    path: str | Path,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str:
    """Safely read text content from a file with UTF-8 encoding.

    Args:
        path: File path to read from.
        encoding: Text encoding. Defaults to 'utf-8'.
        errors: How to handle encoding errors.

    Returns:
        Text content from the file.

    Raises:
        UnicodeError: If decoding fails.
        OSError: If file operations fail.
    """
    path = ensure_utf8_path(path)
    with safe_open(path, "r", encoding=encoding, errors=errors) as f:
        return f.read()

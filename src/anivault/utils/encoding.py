"""
UTF-8 Encoding Configuration Module

This module provides utilities for enforcing UTF-8 encoding throughout the AniVault application.
It ensures consistent handling of Unicode characters, especially important for anime titles
that may contain Japanese, Korean, or other non-ASCII characters.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any, BinaryIO, TextIO

import chardet

# Constants for encoding
UTF8_ENCODING = "utf-8"
UTF8_BOM = "\ufeff"


def setup_utf8_environment() -> None:
    """
    Set up the environment for UTF-8 encoding.

    This function configures the Python environment to use UTF-8 encoding
    by default for all file operations and string handling.
    """
    # Set PYTHONUTF8 environment variable if not already set
    if "PYTHONUTF8" not in os.environ:
        os.environ["PYTHONUTF8"] = "1"

    # Set default encoding for stdout/stderr if they're not already UTF-8
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding != UTF8_ENCODING:
        try:
            # Reconfigure stdout/stderr with UTF-8 encoding
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding=UTF8_ENCODING)
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding=UTF8_ENCODING)
        except (AttributeError, UnicodeError):
            # Fallback: create new text wrappers with UTF-8 encoding

            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding=UTF8_ENCODING,
                errors="replace",
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding=UTF8_ENCODING,
                errors="replace",
            )


def open_utf8(
    file_path: str | Path,
    mode: str = "r",
    encoding: str = UTF8_ENCODING,
    **kwargs: Any,
) -> TextIO | BinaryIO:
    """
    Open a file with UTF-8 encoding by default.

    Args:
        file_path: Path to the file to open
        mode: File open mode ('r', 'w', 'a', etc.)
        encoding: Text encoding to use (defaults to UTF-8)
        **kwargs: Additional arguments to pass to open()

    Returns:
        File handle opened with the specified encoding

    Raises:
        UnicodeDecodeError: If the file contains invalid UTF-8 sequences
        and errors='strict' is used
    """
    # Ensure encoding is specified for text modes
    if "b" not in mode and "encoding" not in kwargs:
        kwargs["encoding"] = encoding

    # Set default error handling for UTF-8 (only for text modes)
    if "b" not in mode and "errors" not in kwargs:
        kwargs["errors"] = "replace"

    return Path(file_path).open(mode, **kwargs)


def read_text_file(file_path: str | Path, encoding: str = UTF8_ENCODING) -> str:
    """
    Read a text file with UTF-8 encoding.

    Args:
        file_path: Path to the file to read
        encoding: Text encoding to use (defaults to UTF-8)

    Returns:
        Contents of the file as a string

    Raises:
        UnicodeDecodeError: If the file contains invalid UTF-8 sequences
    """
    with open_utf8(file_path, "r", encoding=encoding) as f:
        return f.read()


def write_text_file(
    file_path: str | Path,
    content: str,
    encoding: str = UTF8_ENCODING,
    *,
    ensure_utf8_bom: bool = False,
) -> None:
    """
    Write text content to a file with UTF-8 encoding.

    Args:
        file_path: Path to the file to write
        content: Text content to write
        encoding: Text encoding to use (defaults to UTF-8)
        ensure_utf8_bom: Whether to add UTF-8 BOM at the beginning
    """
    if ensure_utf8_bom and not content.startswith(UTF8_BOM):
        content = UTF8_BOM + content

    with open_utf8(file_path, "w", encoding=encoding) as f:
        f.write(content)


def ensure_utf8_string(text: str | bytes, encoding: str = UTF8_ENCODING) -> str:
    """
    Ensure a string or bytes object is properly decoded as UTF-8.

    Args:
        text: String or bytes to convert to UTF-8 string
        encoding: Encoding to use for decoding bytes (defaults to UTF-8)

    Returns:
        UTF-8 encoded string

    Raises:
        UnicodeDecodeError: If bytes cannot be decoded with the specified encoding
    """
    if isinstance(text, bytes):
        return text.decode(encoding)
    if isinstance(text, str):
        # Ensure the string is properly encoded
        return text.encode(encoding).decode(encoding)
    msg = f"Expected str or bytes, got {type(text)}"
    raise TypeError(msg)


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename that works across different filesystems.

    Args:
        filename: Original filename
        max_length: Maximum length for the filename

    Returns:
        Safe filename with invalid characters replaced
    """
    # Characters that are problematic in filenames
    invalid_chars = '<>:"/\\|?*'

    # Replace invalid characters
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    filename = filename.strip(" .")

    # Check if filename is empty or only underscores after cleaning
    if not filename or filename.replace("_", "") == "":
        return "unnamed"

    # Truncate if too long
    if len(filename) > max_length:
        path_obj = Path(filename)
        name = path_obj.stem
        ext = path_obj.suffix
        filename = name[: max_length - len(ext)] + ext

    return filename


def get_file_encoding(file_path: str | Path) -> str:
    """
    Detect the encoding of a text file.

    Args:
        file_path: Path to the file to analyze

    Returns:
        Detected encoding name
    """
    try:
        with Path(file_path).open("rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result.get("encoding", UTF8_ENCODING)
    except ImportError:
        # Fallback to UTF-8 if chardet is not available
        return UTF8_ENCODING
    except Exception:
        return UTF8_ENCODING


# Initialize UTF-8 environment when module is imported
setup_utf8_environment()

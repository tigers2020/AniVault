"""Tests for file I/O utilities with UTF-8 encoding."""

from pathlib import Path
from typing import List

import pytest

from anivault.utils.files import (
    ensure_utf8_path,
    safe_open,
    safe_read_text,
    safe_write_text,
)


class TestSafeOpen:
    """Test safe_open context manager."""

    def test_safe_open_text_mode(self, tmp_path):
        """Test safe_open with text mode enforces UTF-8 encoding."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, 世界! 🌍"

        # Write with safe_open
        with safe_open(test_file, "w") as f:
            f.write(test_content)

        # Read back and verify
        with safe_open(test_file, "r") as f:
            content = f.read()

        assert content == test_content

    def test_safe_open_binary_mode(self, tmp_path):
        """Test safe_open with binary mode passes through unchanged."""
        test_file = tmp_path / "test.bin"
        test_data = b"Binary data \x00\x01\x02"

        # Write with safe_open in binary mode
        with safe_open(test_file, "wb") as f:
            f.write(test_data)

        # Read back and verify
        with safe_open(test_file, "rb") as f:
            data = f.read()

        assert data == test_data

    def test_safe_open_append_mode(self, tmp_path):
        """Test safe_open with append mode."""
        test_file = tmp_path / "append_test.txt"
        initial_content = "Initial content\n"
        appended_content = "Appended content\n"

        # Write initial content
        with safe_open(test_file, "w") as f:
            f.write(initial_content)

        # Append content
        with safe_open(test_file, "a") as f:
            f.write(appended_content)

        # Read and verify
        with safe_open(test_file, "r") as f:
            content = f.read()

        assert content == initial_content + appended_content

    def test_safe_open_utf8_encoding_error(self, tmp_path):
        """Test safe_open handles encoding errors correctly."""
        test_file = tmp_path / "encoding_test.txt"

        # This should work with UTF-8
        with safe_open(test_file, "w", encoding="utf-8") as f:
            f.write("Valid UTF-8: こんにちは")

        # This should raise an error with strict encoding
        with pytest.raises(UnicodeError):
            with safe_open(test_file, "w", encoding="ascii", errors="strict") as f:
                f.write("Invalid ASCII: こんにちは")

    def test_safe_open_with_errors_ignore(self, tmp_path):
        """Test safe_open with errors='ignore'."""
        test_file = tmp_path / "ignore_test.txt"

        # This should work with errors='ignore'
        with safe_open(test_file, "w", encoding="ascii", errors="ignore") as f:
            f.write("Mixed: Hello こんにちは World")

        # Read back (some characters will be missing)
        with safe_open(test_file, "r", encoding="ascii", errors="ignore") as f:
            content = f.read()

        assert "Hello" in content
        assert "World" in content


class TestEnsureUtf8Path:
    """Test ensure_utf8_path function."""

    def test_ensure_utf8_path_with_string(self):
        """Test ensure_utf8_path with string input."""
        path_str = "test/path/ファイル.txt"
        result = ensure_utf8_path(path_str)

        assert isinstance(result, Path)
        assert str(result) == path_str

    def test_ensure_utf8_path_with_path(self):
        """Test ensure_utf8_path with Path input."""
        path_obj = Path("test/path/ファイル.txt")
        result = ensure_utf8_path(path_obj)

        assert isinstance(result, Path)
        assert result == path_obj

    def test_ensure_utf8_path_invalid_type(self):
        """Test ensure_utf8_path with invalid type."""
        with pytest.raises(TypeError):
            ensure_utf8_path(123)  # type: ignore

    def test_ensure_utf8_path_invalid_utf8(self):
        """Test ensure_utf8_path with invalid UTF-8 string."""
        # This should raise UnicodeError
        with pytest.raises(UnicodeError):
            ensure_utf8_path("Invalid: \xff\xfe")  # Invalid UTF-8 sequence


class TestSafeWriteText:
    """Test safe_write_text function."""

    def test_safe_write_text_basic(self, tmp_path):
        """Test basic safe_write_text functionality."""
        test_file = tmp_path / "write_test.txt"
        content = "Hello, 世界! 🌍"

        safe_write_text(test_file, content)

        assert test_file.exists()
        with open(test_file, encoding="utf-8") as f:
            assert f.read() == content

    def test_safe_write_text_with_custom_encoding(self, tmp_path):
        """Test safe_write_text with custom encoding."""
        test_file = tmp_path / "encoding_test.txt"
        content = "Hello, 世界!"

        safe_write_text(test_file, content, encoding="utf-8")

        assert test_file.exists()
        with open(test_file, encoding="utf-8") as f:
            assert f.read() == content

    def test_safe_write_text_multilingual(self, tmp_path):
        """Test safe_write_text with multilingual content."""
        test_file = tmp_path / "multilingual_test.txt"
        content = """
        English: Hello World
        日本語: こんにちは世界
        한국어: 안녕하세요 세계
        Русский: Привет мир
        العربية: مرحبا بالعالم
        עברית: שלום עולם
        """

        safe_write_text(test_file, content)

        assert test_file.exists()
        with open(test_file, encoding="utf-8") as f:
            assert f.read() == content


class TestSafeReadText:
    """Test safe_read_text function."""

    def test_safe_read_text_basic(self, tmp_path):
        """Test basic safe_read_text functionality."""
        test_file = tmp_path / "read_test.txt"
        content = "Hello, 世界! 🌍"

        # Write content first
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Read with safe_read_text
        result = safe_read_text(test_file)
        assert result == content

    def test_safe_read_text_multilingual(self, tmp_path):
        """Test safe_read_text with multilingual content."""
        test_file = tmp_path / "multilingual_read_test.txt"
        content = """
        English: Hello World
        日本語: こんにちは世界
        한국어: 안녕하세요 세계
        """

        # Write content first
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Read with safe_read_text
        result = safe_read_text(test_file)
        assert result == content

    def test_safe_read_text_nonexistent_file(self, tmp_path):
        """Test safe_read_text with nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            safe_read_text(test_file)

    def test_safe_read_text_with_custom_encoding(self, tmp_path):
        """Test safe_read_text with custom encoding."""
        test_file = tmp_path / "custom_encoding_test.txt"
        content = "Hello, 世界!"

        # Write with UTF-8
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Read with custom encoding
        result = safe_read_text(test_file, encoding="utf-8")
        assert result == content


class TestUtf8Integration:
    """Integration tests for UTF-8 file operations."""

    def test_roundtrip_utf8_content(self, tmp_path):
        """Test complete roundtrip of UTF-8 content."""
        test_file = tmp_path / "roundtrip_test.txt"
        original_content = """
        This is a comprehensive test of UTF-8 handling:

        ASCII: Hello World!
        Latin: Café, naïve, résumé
        Japanese: こんにちは世界
        Korean: 안녕하세요 세계
        Chinese: 你好世界
        Russian: Привет мир
        Arabic: مرحبا بالعالم
        Hebrew: שלום עולם
        Emoji: 🌍🚀🎉
        Special: ñáéíóú üöä ß
        """

        # Write with safe_write_text
        safe_write_text(test_file, original_content)

        # Read with safe_read_text
        read_content = safe_read_text(test_file)

        # Verify they match exactly
        assert read_content == original_content

    def test_large_utf8_file(self, tmp_path):
        """Test handling of large UTF-8 file."""
        test_file = tmp_path / "large_utf8_test.txt"

        # Create large content with UTF-8 characters
        lines: List[str] = []
        for i in range(1000):
            lines.append(f"Line {i}: こんにちは世界 {i} 🌍")

        content = "\n".join(lines)

        # Write and read
        safe_write_text(test_file, content)
        read_content = safe_read_text(test_file)

        assert read_content == content
        assert len(read_content) > 10000  # Verify it's actually large

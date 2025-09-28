"""Test UTF-8 file I/O utilities with real anime filenames from filenames.txt."""

from pathlib import Path

import pytest

from anivault.utils.files import safe_open, safe_read_text, safe_write_text


class TestUtf8WithRealFilenames:
    """Test UTF-8 handling with real anime filenames."""

    def test_read_filenames_txt(self):
        """Test reading the actual filenames.txt file with UTF-8 content."""
        filenames_path = Path("filenames.txt")

        if not filenames_path.exists():
            pytest.skip("filenames.txt not found")

        # Read the file using our safe_read_text function
        content = safe_read_text(filenames_path)

        # Verify it contains Korean characters
        assert "미래소년 코난" in content
        assert "슈메이커" in content
        assert "Gundam" in content

        # Verify it's not empty
        assert len(content) > 1000

    def test_write_and_read_korean_filenames(self, tmp_path):
        """Test writing and reading Korean anime filenames."""
        test_file = tmp_path / "korean_filenames.txt"

        # Sample Korean anime filenames from the file
        korean_filenames = [
            "미래소년 코난 (ep 제01-02화)ac3_2Ch Kor-Cd01.avi",
            "미래소년 코난 (Ep 제03-04화)Ac3 2Ch Kor Cd02.avi",
            "[슈메이커] Z Gundam TV EP01.avi",
            "[슈메이커] Z Gundam TV EP02.avi",
        ]

        content = "\n".join(korean_filenames)

        # Write using safe_write_text
        safe_write_text(test_file, content)

        # Read back using safe_read_text
        read_content = safe_read_text(test_file)

        # Verify content matches exactly
        assert read_content == content
        assert "미래소년 코난" in read_content
        assert "슈메이커" in read_content
        assert "Gundam" in read_content

    def test_roundtrip_large_filename_set(self, tmp_path):
        """Test roundtrip with a larger set of filenames."""
        test_file = tmp_path / "large_filename_set.txt"

        # Read a sample of filenames from the actual file
        filenames_path = Path("filenames.txt")
        if not filenames_path.exists():
            pytest.skip("filenames.txt not found")

        # Read first 100 lines
        with open(filenames_path, encoding="utf-8") as f:
            lines = [f.readline().strip() for _ in range(100) if f.readline()]

        # Filter out empty lines
        filenames = [line for line in lines if line.strip()]

        if not filenames:
            pytest.skip("No filenames found in filenames.txt")

        content = "\n".join(filenames)

        # Write using safe_write_text
        safe_write_text(test_file, content)

        # Read back using safe_read_text
        read_content = safe_read_text(test_file)

        # Verify content matches exactly
        assert read_content == content

        # Verify some specific Korean content is preserved
        korean_found = any("코난" in line or "슈메이커" in line for line in filenames)
        if korean_found:
            assert "코난" in read_content or "슈메이커" in read_content

    def test_safe_open_with_korean_filenames(self, tmp_path):
        """Test safe_open context manager with Korean filenames."""
        test_file = tmp_path / "한국어_파일명.txt"
        content = "한국어 내용입니다. 미래소년 코난을 시청합니다."

        # Write using safe_open
        with safe_open(test_file, "w") as f:
            f.write(content)

        # Read back using safe_open
        with safe_open(test_file, "r") as f:
            read_content = f.read()

        assert read_content == content
        assert "한국어" in read_content
        assert "미래소년 코난" in read_content

    def test_encoding_consistency(self, tmp_path):
        """Test that encoding is consistent across different operations."""
        test_file = tmp_path / "encoding_test.txt"

        # Mixed content with Korean, English, and special characters
        content = """
        English: Attack on Titan
        Korean: 진격의 거인
        Japanese: 進撃の巨人
        Special: [1080p] [H.264] [AAC]
        Numbers: S01E01, EP 01-02
        """

        # Test multiple write/read cycles
        for i in range(3):
            safe_write_text(test_file, content)
            read_content = safe_read_text(test_file)
            assert read_content == content

        # Test with safe_open context manager
        with safe_open(test_file, "w") as f:
            f.write(content)

        with safe_open(test_file, "r") as f:
            read_content = f.read()

        assert read_content == content

    def test_file_size_with_utf8(self, tmp_path):
        """Test that UTF-8 files are handled correctly regardless of size."""
        test_file = tmp_path / "size_test.txt"

        # Create content with various UTF-8 characters
        base_content = "한국어 English 日本語 Русский العربية עברית 🌍🚀🎉"

        # Create a larger file by repeating the content
        content = "\n".join([f"Line {i}: {base_content}" for i in range(1000)])

        # Write and read
        safe_write_text(test_file, content)
        read_content = safe_read_text(test_file)

        assert read_content == content
        assert len(read_content) > 50000  # Verify it's actually large

        # Verify UTF-8 characters are preserved
        assert "한국어" in read_content
        assert "🌍" in read_content

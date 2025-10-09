"""
Unit tests for CLI validation models and utilities.
"""

import tempfile
from pathlib import Path

import pytest
import typer
from pydantic import ValidationError

from anivault.cli.common.models import DirectoryPath
from anivault.cli.common.validation import NamingFormat, create_validator


class TestDirectoryPath:
    """Test DirectoryPath model validation."""

    def test_valid_directory(self) -> None:
        """Test validation with valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            directory_path = DirectoryPath(path=path)
            assert directory_path.path == path

    def test_nonexistent_directory(self) -> None:
        """Test validation with non-existent directory."""
        nonexistent_path = Path("/nonexistent/directory")
        
        with pytest.raises(ValidationError) as exc_info:
            DirectoryPath(path=nonexistent_path)
        
        assert "Directory does not exist" in str(exc_info.value)

    def test_file_instead_of_directory(self) -> None:
        """Test validation with file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            file_path = Path(temp_file.name)
            
            with pytest.raises(ValidationError) as exc_info:
                DirectoryPath(path=file_path)
            
            assert "Path is not a directory" in str(exc_info.value)

    def test_unreadable_directory(self) -> None:
        """Test validation with unreadable directory."""
        # Skip this test on Windows as permission handling is different
        import sys
        if sys.platform == "win32":
            pytest.skip("Directory permission testing not reliable on Windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            # Make directory unreadable
            path.chmod(0o000)
            
            try:
                with pytest.raises(ValidationError) as exc_info:
                    DirectoryPath(path=path)
                
                assert "Directory is not readable" in str(exc_info.value)
            finally:
                # Restore permissions for cleanup
                path.chmod(0o755)


class TestNamingFormat:
    """Test NamingFormat model validation."""

    def test_valid_format_with_placeholders(self) -> None:
        """Test validation with valid format string containing placeholders."""
        valid_formats = [
            "{series_name}",
            "{series_name} S{season:02d}E{episode:02d}",
            "{series_name} ({year})",
            "{title} - {quality}",
            "{series_name}/{season}/{episode} - {title}"
        ]
        
        for format_str in valid_formats:
            naming_format = NamingFormat(value=format_str)
            assert naming_format.value == format_str

    def test_valid_format_with_format_specifiers(self) -> None:
        """Test validation with format specifiers like :02d."""
        valid_formats = [
            "{series_name} S{season:02d}E{episode:02d}",
            "{year:04d}",
            "{episode:03d}"
        ]
        
        for format_str in valid_formats:
            naming_format = NamingFormat(value=format_str)
            assert naming_format.value == format_str

    def test_no_placeholders(self) -> None:
        """Test validation with format string containing no placeholders."""
        with pytest.raises(ValidationError) as exc_info:
            NamingFormat(value="simple filename")
        
        assert "must contain at least one valid placeholder" in str(exc_info.value)

    def test_invalid_placeholders(self) -> None:
        """Test validation with invalid placeholders."""
        invalid_formats = [
            "{invalid_placeholder}",
            "{series_name} {invalid_field}",
            "{unknown_field}"
        ]
        
        for format_str in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                NamingFormat(value=format_str)
            
            assert "Invalid placeholders found" in str(exc_info.value)

    def test_mismatched_braces(self) -> None:
        """Test validation with mismatched curly braces."""
        invalid_formats = [
            "{series_name",  # Missing closing brace
            "series_name}",  # Missing opening brace
            "{series_name} {season",  # Missing closing brace
            "series_name} {season}"  # Missing opening brace
        ]
        
        for format_str in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                NamingFormat(value=format_str)
            
            assert "mismatched braces" in str(exc_info.value)

    def test_all_valid_placeholders(self) -> None:
        """Test all valid placeholders are accepted."""
        valid_placeholders = [
            "{series_name}", "{season}", "{episode}", "{title}",
            "{year}", "{quality}", "{resolution}", "{codec}"
        ]
        
        for placeholder in valid_placeholders:
            naming_format = NamingFormat(value=placeholder)
            assert naming_format.value == placeholder


class TestCreateValidator:
    """Test create_validator function."""

    def test_directory_path_validator_success(self) -> None:
        """Test create_validator with DirectoryPath for valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = create_validator(DirectoryPath)
            result = validator(temp_dir)
            assert result == Path(temp_dir)

    def test_directory_path_validator_failure(self) -> None:
        """Test create_validator with DirectoryPath for invalid directory."""
        validator = create_validator(DirectoryPath)
        
        with pytest.raises(typer.BadParameter) as exc_info:
            validator("/nonexistent/directory")
        
        assert "Validation failed" in str(exc_info.value)
        assert "Directory does not exist" in str(exc_info.value)

    def test_naming_format_validator_success(self) -> None:
        """Test create_validator with NamingFormat for valid format."""
        validator = create_validator(NamingFormat)
        result = validator("{series_name} S{season:02d}E{episode:02d}")
        assert result == "{series_name} S{season:02d}E{episode:02d}"

    def test_naming_format_validator_failure(self) -> None:
        """Test create_validator with NamingFormat for invalid format."""
        validator = create_validator(NamingFormat)
        
        with pytest.raises(typer.BadParameter) as exc_info:
            validator("{invalid_placeholder}")
        
        assert "Validation failed" in str(exc_info.value)
        assert "Invalid placeholders found" in str(exc_info.value)

    def test_validator_error_message_format(self) -> None:
        """Test that validator provides clear error messages."""
        validator = create_validator(NamingFormat)
        
        with pytest.raises(typer.BadParameter) as exc_info:
            validator("no placeholders")
        
        error_msg = str(exc_info.value)
        assert "Validation failed" in error_msg
        assert "must contain at least one valid placeholder" in error_msg
        assert "Valid placeholders:" in error_msg

    def test_validator_with_multiple_errors(self) -> None:
        """Test validator with multiple validation errors."""
        validator = create_validator(NamingFormat)
        
        with pytest.raises(typer.BadParameter) as exc_info:
            validator("{invalid1} {invalid2}")
        
        error_msg = str(exc_info.value)
        assert "Validation failed" in error_msg
        assert "Invalid placeholders found" in error_msg
        assert "invalid1" in error_msg
        assert "invalid2" in error_msg

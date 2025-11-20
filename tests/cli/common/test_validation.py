"""
Unit tests for CLI validation models and utilities.
"""

import tempfile
from pathlib import Path

import pytest
import typer
from pydantic import ValidationError

from anivault.cli.common.models import DirectoryPath, OrganizeOptions
from anivault.cli.common.validation import (
    NamingFormat,
    create_validator,
    ensure_json_mode_consistency,
    normalize_extensions_list,
    validate_directory_with_context,
    validate_file_path,
)
from anivault.shared.errors import ApplicationError, ErrorCode


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
            "{series_name}/{season}/{episode} - {title}",
        ]

        for format_str in valid_formats:
            naming_format = NamingFormat(value=format_str)
            assert naming_format.value == format_str

    def test_valid_format_with_format_specifiers(self) -> None:
        """Test validation with format specifiers like :02d."""
        valid_formats = [
            "{series_name} S{season:02d}E{episode:02d}",
            "{year:04d}",
            "{episode:03d}",
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
            "{unknown_field}",
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
            "series_name} {season}",  # Missing opening brace
        ]

        for format_str in invalid_formats:
            with pytest.raises(ValidationError) as exc_info:
                NamingFormat(value=format_str)

            assert "mismatched braces" in str(exc_info.value)

    def test_all_valid_placeholders(self) -> None:
        """Test all valid placeholders are accepted."""
        valid_placeholders = [
            "{series_name}",
            "{season}",
            "{episode}",
            "{title}",
            "{year}",
            "{quality}",
            "{resolution}",
            "{codec}",
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


class TestValidateDirectoryWithContext:
    """Test validate_directory_with_context function."""

    def test_valid_directory(self) -> None:
        """Test validation with valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory_with_context(temp_dir, "test_operation")
            assert result == Path(temp_dir)

    def test_nonexistent_directory(self) -> None:
        """Test validation with non-existent directory."""
        with pytest.raises(ApplicationError) as exc_info:
            validate_directory_with_context("/nonexistent/path", "test_operation")

        assert exc_info.value.code == ErrorCode.DIRECTORY_NOT_FOUND
        assert "does not exist" in exc_info.value.message

    def test_file_instead_of_directory(self) -> None:
        """Test validation with file path instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ApplicationError) as exc_info:
                validate_directory_with_context(temp_file.name, "test_operation")

            assert exc_info.value.code == ErrorCode.INVALID_PATH
            assert "not a directory" in exc_info.value.message

    def test_error_context_includes_file_path(self) -> None:
        """Test that error context includes file path."""
        with pytest.raises(ApplicationError) as exc_info:
            validate_directory_with_context("/test/path", "scan_files")

        assert exc_info.value.context is not None
        assert "file_path" in exc_info.value.context.additional_data
        assert exc_info.value.context.operation == "scan_files"


class TestValidateFilePath:
    """Test validate_file_path function."""

    def test_existing_file(self) -> None:
        """Test validation with existing file."""
        # Create temp file, close it, then validate
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        # File is now closed, can be validated and deleted
        try:
            result = validate_file_path(temp_path, "test_operation", must_exist=True)
            assert result == temp_path
        finally:
            temp_path.unlink(missing_ok=True)

    def test_nonexistent_file_must_exist(self) -> None:
        """Test validation with non-existent file when must_exist=True."""
        with pytest.raises(ApplicationError) as exc_info:
            validate_file_path(
                "/nonexistent/file.txt", "test_operation", must_exist=True
            )

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND

    def test_nonexistent_file_output_mode(self) -> None:
        """Test validation with non-existent file when must_exist=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.json"
            result = validate_file_path(output_file, "write_results", must_exist=False)
            assert result == output_file

    def test_output_file_parent_created(self) -> None:
        """Test that parent directory is created for output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "nested" / "path" / "output.json"

            result = validate_file_path(output_file, "write_results", must_exist=False)

            assert result == output_file
            assert output_file.parent.exists()

    def test_directory_instead_of_file(self) -> None:
        """Test validation with directory path instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ApplicationError) as exc_info:
                validate_file_path(temp_dir, "test_operation", must_exist=True)

            assert exc_info.value.code == ErrorCode.INVALID_PATH
            assert "not a file" in exc_info.value.message


class TestEnsureJsonModeConsistency:
    """Test ensure_json_mode_consistency function."""

    def test_json_with_verbose_fails(self) -> None:
        """Test that JSON and verbose flags are mutually exclusive."""

        class MockOptions:
            json_output = True
            verbose = True

        with pytest.raises(ApplicationError) as exc_info:
            ensure_json_mode_consistency(MockOptions(), "test_operation")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "mutually exclusive" in exc_info.value.message

    def test_dry_run_with_yes_fails(self) -> None:
        """Test that dry-run with yes flag is invalid."""

        class MockOptions:
            dry_run = True
            yes = True

        with pytest.raises(ApplicationError) as exc_info:
            ensure_json_mode_consistency(MockOptions(), "test_operation")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "dry-run" in exc_info.value.message
        assert "--yes has no effect" in exc_info.value.message

    def test_valid_combinations(self) -> None:
        """Test that valid option combinations pass."""
        valid_options = [
            type("Options", (), {"json_output": True, "verbose": False}),
            type("Options", (), {"json_output": False, "verbose": True}),
            type("Options", (), {"dry_run": True, "yes": False}),
            type("Options", (), {"dry_run": False, "yes": True}),
            type("Options", (), {"dry_run": False, "yes": False}),
        ]

        for options in valid_options:
            # Should not raise
            ensure_json_mode_consistency(options(), "test_operation")


class TestNormalizeExtensionsList:
    """Test normalize_extensions_list function."""

    def test_normalize_string_input(self) -> None:
        """Test normalization with comma-separated string."""
        result = normalize_extensions_list("mkv,MP4,avi")
        assert result == [".mkv", ".mp4", ".avi"]

    def test_normalize_list_input(self) -> None:
        """Test normalization with list input."""
        result = normalize_extensions_list([".MKV", "mp4", ".AVI"])
        assert result == [".mkv", ".mp4", ".avi"]

    def test_add_leading_dot(self) -> None:
        """Test that leading dot is added if missing."""
        result = normalize_extensions_list("mkv,mp4")
        assert all(ext.startswith(".") for ext in result)

    def test_lowercase_conversion(self) -> None:
        """Test that extensions are converted to lowercase."""
        result = normalize_extensions_list("MKV,MP4,AVI")
        assert all(ext.islower() for ext in result)

    def test_strip_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        result = normalize_extensions_list(" mkv , mp4 , avi ")
        assert result == [".mkv", ".mp4", ".avi"]

    def test_empty_strings_skipped(self) -> None:
        """Test that empty strings are skipped."""
        result = normalize_extensions_list("mkv,,mp4,,avi")
        assert result == [".mkv", ".mp4", ".avi"]

    def test_mixed_formats(self) -> None:
        """Test handling of mixed formats."""
        result = normalize_extensions_list([".mkv", "MP4", " avi ", ".WMV"])
        assert result == [".mkv", ".mp4", ".avi", ".wmv"]

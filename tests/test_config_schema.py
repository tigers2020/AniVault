"""
Tests for the configuration schema validation system.

This module tests the ConfigSchemaValidator class to ensure proper
validation of configuration structure and values.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.core.config_schema import ConfigSchemaValidator


class TestConfigSchemaValidator:
    """Test cases for ConfigSchemaValidator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = ConfigSchemaValidator()

    def test_initialization(self) -> None:
        """Test ConfigSchemaValidator initialization."""
        assert self.validator.validator is not None
        assert self.validator._schema is not None
        assert len(self.validator._schema) > 0

    def test_validate_valid_config(self) -> None:
        """Test validation of a valid configuration."""
        valid_config = {
            "version": "1.0.0",
            "security": {
                "encryption_enabled": True,
                "encrypted_keys": ["services.tmdb_api.api_key"],
            },
            "services": {
                "tmdb_api": {
                    "api_key": "a1b2c3d4e5f6789012345678901234ab",
                    "language": "ko-KR",
                    "timeout": 30,
                    "retry_attempts": 3,
                }
            },
            "application": {
                "file_organization": {
                    "destination_root": "/test/path",
                    "organize_mode": "복사",
                    "naming_scheme": "standard",
                    "safe_mode": True,
                    "backup_before_organize": False,
                    "prefer_anitopy": False,
                    "fallback_parser": "FileParser",
                    "realtime_monitoring": False,
                    "auto_refresh_interval": 30,
                    "show_advanced_options": False,
                },
                "backup_settings": {"backup_location": "/backup/path", "max_backup_count": 10},
                "logging_config": {"log_level": "INFO", "log_to_file": False},
                "performance_settings": {"max_workers": 4, "cache_size": 100},
            },
            "user_preferences": {
                "gui_state": {
                    "window_geometry": None,
                    "last_source_directory": "/source/path",
                    "last_destination_directory": "/dest/path",
                    "remember_last_session": True,
                },
                "accessibility": {
                    "high_contrast_mode": False,
                    "keyboard_navigation": True,
                    "screen_reader_support": True,
                },
                "theme_preferences": {"theme": "dark", "language": "ko"},
                "language_settings": {"date_format": "YYYY-MM-DD", "time_format": "HH:mm:ss"},
            },
            "metadata": {"migrated_at": "", "migration_version": "1.0.0", "source_files": []},
        }

        is_valid, errors = self.validator.validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required_sections(self) -> None:
        """Test validation with missing required sections."""
        invalid_config = {
            "version": "1.0.0"
            # Missing required sections: security, application, user_preferences
        }

        is_valid, errors = self.validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Missing required section: security" in error for error in errors)
        assert any("Missing required section: application" in error for error in errors)
        assert any("Missing required section: user_preferences" in error for error in errors)

    def test_validate_invalid_types(self) -> None:
        """Test validation with invalid data types."""
        invalid_config = {
            "version": 1.0,  # Should be string
            "security": {
                "encryption_enabled": "true",  # Should be boolean
                "encrypted_keys": "not_a_list",  # Should be list
            },
            "application": {"file_organization": {"safe_mode": "yes"}},  # Should be boolean
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {},
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Invalid type for version" in error for error in errors)
        assert any("Invalid type for security.encryption_enabled" in error for error in errors)
        assert any("Invalid type for security.encrypted_keys" in error for error in errors)

    def test_validate_invalid_values(self) -> None:
        """Test validation with invalid values."""
        invalid_config = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": {
                "tmdb_api": {
                    "api_key": "invalid_key",  # Invalid API key format
                    "language": "invalid_lang",  # Invalid language
                    "timeout": 500,  # Out of range
                    "retry_attempts": 15,  # Out of range
                }
            },
            "application": {
                "file_organization": {
                    "organize_mode": "invalid_mode",  # Invalid organize mode
                    "naming_scheme": "invalid_scheme",  # Invalid naming scheme
                    "auto_refresh_interval": 5000,  # Out of range
                },
                "backup_settings": {"max_backup_count": 200},  # Out of range
                "logging_config": {"log_level": "INVALID"},  # Invalid log level
                "performance_settings": {"max_workers": 50},  # Out of range
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {
                    "theme": "invalid_theme",  # Invalid theme
                    "language": "invalid_lang",  # Invalid language
                },
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Invalid value for services.tmdb_api.api_key" in error for error in errors)
        assert any("Invalid value for services.tmdb_api.language" in error for error in errors)
        assert any("Value out of range for services.tmdb_api.timeout" in error for error in errors)
        assert any(
            "Value out of range for services.tmdb_api.retry_attempts" in error for error in errors
        )
        assert any(
            "Invalid value for application.file_organization.organize_mode" in error
            for error in errors
        )
        assert any(
            "Invalid value for application.file_organization.naming_scheme" in error
            for error in errors
        )
        assert any(
            "Value out of range for application.file_organization.auto_refresh_interval" in error
            for error in errors
        )
        assert any(
            "Value out of range for application.backup_settings.max_backup_count" in error
            for error in errors
        )
        assert any(
            "Invalid value for application.logging_config.log_level" in error for error in errors
        )
        assert any(
            "Value out of range for application.performance_settings.max_workers" in error
            for error in errors
        )
        assert any(
            "Invalid value for user_preferences.theme_preferences.theme" in error
            for error in errors
        )
        assert any(
            "Invalid value for user_preferences.theme_preferences.language" in error
            for error in errors
        )

    def test_validate_string_length(self) -> None:
        """Test string length validation."""
        invalid_config = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": {
                "tmdb_api": {
                    "api_key": "c479f9ce20ccbcc06dbcce991a238120",
                    "language": "ko-KR",
                    "timeout": 30,
                    "retry_attempts": 3,
                }
            },
            "application": {
                "file_organization": {
                    "fallback_parser": "",  # Too short
                },
                "backup_settings": {},
                "logging_config": {},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {},
                "language_settings": {
                    "date_format": "x" * 50,  # Too long
                    "time_format": "x" * 50,  # Too long
                },
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any(
            "Invalid string length for application.file_organization.fallback_parser" in error
            for error in errors
        )
        assert any(
            "Invalid string length for user_preferences.language_settings.date_format" in error
            for error in errors
        )
        assert any(
            "Invalid string length for user_preferences.language_settings.time_format" in error
            for error in errors
        )

    def test_validate_path_validation(self) -> None:
        """Test path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_file.txt"
            test_file.write_text("test")

            # Valid path configuration
            valid_config = {
                "version": "1.0.0",
                "security": {"encryption_enabled": True, "encrypted_keys": []},
                "services": {
                    "tmdb_api": {
                        "api_key": "c479f9ce20ccbcc06dbcce991a238120",
                        "language": "ko-KR",
                        "timeout": 30,
                        "retry_attempts": 3,
                    }
                },
                "application": {
                    "file_organization": {
                        "destination_root": str(temp_path)  # Valid directory path
                    },
                    "backup_settings": {},
                    "logging_config": {},
                    "performance_settings": {},
                },
                "user_preferences": {
                    "gui_state": {"last_source_directory": str(temp_path)},  # Valid directory path
                    "accessibility": {},
                    "theme_preferences": {},
                    "language_settings": {},
                },
                "metadata": {},
            }

            is_valid, errors = self.validator.validate_config(valid_config)
            assert is_valid is True
            assert len(errors) == 0

            # Invalid path configuration
            invalid_config = {
                "version": "1.0.0",
                "security": {"encryption_enabled": True, "encrypted_keys": []},
                "services": {
                    "tmdb_api": {
                        "api_key": "c479f9ce20ccbcc06dbcce991a238120",
                        "language": "ko-KR",
                        "timeout": 30,
                        "retry_attempts": 3,
                    }
                },
                "application": {
                    "file_organization": {"destination_root": "/nonexistent/path"},  # Invalid path
                    "backup_settings": {},
                    "logging_config": {},
                    "performance_settings": {},
                },
                "user_preferences": {
                    "gui_state": {},
                    "accessibility": {},
                    "theme_preferences": {},
                    "language_settings": {},
                },
                "metadata": {},
            }

            is_valid, errors = self.validator.validate_config(invalid_config)
            assert is_valid is False
            assert len(errors) > 0
            assert any(
                "Invalid path for application.file_organization.destination_root" in error
                for error in errors
            )

    def test_validate_nested_properties(self) -> None:
        """Test validation of nested properties."""
        config_with_missing_nested = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": {
                "tmdb_api": {
                    "api_key": "c479f9ce20ccbcc06dbcce991a238120",
                    "language": "ko-KR",
                    "timeout": 30,
                    "retry_attempts": 3,
                }
            },
            "application": {
                "file_organization": {
                    # Missing required properties
                },
                "backup_settings": {},
                "logging_config": {},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {},
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(config_with_missing_nested)
        # Should be valid since nested properties are not required by default
        assert is_valid is True

    def test_get_default_config(self) -> None:
        """Test getting default configuration."""
        default_config = self.validator.get_default_config()

        # Check that all required sections are present
        assert "version" in default_config
        assert "security" in default_config
        assert "application" in default_config
        assert "user_preferences" in default_config
        assert "metadata" in default_config

        # Check that default values are set
        assert default_config["security"]["encryption_enabled"] is True
        assert default_config["application"]["file_organization"]["safe_mode"] is True
        assert default_config["user_preferences"]["theme_preferences"]["theme"] == "auto"
        assert default_config["user_preferences"]["theme_preferences"]["language"] == "ko"

    def test_get_schema_errors(self) -> None:
        """Test getting detailed schema errors."""
        invalid_config = {
            "version": "invalid_version",
            "security": {"encryption_enabled": "not_boolean"},
        }

        errors = self.validator.get_schema_errors(invalid_config)
        assert len(errors) > 0
        # Check for type error for security.encryption_enabled
        assert any("Invalid type for security.encryption_enabled" in error for error in errors)
        # Check for missing required sections
        assert any("Missing required section" in error for error in errors)

    def test_validate_services_section(self) -> None:
        """Test validation of services section."""
        # Valid TMDB configuration
        valid_services = {
            "tmdb_api": {
                "api_key": "a1b2c3d4e5f6789012345678901234ab",
                "language": "ko-KR",
                "timeout": 30,
                "retry_attempts": 3,
            }
        }

        config = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": valid_services,
            "application": {
                "file_organization": {},
                "backup_settings": {},
                "logging_config": {},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {},
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is True
        assert len(errors) == 0

        # Invalid TMDB configuration
        invalid_services = {
            "tmdb_api": {
                "api_key": "invalid_key",
                "language": "invalid_lang",
                "timeout": 500,
                "retry_attempts": 15,
            }
        }

        config["services"] = invalid_services
        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("services.tmdb_api" in error for error in errors)

    def test_validate_application_section(self) -> None:
        """Test validation of application section."""
        # Valid file organization configuration
        valid_file_org = {
            "destination_root": "/test/path",
            "organize_mode": "복사",
            "naming_scheme": "standard",
            "safe_mode": True,
            "backup_before_organize": False,
            "prefer_anitopy": False,
            "fallback_parser": "FileParser",
            "realtime_monitoring": False,
            "auto_refresh_interval": 30,
            "show_advanced_options": False,
        }

        config = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": {},
            "application": {
                "file_organization": valid_file_org,
                "backup_settings": {},
                "logging_config": {},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": {},
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is True
        assert len(errors) == 0

        # Invalid file organization configuration
        invalid_file_org = {
            "organize_mode": "invalid_mode",
            "naming_scheme": "invalid_scheme",
            "auto_refresh_interval": 5000,
        }

        config["application"]["file_organization"] = invalid_file_org
        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("application.file_organization" in error for error in errors)

    def test_validate_user_preferences_section(self) -> None:
        """Test validation of user preferences section."""
        # Valid theme preferences
        valid_theme_prefs = {"theme": "dark", "language": "ko"}

        config = {
            "version": "1.0.0",
            "security": {"encryption_enabled": True, "encrypted_keys": []},
            "services": {},
            "application": {
                "file_organization": {},
                "backup_settings": {},
                "logging_config": {},
                "performance_settings": {},
            },
            "user_preferences": {
                "gui_state": {},
                "accessibility": {},
                "theme_preferences": valid_theme_prefs,
                "language_settings": {},
            },
            "metadata": {},
        }

        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is True
        assert len(errors) == 0

        # Invalid theme preferences
        invalid_theme_prefs = {"theme": "invalid_theme", "language": "invalid_lang"}

        config["user_preferences"]["theme_preferences"] = invalid_theme_prefs
        is_valid, errors = self.validator.validate_config(config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("user_preferences.theme_preferences.theme" in error for error in errors)
        assert any("user_preferences.theme_preferences.language" in error for error in errors)

    def test_validate_with_mock_validators(self) -> None:
        """Test validation with mocked validator methods."""
        with patch.object(self.validator.validator, "validate_api_key", return_value=False):
            config = {
                "version": "1.0.0",
                "security": {"encryption_enabled": True, "encrypted_keys": []},
                "services": {"tmdb_api": {"api_key": "a1b2c3d4e5f6789012345678901234ab"}},
                "application": {
                    "file_organization": {},
                    "backup_settings": {},
                    "logging_config": {},
                    "performance_settings": {},
                },
                "user_preferences": {
                    "gui_state": {},
                    "accessibility": {},
                    "theme_preferences": {},
                    "language_settings": {},
                },
                "metadata": {},
            }

            is_valid, errors = self.validator.validate_config(config)
            assert is_valid is False
            assert len(errors) > 0
            assert any("Invalid value for services.tmdb_api.api_key" in error for error in errors)

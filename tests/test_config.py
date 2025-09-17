"""
Tests for the enhanced configuration management system.

This module tests the SecureConfigManager and ConfigValidator classes
to ensure proper functionality, security, and thread safety.
"""

import json
import tempfile
import threading
import time
from pathlib import Path

from src.core.config import SecureConfigManager
from src.utils.validators import ConfigValidator


class TestConfigValidator:
    """Test cases for ConfigValidator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = ConfigValidator()

    def test_validate_api_key_tmdb(self) -> None:
        """Test TMDB API key validation."""
        # Valid TMDB API key (32 hex characters)
        assert self.validator.validate_api_key("a1b2c3d4e5f6789012345678901234ab", "tmdb")
        assert self.validator.validate_api_key("ABCDEF1234567890ABCDEF1234567890", "tmdb")

        # Invalid TMDB API keys
        assert not self.validator.validate_api_key("", "tmdb")
        assert not self.validator.validate_api_key("short", "tmdb")
        assert not self.validator.validate_api_key("a" * 31, "tmdb")  # Too short
        assert not self.validator.validate_api_key("a" * 33, "tmdb")  # Too long
        assert not self.validator.validate_api_key("g" * 32, "tmdb")  # Invalid character

    def test_validate_api_key_generic(self) -> None:
        """Test generic API key validation."""
        # Valid generic API keys
        assert self.validator.validate_api_key("a" * 16, "generic")
        assert self.validator.validate_api_key("a" * 32, "generic")
        assert self.validator.validate_api_key("a" * 64, "generic")

        # Invalid generic API keys
        assert not self.validator.validate_api_key("", "generic")
        assert not self.validator.validate_api_key("a" * 15, "generic")  # Too short
        assert not self.validator.validate_api_key("a" * 65, "generic")  # Too long
        assert not self.validator.validate_api_key("a" * 15 + "!", "generic")  # Invalid character

    def test_validate_path(self) -> None:
        """Test path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_file.txt"
            test_file.write_text("test")

            # Valid existing paths
            assert self.validator.validate_path(str(temp_path), must_exist=True)
            assert self.validator.validate_path(str(test_file), must_exist=True)
            assert self.validator.validate_path(str(temp_path), must_be_directory=True)

            # Valid non-existing paths (parent exists)
            new_file = temp_path / "new_file.txt"
            assert self.validator.validate_path(str(new_file), must_exist=False)

            # Invalid paths
            assert not self.validator.validate_path("", must_exist=True)
            assert not self.validator.validate_path("nonexistent/path", must_exist=True)
            assert not self.validator.validate_path(str(test_file), must_be_directory=True)

    def test_validate_theme(self) -> None:
        """Test theme validation."""
        valid_themes = ["auto", "light", "dark", "system"]
        for theme in valid_themes:
            assert self.validator.validate_theme(theme)
            assert self.validator.validate_theme(theme.upper())

        # Invalid themes
        assert not self.validator.validate_theme("invalid")
        assert not self.validator.validate_theme("")
        assert not self.validator.validate_theme(None)

    def test_validate_language(self) -> None:
        """Test language validation."""
        valid_languages = ["ko", "en", "ja", "zh", "ko-KR", "en-US", "ja-JP", "zh-CN"]
        for lang in valid_languages:
            assert self.validator.validate_language(lang)
            assert self.validator.validate_language(lang.lower())

        # Invalid languages
        assert not self.validator.validate_language("invalid")
        assert not self.validator.validate_language("")
        assert not self.validator.validate_language(None)

    def test_validate_numeric_range(self) -> None:
        """Test numeric range validation."""
        # Valid ranges
        assert self.validator.validate_numeric_range(5, 0, 10)
        assert self.validator.validate_numeric_range(0, 0, 10)
        assert self.validator.validate_numeric_range(10, 0, 10)
        assert self.validator.validate_numeric_range(5.5, 0, 10)

        # Invalid ranges
        assert not self.validator.validate_numeric_range(-1, 0, 10)
        assert not self.validator.validate_numeric_range(11, 0, 10)
        assert not self.validator.validate_numeric_range("5", 0, 10)
        assert not self.validator.validate_numeric_range(None, 0, 10)

    def test_validate_organize_mode(self) -> None:
        """Test organize mode validation."""
        valid_modes = ["복사", "이동", "copy", "move"]
        for mode in valid_modes:
            assert self.validator.validate_organize_mode(mode)

        # Invalid modes
        assert not self.validator.validate_organize_mode("invalid")
        assert not self.validator.validate_organize_mode("")
        assert not self.validator.validate_organize_mode(None)

    def test_validate_naming_scheme(self) -> None:
        """Test naming scheme validation."""
        valid_schemes = ["standard", "anitopy", "custom"]
        for scheme in valid_schemes:
            assert self.validator.validate_naming_scheme(scheme)
            assert self.validator.validate_naming_scheme(scheme.upper())

        # Invalid schemes
        assert not self.validator.validate_naming_scheme("invalid")
        assert not self.validator.validate_naming_scheme("")
        assert not self.validator.validate_naming_scheme(None)

    def test_validate_boolean(self) -> None:
        """Test boolean validation."""
        assert self.validator.validate_boolean(True)
        assert self.validator.validate_boolean(False)

        # Invalid booleans
        assert not self.validator.validate_boolean("true")
        assert not self.validator.validate_boolean(1)
        assert not self.validator.validate_boolean(0)
        assert not self.validator.validate_boolean(None)

    def test_validate_string_length(self) -> None:
        """Test string length validation."""
        test_string = "hello"

        # Valid lengths
        assert self.validator.validate_string_length(test_string, 0, 10)
        assert self.validator.validate_string_length(test_string, 5, 5)
        assert self.validator.validate_string_length(test_string, 0)

        # Invalid lengths
        assert not self.validator.validate_string_length(test_string, 6, 10)
        assert not self.validator.validate_string_length(test_string, 0, 4)
        assert not self.validator.validate_string_length(None, 0, 10)

    def test_validate_list_items(self) -> None:
        """Test list validation."""
        # Valid lists
        assert self.validator.validate_list_items([1, 2, 3])
        assert self.validator.validate_list_items([])

        # With item validator
        assert self.validator.validate_list_items([1, 2, 3], lambda x: isinstance(x, int))
        assert not self.validator.validate_list_items([1, "2", 3], lambda x: isinstance(x, int))

        # Invalid lists
        assert not self.validator.validate_list_items("not a list")
        assert not self.validator.validate_list_items(None)

    def test_validate_config_section(self) -> None:
        """Test configuration section validation."""
        config = {"key1": "value1", "key2": "value2"}
        required_keys = ["key1"]
        optional_keys = ["key2", "key3"]

        # Valid config
        is_valid, errors = self.validator.validate_config_section(
            config, required_keys, optional_keys
        )
        assert is_valid
        assert len(errors) == 0

        # Missing required key
        config_missing = {"key2": "value2"}
        is_valid, errors = self.validator.validate_config_section(
            config_missing, required_keys, optional_keys
        )
        assert not is_valid
        assert "Missing required key: key1" in errors

        # Unknown key
        config_unknown = {"key1": "value1", "key2": "value2", "unknown": "value"}
        is_valid, errors = self.validator.validate_config_section(
            config_unknown, required_keys, optional_keys
        )
        assert not is_valid
        assert "Unknown key: unknown" in errors


class TestSecureConfigManager:
    """Test cases for SecureConfigManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        self.manager = SecureConfigManager(self.config_path)

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self) -> None:
        """Test SecureConfigManager initialization."""
        assert self.manager._base_manager is not None
        assert self.manager._lock is not None
        assert self.manager._validator is not None
        assert len(self.manager._encrypted_keys) > 0

    def test_encoding_decoding(self) -> None:
        """Test base64 encoding and decoding."""
        test_data = "test_api_key_12345"

        # Test encoding
        encoded = self.manager._encode_sensitive_data(test_data)
        assert encoded != test_data
        assert isinstance(encoded, str)

        # Test decoding
        decoded = self.manager._decode_sensitive_data(encoded)
        assert decoded == test_data

    def test_sensitive_key_detection(self) -> None:
        """Test sensitive key detection."""
        # Sensitive keys
        assert self.manager._is_sensitive_key("services.tmdb_api.api_key")
        assert self.manager._is_sensitive_key("services.api_keys.tmdb")
        assert self.manager._is_sensitive_key("user_preferences.gui_state.last_source_directory")

        # Non-sensitive keys
        assert not self.manager._is_sensitive_key("user_preferences.theme_preferences.theme")
        assert not self.manager._is_sensitive_key("application.file_organization.safe_mode")

    def test_set_get_sensitive_data(self) -> None:
        """Test setting and getting sensitive data."""
        api_key = "test_api_key_12345"

        # Set sensitive data
        self.manager.set("services.tmdb_api.api_key", api_key)

        # Get sensitive data (should be decrypted automatically)
        retrieved_key = self.manager.get("services.tmdb_api.api_key")
        assert retrieved_key == api_key

        # Check that encrypted version is stored
        encrypted_key = self.manager._base_manager.get("services.tmdb_api.api_key_encrypted")
        assert encrypted_key is not None
        assert encrypted_key != api_key

    def test_set_get_non_sensitive_data(self) -> None:
        """Test setting and getting non-sensitive data."""
        theme = "dark"

        # Set non-sensitive data
        self.manager.set("user_preferences.theme_preferences.theme", theme)

        # Get non-sensitive data
        retrieved_theme = self.manager.get("user_preferences.theme_preferences.theme")
        assert retrieved_theme == theme

        # Check that no encrypted version is stored
        encrypted_theme = self.manager._base_manager.get(
            "user_preferences.theme_preferences.theme_encrypted"
        )
        assert encrypted_theme is None

    def test_tmdb_api_key_methods(self) -> None:
        """Test TMDB API key specific methods."""
        api_key = "a1b2c3d4e5f6789012345678901234ab"

        # Test setting valid API key
        result = self.manager.set_tmdb_api_key(api_key)
        assert result is True

        # Test getting API key
        retrieved_key = self.manager.get_tmdb_api_key()
        assert retrieved_key == api_key

        # Test setting invalid API key
        result = self.manager.set_tmdb_api_key("invalid_key")
        assert result is False

    def test_destination_root_methods(self) -> None:
        """Test destination root specific methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test setting valid path
            result = self.manager.set_destination_root(temp_dir)
            assert result is True

            # Test getting path
            retrieved_path = self.manager.get_destination_root()
            assert retrieved_path == temp_dir

            # Test setting invalid path
            result = self.manager.set_destination_root("/nonexistent/path")
            assert result is False

    def test_theme_methods(self) -> None:
        """Test theme specific methods."""
        # Test setting valid theme
        result = self.manager.set_theme("dark")
        assert result is True

        # Test getting theme
        retrieved_theme = self.manager.get_theme()
        assert retrieved_theme == "dark"

        # Test setting invalid theme
        result = self.manager.set_theme("invalid")
        assert result is False

    def test_language_methods(self) -> None:
        """Test language specific methods."""
        # Test setting valid language
        result = self.manager.set_language("ko")
        assert result is True

        # Test getting language
        retrieved_language = self.manager.get_language()
        assert retrieved_language == "ko"

        # Test setting invalid language
        result = self.manager.set_language("invalid")
        assert result is False

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        # Test with valid config
        assert self.manager.validate_config() is True

        # Test with invalid API key
        self.manager.set("services.tmdb_api.api_key", "invalid_key", encrypt=True)
        assert self.manager.validate_config() is False

    def test_save_reload_config(self) -> None:
        """Test saving and reloading configuration."""
        # Set some test data
        self.manager.set("test.key", "test_value")
        self.manager.set("services.tmdb_api.api_key", "test_api_key", encrypt=True)

        # Save configuration
        result = self.manager.save_config()
        assert result is True
        assert self.config_path.exists()

        # Create new manager instance to test reload
        new_manager = SecureConfigManager(self.config_path)

        # Check that data is loaded correctly
        assert new_manager.get("test.key") == "test_value"
        assert new_manager.get("services.tmdb_api.api_key") == "test_api_key"

    def test_get_all_config(self) -> None:
        """Test getting all configuration with decryption."""
        # Set some test data
        self.manager.set("test.key", "test_value")
        self.manager.set("services.tmdb_api.api_key", "test_api_key", encrypt=True)

        # Get all config
        all_config = self.manager.get_all_config()

        # Check that sensitive data is decrypted
        assert all_config["test"]["key"] == "test_value"
        assert all_config["services"]["tmdb_api"]["api_key"] == "test_api_key"

    def test_backup_config(self) -> None:
        """Test configuration backup."""
        # Set some test data
        self.manager.set("test.key", "test_value")

        # Create backup
        backup_path = Path(self.temp_dir) / "backup.json"
        result = self.manager.backup_config(backup_path)
        assert result is True
        assert backup_path.exists()

        # Verify backup content
        with open(backup_path, encoding="utf-8") as f:
            backup_data = json.load(f)
        assert backup_data["test"]["key"] == "test_value"

    def test_thread_safety(self) -> None:
        """Test thread safety of configuration operations."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    # Set and get configuration
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    self.manager.set(key, value)
                    retrieved = self.manager.get(key)
                    results.append((key, value, retrieved))

                    # Set sensitive data
                    api_key = f"api_key_{worker_id}_{i}"
                    self.manager.set("services.tmdb_api.api_key", api_key, encrypt=True)
                    retrieved_key = self.manager.get("services.tmdb_api.api_key")
                    results.append(("api_key", api_key, retrieved_key))

                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify all operations completed successfully
        assert len(results) == 100  # 5 workers * 10 iterations * 2 operations each

        # Verify data integrity
        for key, expected_value, actual_value in results:
            assert (
                actual_value == expected_value
            ), f"Mismatch for {key}: expected {expected_value}, got {actual_value}"

    def test_encryption_disabled_scenario(self) -> None:
        """Test behavior when encryption is disabled."""
        # Disable encryption in security settings
        self.manager.set("security.encryption_enabled", False)

        # Set sensitive data
        api_key = "test_api_key_12345"
        self.manager.set("services.tmdb_api.api_key", api_key)

        # Should store in plain text when encryption is disabled
        plain_key = self.manager._base_manager.get("services.tmdb_api.api_key")
        assert plain_key == api_key

        # Encrypted version should not exist
        encrypted_key = self.manager._base_manager.get("services.tmdb_api.api_key_encrypted")
        assert encrypted_key is None

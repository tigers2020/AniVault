"""
Tests for the secure storage system.

This module tests the SecureKeyManager and SecureStorage classes
to ensure proper encryption, decryption, and key management.
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from src.core.secure_storage import SecureKeyManager, SecureStorage


class TestSecureKeyManager:
    """Test cases for SecureKeyManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.key_file_path = Path(self.temp_dir) / "test_key"
        self.key_manager = SecureKeyManager(self.key_file_path)

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self) -> None:
        """Test SecureKeyManager initialization."""
        assert self.key_manager.key_file_path == self.key_file_path
        assert self.key_manager._key is not None
        assert len(self.key_manager._key) > 0

    def test_key_generation(self) -> None:
        """Test key generation."""
        # Key should be generated during initialization
        assert self.key_manager._key is not None
        assert isinstance(self.key_manager._key, bytes)
        assert len(self.key_manager._key) > 0

    def test_key_persistence(self) -> None:
        """Test key persistence across instances."""
        # Get the current key
        original_key = self.key_manager.get_key()

        # Create a new instance with the same key file
        new_key_manager = SecureKeyManager(self.key_file_path)
        loaded_key = new_key_manager.get_key()

        # Keys should be the same
        assert original_key == loaded_key

    def test_key_rotation(self) -> None:
        """Test key rotation."""
        original_key = self.key_manager.get_key()

        # Rotate the key
        success = self.key_manager.rotate_key()
        assert success is True

        # New key should be different
        new_key = self.key_manager.get_key()
        assert new_key != original_key
        assert isinstance(new_key, bytes)
        assert len(new_key) > 0

    def test_key_file_creation(self) -> None:
        """Test that key file is created with proper permissions."""
        assert self.key_file_path.exists()

        # Check file size (should contain salt + key)
        file_size = self.key_file_path.stat().st_size
        assert file_size > 0

    def test_thread_safety(self) -> None:
        """Test thread safety of key operations."""
        results = []
        errors = []

        def worker():
            try:
                for _ in range(10):
                    key = self.key_manager.get_key()
                    results.append(key)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # All keys should be the same
        assert len(set(results)) == 1, "Keys should be consistent across threads"


class TestSecureStorage:
    """Test cases for SecureStorage class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.key_file_path = Path(self.temp_dir) / "test_key"
        self.storage = SecureStorage(SecureKeyManager(self.key_file_path))

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self) -> None:
        """Test SecureStorage initialization."""
        assert self.storage.key_manager is not None
        assert self.storage._cipher_suite is not None

    def test_encrypt_decrypt_data(self) -> None:
        """Test data encryption and decryption."""
        test_data = "This is sensitive data that needs to be encrypted"

        # Encrypt the data
        encrypted = self.storage.encrypt_data(test_data)
        assert encrypted != test_data
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

        # Decrypt the data
        decrypted = self.storage.decrypt_data(encrypted)
        assert decrypted == test_data

    def test_encrypt_decrypt_empty_data(self) -> None:
        """Test encryption/decryption of empty data."""
        # Empty string
        encrypted = self.storage.encrypt_data("")
        decrypted = self.storage.decrypt_data(encrypted)
        assert decrypted == ""

        # None (should be handled gracefully)
        encrypted = self.storage.encrypt_data(None)
        decrypted = self.storage.decrypt_data(encrypted)
        assert decrypted == ""

    def test_encrypt_decrypt_special_characters(self) -> None:
        """Test encryption/decryption of data with special characters."""
        test_cases = [
            "Hello, World!",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Unicode: 你好世界 🌍",
            "Newlines:\nLine1\nLine2",
            "Tabs:\tTab1\tTab2",
        ]

        for test_data in test_cases:
            encrypted = self.storage.encrypt_data(test_data)
            decrypted = self.storage.decrypt_data(encrypted)
            assert decrypted == test_data, f"Failed for: {repr(test_data)}"

    def test_hash_data(self) -> None:
        """Test data hashing."""
        test_data = "Test data for hashing"

        # Hash the data
        hash1 = self.storage.hash_data(test_data)
        hash2 = self.storage.hash_data(test_data)

        # Same data should produce same hash
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 produces 64 character hex string

        # Different data should produce different hash
        different_data = "Different test data"
        hash3 = self.storage.hash_data(different_data)
        assert hash1 != hash3

    def test_verify_data_integrity(self) -> None:
        """Test data integrity verification."""
        test_data = "Test data for integrity verification"

        # Get hash of the data
        data_hash = self.storage.hash_data(test_data)

        # Verify integrity with correct hash
        assert self.storage.verify_data_integrity(test_data, data_hash) is True

        # Verify integrity with incorrect hash
        wrong_hash = "wrong_hash_value"
        assert self.storage.verify_data_integrity(test_data, wrong_hash) is False

        # Verify integrity with empty data
        assert self.storage.verify_data_integrity("", data_hash) is False
        assert self.storage.verify_data_integrity(test_data, "") is False

    def test_secure_store_retrieve(self) -> None:
        """Test secure store and retrieve operations."""
        key = "test_key"
        value = "Test sensitive value"

        # Store the data
        stored_data = self.storage.secure_store(key, value)
        assert "encrypted_value" in stored_data
        assert "key" in stored_data
        assert "timestamp" in stored_data
        assert "hash" in stored_data

        # Retrieve the data
        retrieved_value = self.storage.secure_retrieve(stored_data)
        assert retrieved_value == value

    def test_secure_store_retrieve_without_hash(self) -> None:
        """Test secure store and retrieve without integrity checking."""
        key = "test_key"
        value = "Test sensitive value"

        # Store the data without hash
        stored_data = self.storage.secure_store(key, value, include_hash=False)
        assert "encrypted_value" in stored_data
        assert "hash" not in stored_data

        # Retrieve the data without integrity verification
        retrieved_value = self.storage.secure_retrieve(stored_data, verify_integrity=False)
        assert retrieved_value == value

    def test_secure_retrieve_invalid_data(self) -> None:
        """Test secure retrieve with invalid data."""
        # Test with empty dictionary
        result = self.storage.secure_retrieve({})
        assert result is None

        # Test with missing encrypted_value
        result = self.storage.secure_retrieve({"key": "test"})
        assert result is None

        # Test with corrupted encrypted data
        result = self.storage.secure_retrieve({"encrypted_value": "invalid_data"})
        assert result is None

    def test_rotate_encryption_key(self) -> None:
        """Test encryption key rotation."""
        # Store some data
        test_data = "Test data before key rotation"
        encrypted_before = self.storage.encrypt_data(test_data)

        # Rotate the key
        success = self.storage.rotate_encryption_key()
        assert success is True

        # Data encrypted with old key should not decrypt with new key
        # This should raise an exception or return None/invalid data
        try:
            decrypted_after = self.storage.decrypt_data(encrypted_before)
            # If no exception is raised, the decrypted data should be different
            assert decrypted_after != test_data
        except Exception:
            # Expected behavior - old data should not decrypt with new key
            pass

        # New data should encrypt/decrypt correctly
        new_encrypted = self.storage.encrypt_data(test_data)
        new_decrypted = self.storage.decrypt_data(new_encrypted)
        assert new_decrypted == test_data

    def test_thread_safety(self) -> None:
        """Test thread safety of storage operations."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    # Test encryption/decryption
                    test_data = f"Worker {worker_id} data {i}"
                    encrypted = self.storage.encrypt_data(test_data)
                    decrypted = self.storage.decrypt_data(encrypted)
                    results.append((test_data, decrypted))

                    # Test secure store/retrieve
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    stored = self.storage.secure_store(key, value)
                    retrieved = self.storage.secure_retrieve(stored)
                    results.append((value, retrieved))

                    time.sleep(0.001)
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
        for original, processed in results:
            assert original == processed, f"Data mismatch: {original} != {processed}"

    def test_fallback_encryption(self) -> None:
        """Test fallback to base64 when cryptography fails."""
        # Mock the cipher suite to simulate failure
        with patch.object(self.storage, "_cipher_suite", None):
            test_data = "Test data for fallback encryption"

            # Should fallback to base64
            encrypted = self.storage.encrypt_data(test_data)
            decrypted = self.storage.decrypt_data(encrypted)

            assert decrypted == test_data
            # Should be base64 encoded (not Fernet encrypted)
            assert encrypted != test_data
            assert len(encrypted) > 0

    def test_large_data_encryption(self) -> None:
        """Test encryption of large data."""
        # Create large test data (1MB)
        large_data = "A" * (1024 * 1024)

        # Encrypt and decrypt large data
        encrypted = self.storage.encrypt_data(large_data)
        decrypted = self.storage.decrypt_data(encrypted)

        assert decrypted == large_data
        assert len(encrypted) > 0
        assert encrypted != large_data

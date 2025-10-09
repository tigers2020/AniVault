"""Security-focused tests for encryption module.

Failure-First Testing for token validation.
"""

import pytest
from cryptography.fernet import InvalidToken

from anivault.security.encryption import EncryptionService
from anivault.shared.errors import ErrorCode, SecurityError


class TestTokenValidationFailures:
    """토큰 검증 실패 케이스 테스트 (Failure-First)."""

    def setup_method(self):
        """각 테스트 전에 EncryptionService 인스턴스 생성."""
        test_pin = "test_pin_1234"
        test_salt = b"test_salt_16bytes"
        self.service = EncryptionService(pin=test_pin, salt=test_salt)

    def test_validate_token_invalid(self):
        """잘못된 토큰일 때 SecurityError 발생 테스트."""
        # Given: 잘못된 토큰
        invalid_token = "invalid_token_format_12345"

        # When & Then: SecurityError 발생해야 함
        with pytest.raises(SecurityError) as exc_info:
            self.service.validate_token(invalid_token)

        assert exc_info.value.code == ErrorCode.INVALID_TOKEN
        assert "invalid" in str(exc_info.value.message).lower()

    def test_validate_token_malformed(self):
        """형식이 잘못된 토큰일 때 SecurityError 발생 테스트."""
        # Given: 형식이 완전히 잘못된 토큰
        malformed_token = "not-a-fernet-token"

        # When & Then: SecurityError 발생해야 함
        with pytest.raises(SecurityError) as exc_info:
            self.service.validate_token(malformed_token)

        assert exc_info.value.code == ErrorCode.INVALID_TOKEN

    def test_validate_token_empty(self):
        """빈 토큰일 때 SecurityError 발생 테스트."""
        # Given: 빈 토큰
        empty_token = ""

        # When & Then: SecurityError 발생해야 함
        with pytest.raises(SecurityError) as exc_info:
            self.service.validate_token(empty_token)

        assert exc_info.value.code == ErrorCode.INVALID_TOKEN

    def test_validate_token_success(self):
        """유효한 토큰 검증 성공 테스트."""
        # Given: 유효한 토큰 생성
        test_data = "test_secret_data"
        valid_token = self.service.encrypt(test_data)

        # When: 토큰 검증 (예외 발생하지 않아야 함)
        self.service.validate_token(valid_token)

        # Then: 정상적으로 복호화 가능
        decrypted = self.service.decrypt(valid_token)
        assert decrypted == test_data

    def test_validate_token_from_different_key(self):
        """다른 키로 생성된 토큰일 때 SecurityError 발생 테스트."""
        # Given: 다른 EncryptionService로 생성된 토큰
        other_pin = "different_pin_5678"
        other_salt = b"different_salt16"
        other_service = EncryptionService(pin=other_pin, salt=other_salt)
        other_token = other_service.encrypt("test_data")

        # When & Then: 현재 service로 검증 시 SecurityError
        with pytest.raises(SecurityError) as exc_info:
            self.service.validate_token(other_token)

        assert exc_info.value.code == ErrorCode.INVALID_TOKEN


class TestEncryptionServiceSecurity:
    """암호화 서비스 보안 테스트."""

    def setup_method(self):
        """각 테스트 전에 EncryptionService 인스턴스 생성."""
        test_pin = "test_pin_1234"
        test_salt = b"test_salt_16bytes"
        self.service = EncryptionService(pin=test_pin, salt=test_salt)

    def test_encrypt_decrypt_roundtrip(self):
        """암호화-복호화 왕복 테스트."""
        # Given
        plaintext = "sensitive_data_12345"

        # When
        encrypted = self.service.encrypt(plaintext)
        decrypted = self.service.decrypt(encrypted)

        # Then
        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_produces_different_tokens(self):
        """동일한 데이터를 암호화해도 다른 토큰 생성 (nonce 사용)."""
        # Given
        plaintext = "same_data"

        # When
        token1 = self.service.encrypt(plaintext)
        token2 = self.service.encrypt(plaintext)

        # Then: 토큰은 다르지만 복호화하면 동일
        assert token1 != token2
        assert self.service.decrypt(token1) == plaintext
        assert self.service.decrypt(token2) == plaintext

# AniVault Security Module

This module provides core encryption and security functionality for AniVault's secure keyring system.

## Features

- **PIN-based Encryption**: Uses PBKDF2-HMAC-SHA256 with 600,000 iterations for strong key derivation
- **Fernet Symmetric Encryption**: Industry-standard authenticated encryption
- **Secure Salt Generation**: Cryptographically secure random salt generation
- **Comprehensive Error Handling**: Structured error handling with context preservation
- **Type Safety**: Full type hints and validation

## Usage

### Basic Encryption

```python
from anivault.security import EncryptionService, DecryptionError
import os

# Generate a secure salt
salt = EncryptionService.generate_salt()

# Create encryption service with user PIN
service = EncryptionService("user_pin_123", salt)

# Encrypt sensitive data
api_key = "your-secret-api-key"
encrypted_token = service.encrypt(api_key)

# Decrypt when needed
try:
    decrypted_key = service.decrypt(encrypted_token)
    print(f"Decrypted: {decrypted_key}")
except DecryptionError as e:
    print(f"Decryption failed: {e}")
```

### Token Validation

```python
# Check if a token is valid without decrypting
try:
    service.validate_token(encrypted_token)
    print("Token is valid")
except SecurityError:
    print("Token is invalid or tampered")
```

## Security Features

- **Strong Key Derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations
- **Authenticated Encryption**: Fernet provides both encryption and authentication
- **Salt-based Security**: Each encryption uses a unique salt
- **Error Handling**: Secure error handling that doesn't leak sensitive information

## Error Handling

The module provides structured error handling:

- `DecryptionError`: Raised when decryption fails due to invalid token or wrong key
- `ApplicationError`: Raised for other errors with full context information

All errors include operation context for debugging while preserving security.

## Testing

The module includes comprehensive unit tests covering:

- Key derivation determinism and security
- Encryption/decryption roundtrip
- Error handling for invalid inputs
- Edge cases (empty strings, Unicode, large data)
- Security properties (isolation between different PINs)
- Fernet compatibility

Run tests with:
```bash
pytest tests/security/test_encryption.py -v
```

## Security Considerations

1. **PIN Strength**: Use strong PINs (minimum 8 characters, mixed case, numbers)
2. **Salt Storage**: Store salts securely and never reuse them
3. **Key Management**: Keys are derived from PINs and salts, never stored directly
4. **Token Handling**: Encrypted tokens should be treated as sensitive data
5. **Error Information**: Error messages don't leak sensitive information

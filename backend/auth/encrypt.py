"""
Encrypt / decrypt Canvas API tokens before storing in Supabase.
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).

Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Set as ENCRYPTION_KEY env var.
"""

import base64
from cryptography.fernet import Fernet, InvalidToken
from config import config


def _get_fernet() -> Fernet:
    key = config.ENCRYPTION_KEY
    if not key:
        # Dev fallback — generate a stable key from JWT_SECRET
        # NOT suitable for production
        import hashlib
        raw = hashlib.sha256(config.JWT_SECRET.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a Canvas API token for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored Canvas API token."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt token — key mismatch or corrupted data")

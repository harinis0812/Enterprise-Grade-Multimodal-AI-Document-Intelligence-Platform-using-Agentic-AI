from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import settings

_fernet_instance: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """
    Returns the singleton Fernet cipher instance configured with DOCUMENT_ENCRYPTION_KEY.
    """
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.DOCUMENT_ENCRYPTION_KEY.strip()
        _fernet_instance = Fernet(key.encode("utf-8"))
    return _fernet_instance


def reset_fernet_instance():
    """Resets the cached Fernet instance (useful in tests when switching keys)."""
    global _fernet_instance
    _fernet_instance = None


def is_encrypted(value: Optional[str]) -> bool:
    """
    Checks if the given string appears to be a Fernet-encrypted ciphertext token.
    Fernet tokens begin with 'gAAAAA' (base64 for version 0x80 + timestamp prefix).
    """
    if not value or not isinstance(value, str):
        return False
    return value.startswith("gAAAAA") and len(value) >= 50


def encrypt_text(value: Optional[str]) -> Optional[str]:
    """
    Encrypts a plaintext string using Fernet authenticated encryption (AES-128-CBC + HMAC-SHA256).
    Idempotent: if already encrypted, returns the value as-is to prevent double-encryption.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return value
    if is_encrypted(value):
        return value

    cipher = get_fernet()
    encrypted_bytes = cipher.encrypt(value.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_text(value: Optional[str]) -> Optional[str]:
    """
    Decrypts a Fernet ciphertext string into plaintext.
    Backward-compatible: if the string is not encrypted, returns the value as-is.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return value
    if not is_encrypted(value):
        return value

    try:
        cipher = get_fernet()
        decrypted_bytes = cipher.decrypt(value.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        # If decryption fails (e.g. key mismatch or corrupt token), return original safely
        return value
    except Exception:
        return value

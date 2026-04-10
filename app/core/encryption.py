"""Fernet-based field-level encryption for secrets at rest."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import EncryptionError

__all__ = ["SecretEncryption"]


class SecretEncryption:
    """Encrypts/decrypts secret fields using Fernet (AES-128-CBC + HMAC-SHA256).

    Used for: user API keys, MCP server env vars, tool auth configs.
    """

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError) as exc:
            raise EncryptionError(f"Invalid ENCRYPTION_KEY: {exc}") from exc

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string. Returns a base64 Fernet token."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Fernet token back to plaintext."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise EncryptionError("Decryption failed — token is invalid or tampered") from exc

    def encrypt_dict_values(self, data: dict[str, str]) -> dict[str, str]:
        """Encrypt all values in a dict, preserving keys as plaintext."""
        return {key: self.encrypt(value) for key, value in data.items()}

    def decrypt_dict_values(self, data: dict[str, str]) -> dict[str, str]:
        """Decrypt all values in a dict."""
        return {key: self.decrypt(value) for key, value in data.items()}

    def mask_secret(self, plaintext: str, visible_prefix: int = 8) -> str:
        """Return a masked version of a secret for safe display in API responses.

        Examples:
            mask_secret("sk-ant-abc123xyz789") -> "sk-ant-a...****"
            mask_secret("short") -> "****"
            mask_secret("") -> "****"
        """
        mask = "****"
        if len(plaintext) <= visible_prefix:
            return mask
        return plaintext[:visible_prefix] + "..." + mask

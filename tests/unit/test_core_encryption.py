"""Tests for app.core.encryption — Fernet encrypt/decrypt, dict operations, masking."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import SecretEncryption
from app.core.exceptions import EncryptionError

KEY = Fernet.generate_key().decode()


@pytest.fixture
def enc() -> SecretEncryption:
    return SecretEncryption(KEY)


class TestEncryptDecrypt:
    def test_round_trip(self, enc):
        plaintext = "my-secret-api-key"
        encrypted = enc.encrypt(plaintext)
        assert encrypted != plaintext
        assert enc.decrypt(encrypted) == plaintext

    def test_encrypted_is_string(self, enc):
        result = enc.encrypt("test")
        assert isinstance(result, str)

    def test_different_encryptions_differ(self, enc):
        """Fernet uses random IV so same plaintext produces different ciphertext."""
        a = enc.encrypt("same")
        b = enc.encrypt("same")
        assert a != b

    def test_decrypt_tampered_raises(self, enc):
        encrypted = enc.encrypt("test")
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(EncryptionError):
            enc.decrypt(tampered)

    def test_decrypt_garbage_raises(self, enc):
        with pytest.raises(EncryptionError):
            enc.decrypt("not-valid-fernet-token")

    def test_empty_string(self, enc):
        encrypted = enc.encrypt("")
        assert enc.decrypt(encrypted) == ""


class TestDictOperations:
    def test_encrypt_decrypt_dict_round_trip(self, enc):
        original = {"OPENAI_API_KEY": "sk-123", "ANTHROPIC_API_KEY": "sk-ant-456"}
        encrypted = enc.encrypt_dict_values(original)

        # All values should be encrypted (different from originals)
        for key in original:
            assert encrypted[key] != original[key]

        # Round-trip
        decrypted = enc.decrypt_dict_values(encrypted)
        assert decrypted == original

    def test_empty_dict(self, enc):
        assert enc.encrypt_dict_values({}) == {}
        assert enc.decrypt_dict_values({}) == {}

    def test_keys_preserved(self, enc):
        original = {"a": "1", "b": "2"}
        encrypted = enc.encrypt_dict_values(original)
        assert set(encrypted.keys()) == {"a", "b"}


class TestMaskSecret:
    def test_short_secret_fully_masked(self, enc):
        result = enc.mask_secret("abc")
        assert result == "****"

    def test_long_secret_partially_visible(self, enc):
        result = enc.mask_secret("sk-1234567890")
        assert result.startswith("sk-1")
        assert result.endswith("****")

    def test_empty_string(self, enc):
        result = enc.mask_secret("")
        assert result == "****"


class TestInvalidKey:
    def test_invalid_key_raises(self):
        with pytest.raises(Exception):
            SecretEncryption("not-a-valid-fernet-key")

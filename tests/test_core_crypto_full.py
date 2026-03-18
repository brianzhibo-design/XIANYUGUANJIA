"""
Test suite for core crypto module.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.core.crypto import encrypt, decrypt, generate_key, get_or_create_key


class TestCryptoEncryptDecrypt:
    """Tests for encryption and decryption functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt/decrypt roundtrip works correctly."""
        original = "test_secret_data"
        encrypted = encrypt(original)
        assert encrypted != original
        assert isinstance(encrypted, str)

        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        encrypted = encrypt("")
        decrypted = decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_unicode(self):
        """Test encryption of unicode characters."""
        original = "中文测试 🎉 émojis"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_long_string(self):
        """Test encryption of long string."""
        original = "A" * 10000
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_different_inputs_produce_different_outputs(self):
        """Test that different inputs produce different encrypted outputs."""
        encrypted1 = encrypt("data1")
        encrypted2 = encrypt("data2")
        assert encrypted1 != encrypted2

    def test_same_input_produces_different_outputs(self):
        """Test that same input produces different encrypted outputs (with different IV)."""
        encrypted1 = encrypt("same_data")
        encrypted2 = encrypt("same_data")
        assert encrypted1 != encrypted2


class TestCryptoKeyManagement:
    """Tests for key management functions."""

    def test_generate_key(self):
        """Test key generation."""
        key = generate_key()
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_get_or_create_key_creates_new_key(self):
        """Test that get_or_create_key creates a new key if none exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / ".encryption_key"

            key = get_or_create_key(str(key_file))
            assert isinstance(key, bytes)
            assert key_file.exists()

    def test_get_or_create_key_reads_existing_key(self):
        """Test that get_or_create_key reads existing key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / ".encryption_key"

            key1 = get_or_create_key(str(key_file))
            key2 = get_or_create_key(str(key_file))

            assert key1 == key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

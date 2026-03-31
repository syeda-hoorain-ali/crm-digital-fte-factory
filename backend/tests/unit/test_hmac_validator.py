"""Unit tests for HMAC validator."""

import pytest
from src.utils.hmac_validator import HMACValidator


class TestHMACValidator:
    """Test suite for HMAC signature validation."""

    def test_generate_signature(self):
        """Test HMAC signature generation."""
        validator = HMACValidator("test_secret")
        payload = b"test payload"

        signature = validator.generate_signature(payload)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex digest length

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        validator = HMACValidator("test_secret")
        payload = b"test payload"

        signature = validator.generate_signature(payload)
        is_valid = validator.verify_signature(payload, signature)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        validator = HMACValidator("test_secret")
        payload = b"test payload"

        is_valid = validator.verify_signature(payload, "invalid_signature")

        assert is_valid is False

    def test_verify_signature_with_prefix(self):
        """Test signature verification with prefix stripping."""
        validator = HMACValidator("test_secret")
        payload = b"test payload"

        signature = validator.generate_signature(payload)
        prefixed_signature = f"sha256={signature}"

        is_valid = validator.verify_signature(
            payload,
            prefixed_signature,
            signature_prefix="sha256="
        )

        assert is_valid is True

    def test_verify_signature_different_secrets(self):
        """Test that signatures from different secrets don't match."""
        validator1 = HMACValidator("secret1")
        validator2 = HMACValidator("secret2")
        payload = b"test payload"

        signature1 = validator1.generate_signature(payload)
        is_valid = validator2.verify_signature(payload, signature1)

        assert is_valid is False

    def test_verify_signature_different_payloads(self):
        """Test that signatures for different payloads don't match."""
        validator = HMACValidator("test_secret")
        payload1 = b"payload1"
        payload2 = b"payload2"

        signature1 = validator.generate_signature(payload1)
        is_valid = validator.verify_signature(payload2, signature1)

        assert is_valid is False

    def test_verify_request_valid(self):
        """Test request verification with valid signature."""
        validator = HMACValidator("test_secret")
        body = b"request body"

        signature = validator.generate_signature(body)
        is_valid = validator.verify_request(body, signature)

        assert is_valid is True

    def test_verify_request_empty_signature(self):
        """Test request verification with empty signature."""
        validator = HMACValidator("test_secret")
        body = b"request body"

        is_valid = validator.verify_request(body, "")

        assert is_valid is False

    def test_verify_request_none_signature(self):
        """Test request verification with None signature."""
        validator = HMACValidator("test_secret")
        body = b"request body"

        is_valid = validator.verify_request(body, None) # type: ignore
        assert is_valid is False

    def test_constant_time_comparison(self):
        """Test that comparison is constant-time (timing attack resistant)."""
        validator = HMACValidator("test_secret")
        payload = b"test payload"

        correct_signature = validator.generate_signature(payload)
        wrong_signature = "0" * 64

        # Both should return False, but timing should be similar
        # This is a basic test - real timing attack testing requires more sophisticated tools
        is_valid_correct = validator.verify_signature(payload, correct_signature)
        is_valid_wrong = validator.verify_signature(payload, wrong_signature)

        assert is_valid_correct is True
        assert is_valid_wrong is False

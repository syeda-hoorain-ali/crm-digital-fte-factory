"""HMAC signature verification for webhook authentication."""

import hmac
import hashlib
from typing import Optional


class HMACValidator:
    """HMAC signature validator with constant-time comparison."""

    def __init__(self, secret: str):
        """Initialize validator with webhook secret.

        Args:
            secret: Webhook secret key for HMAC generation
        """
        self.secret = secret.encode('utf-8')

    def generate_signature(self, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature for payload.

        Args:
            payload: Raw payload bytes

        Returns:
            Hex-encoded HMAC signature
        """
        signature = hmac.new(
            self.secret,
            payload,
            hashlib.sha256
        )
        return signature.hexdigest()

    def verify_signature(
        self,
        payload: bytes,
        provided_signature: str,
        signature_prefix: Optional[str] = None
    ) -> bool:
        """Verify HMAC signature using constant-time comparison.

        Args:
            payload: Raw payload bytes
            provided_signature: Signature from webhook header
            signature_prefix: Optional prefix to strip (e.g., "sha256=")

        Returns:
            True if signature is valid, False otherwise
        """
        # Strip prefix if provided
        if signature_prefix and provided_signature.startswith(signature_prefix):
            provided_signature = provided_signature[len(signature_prefix):]

        # Generate expected signature
        expected_signature = self.generate_signature(payload)

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, provided_signature)

    def verify_request(
        self,
        body: bytes,
        signature_header: str,
        signature_prefix: Optional[str] = None
    ) -> bool:
        """Verify webhook request signature.

        Args:
            body: Request body bytes
            signature_header: Signature from request header
            signature_prefix: Optional prefix to strip

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header:
            return False

        return self.verify_signature(body, signature_header, signature_prefix)

"""Email parsing utilities for Gmail messages."""

import base64
import email
import logging
from email.message import EmailMessage
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailParser:
    """Parser for Gmail API message format."""

    @staticmethod
    def parse_gmail_message(gmail_message: dict[str, Any]) -> dict[str, Any]:
        """Parse Gmail API message format into structured data.

        Args:
            gmail_message: Raw Gmail API message response

        Returns:
            Parsed message data with headers, body, and metadata
        """
        headers = EmailParser._extract_headers(gmail_message)
        body = EmailParser._extract_body(gmail_message)
        attachments = EmailParser._extract_attachments(gmail_message)

        return {
            'message_id': gmail_message['id'],
            'thread_id': gmail_message.get('threadId'),
            'from': headers.get('From'),
            'to': headers.get('To'),
            'subject': headers.get('Subject'),
            'date': headers.get('Date'),
            'in_reply_to': headers.get('In-Reply-To'),
            'references': headers.get('References'),
            'message_id_header': headers.get('Message-ID'),
            'body': body,
            'attachments': attachments,
            'labels': gmail_message.get('labelIds', []),
            'snippet': gmail_message.get('snippet', ''),
            'internal_date': gmail_message.get('internalDate')
        }

    @staticmethod
    def _extract_headers(gmail_message: dict[str, Any]) -> dict[str, str]:
        """Extract email headers from Gmail message.

        Args:
            gmail_message: Raw Gmail API message

        Returns:
            Dictionary of header name to value
        """
        headers = {}
        payload = gmail_message.get('payload', {})

        for header in payload.get('headers', []):
            name = header.get('name')
            value = header.get('value')
            if name and value:
                headers[name] = value

        return headers

    @staticmethod
    def _extract_body(gmail_message: dict[str, Any]) -> str:
        """Extract email body from Gmail message.

        Args:
            gmail_message: Raw Gmail API message

        Returns:
            Email body text (plain text preferred, HTML as fallback)
        """
        payload = gmail_message.get('payload', {})

        # Try to get plain text body first
        body = EmailParser._get_body_from_parts(payload, 'text/plain')

        # Fallback to HTML if no plain text
        if not body:
            body = EmailParser._get_body_from_parts(payload, 'text/html')

        # Last resort: use snippet
        if not body:
            body = gmail_message.get('snippet', '')

        return body

    @staticmethod
    def _get_body_from_parts(payload: dict[str, Any], mime_type: str) -> str:
        """Recursively extract body from message parts.

        Args:
            payload: Gmail message payload
            mime_type: MIME type to extract (text/plain or text/html)

        Returns:
            Decoded body text or empty string
        """
        # Check if this part matches the desired MIME type
        if payload.get('mimeType') == mime_type:
            body_data = payload.get('body', {}).get('data')
            if body_data:
                return EmailParser._decode_base64(body_data)

        # Recursively check parts
        for part in payload.get('parts', []):
            body = EmailParser._get_body_from_parts(part, mime_type)
            if body:
                return body

        return ''

    @staticmethod
    def _decode_base64(data: str) -> str:
        """Decode base64url-encoded data.

        Args:
            data: Base64url-encoded string

        Returns:
            Decoded UTF-8 string
        """
        try:
            # Gmail uses base64url encoding (URL-safe)
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Failed to decode base64 data: {e}")
            return ''

    @staticmethod
    def _extract_attachments(gmail_message: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract attachment metadata from Gmail message.

        Args:
            gmail_message: Raw Gmail API message

        Returns:
            List of attachment metadata dictionaries
        """
        attachments = []
        payload = gmail_message.get('payload', {})

        EmailParser._collect_attachments(payload, attachments)

        return attachments

    @staticmethod
    def _collect_attachments(
        part: dict[str, Any],
        attachments: list[dict[str, Any]]
    ) -> None:
        """Recursively collect attachments from message parts.

        Args:
            part: Message part to check
            attachments: List to append attachment metadata to
        """
        # Check if this part is an attachment
        filename = part.get('filename')
        body = part.get('body', {})
        attachment_id = body.get('attachmentId')

        if filename and attachment_id:
            attachments.append({
                'filename': filename,
                'mime_type': part.get('mimeType'),
                'size': body.get('size', 0),
                'attachment_id': attachment_id
            })

        # Recursively check nested parts
        for nested_part in part.get('parts', []):
            EmailParser._collect_attachments(nested_part, attachments)

    @staticmethod
    def detect_thread_info(parsed_message: dict[str, Any]) -> dict[str, Any]:
        """Detect email threading information.

        Args:
            parsed_message: Parsed email message

        Returns:
            Threading information with parent detection
        """
        in_reply_to = parsed_message.get('in_reply_to')
        references = parsed_message.get('references')

        # Parse references header (space or comma separated)
        reference_ids = []
        if references:
            # Split by whitespace and commas, filter empty strings
            reference_ids = [
                ref.strip()
                for ref in references.replace(',', ' ').split()
                if ref.strip()
            ]

        # Determine if this is a reply
        is_reply = bool(in_reply_to or reference_ids)

        # Parent message ID is the In-Reply-To or last reference
        parent_message_id = None
        if in_reply_to:
            parent_message_id = in_reply_to.strip('<>')
        elif reference_ids:
            parent_message_id = reference_ids[-1].strip('<>')

        return {
            'is_reply': is_reply,
            'parent_message_id': parent_message_id,
            'in_reply_to': in_reply_to,
            'references': reference_ids,
            'thread_id': parsed_message.get('thread_id')
        }

    @staticmethod
    def extract_sender_info(parsed_message: dict[str, Any]) -> dict[str, str | None]:
        """Extract sender email and name from From header.

        Args:
            parsed_message: Parsed email message

        Returns:
            Dictionary with email and name
        """
        from_header = parsed_message.get('from', '')

        try:
            # Parse email address using email library
            msg = EmailMessage()
            msg['From'] = from_header

            addresses = msg.get('From', '').addresses
            if addresses:
                addr = addresses[0]
                return {
                    'email': addr.addr_spec,
                    'name': addr.display_name or None
                }
        except Exception as e:
            logger.warning(f"Failed to parse From header: {e}")

        # Fallback: simple regex-like extraction
        email_addr = EmailParser._extract_email_simple(from_header)
        name = EmailParser._extract_name_simple(from_header)

        return {
            'email': email_addr,
            'name': name
        }

    @staticmethod
    def _extract_email_simple(from_header: str) -> str | None:
        """Simple email extraction from From header.

        Args:
            from_header: From header value

        Returns:
            Email address or None
        """
        # Look for email in angle brackets
        if '<' in from_header and '>' in from_header:
            start = from_header.index('<') + 1
            end = from_header.index('>')
            return from_header[start:end].strip()

        # Assume entire header is email if no brackets
        if '@' in from_header:
            return from_header.strip()

        return None

    @staticmethod
    def _extract_name_simple(from_header: str) -> str | None:
        """Simple name extraction from From header.

        Args:
            from_header: From header value

        Returns:
            Display name or None
        """
        # Name is before angle bracket
        if '<' in from_header:
            name = from_header[:from_header.index('<')].strip()
            # Remove quotes if present
            name = name.strip('"').strip("'")
            return name if name else None

        return None

    @staticmethod
    def parse_timestamp(date_header: str | None) -> datetime | None:
        """Parse email Date header to datetime.

        Args:
            date_header: Date header value

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_header:
            return None

        try:
            # Use email.utils to parse RFC 2822 date
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_header)
        except Exception as e:
            logger.warning(f"Failed to parse date header '{date_header}': {e}")
            return None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for storage
        """
        import os
        import re

        # Remove any directory components
        filename = os.path.basename(filename)

        # Remove any remaining path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Replace any remaining dangerous characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)

        # Ensure filename is not empty
        if not filename:
            filename = 'attachment'

        # Limit length to 255 characters (common filesystem limit)
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            max_name_len = 255 - len(ext)
            filename = name[:max_name_len] + ext

        return filename

"""Unit tests for email parser."""

import pytest
from datetime import datetime

from src.channels.email_parser import EmailParser


class TestEmailParser:
    """Test suite for EmailParser."""

    def test_parse_gmail_message_basic(self):
        """Test parsing basic Gmail message."""
        gmail_message = {
            'id': 'msg123',
            'threadId': 'thread456',
            'labelIds': ['INBOX'],
            'snippet': 'Test message snippet',
            'internalDate': '1234567890000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'To', 'value': 'support@company.com'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
                    {'name': 'Message-ID', 'value': '<msg123@mail.gmail.com>'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': 'VGVzdCBtZXNzYWdlIGJvZHk='  # Base64: "Test message body"
                }
            }
        }

        parsed = EmailParser.parse_gmail_message(gmail_message)

        assert parsed['message_id'] == 'msg123'
        assert parsed['thread_id'] == 'thread456'
        assert parsed['from'] == 'John Doe <john@example.com>'
        assert parsed['to'] == 'support@company.com'
        assert parsed['subject'] == 'Test Subject'
        assert parsed['body'] == 'Test message body'
        assert parsed['snippet'] == 'Test message snippet'
        assert parsed['labels'] == ['INBOX']

    def test_parse_gmail_message_with_parts(self):
        """Test parsing multipart Gmail message."""
        gmail_message = {
            'id': 'msg123',
            'threadId': 'thread456',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'Subject', 'value': 'Multipart Test'}
                ],
                'mimeType': 'multipart/alternative',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': 'UGxhaW4gdGV4dCBib2R5'  # "Plain text body"
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': 'PGh0bWw-SFRNTCBib2R5PC9odG1sPg=='  # "<html>HTML body</html>"
                        }
                    }
                ]
            }
        }

        parsed = EmailParser.parse_gmail_message(gmail_message)

        # Should prefer plain text over HTML
        assert parsed['body'] == 'Plain text body'

    def test_extract_headers(self):
        """Test header extraction."""
        gmail_message = {
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'In-Reply-To', 'value': '<parent@example.com>'},
                    {'name': 'References', 'value': '<ref1@example.com> <ref2@example.com>'}
                ]
            }
        }

        headers = EmailParser._extract_headers(gmail_message)

        assert headers['From'] == 'sender@example.com'
        assert headers['To'] == 'recipient@example.com'
        assert headers['Subject'] == 'Test Subject'
        assert headers['In-Reply-To'] == '<parent@example.com>'
        assert headers['References'] == '<ref1@example.com> <ref2@example.com>'

    def test_decode_base64(self):
        """Test base64url decoding."""
        # Standard base64url encoding
        encoded = 'SGVsbG8gV29ybGQh'  # "Hello World!"
        decoded = EmailParser._decode_base64(encoded)
        assert decoded == 'Hello World!'

        # With URL-safe characters
        encoded = 'SGVsbG8gV29ybGQh'
        decoded = EmailParser._decode_base64(encoded)
        assert decoded == 'Hello World!'

    def test_extract_attachments(self):
        """Test attachment extraction."""
        gmail_message = {
            'payload': {
                'parts': [
                    {
                        'filename': 'document.pdf',
                        'mimeType': 'application/pdf',
                        'body': {
                            'attachmentId': 'attach123',
                            'size': 12345
                        }
                    },
                    {
                        'filename': 'image.png',
                        'mimeType': 'image/png',
                        'body': {
                            'attachmentId': 'attach456',
                            'size': 67890
                        }
                    }
                ]
            }
        }

        attachments = EmailParser._extract_attachments(gmail_message)

        assert len(attachments) == 2
        assert attachments[0]['filename'] == 'document.pdf'
        assert attachments[0]['mime_type'] == 'application/pdf'
        assert attachments[0]['attachment_id'] == 'attach123'
        assert attachments[0]['size'] == 12345
        assert attachments[1]['filename'] == 'image.png'

    def test_detect_thread_info_new_message(self):
        """Test thread detection for new message."""
        parsed_message = {
            'in_reply_to': None,
            'references': None,
            'thread_id': 'thread123'
        }

        thread_info = EmailParser.detect_thread_info(parsed_message)

        assert thread_info['is_reply'] is False
        assert thread_info['parent_message_id'] is None
        assert thread_info['thread_id'] == 'thread123'

    def test_detect_thread_info_reply(self):
        """Test thread detection for reply."""
        parsed_message = {
            'in_reply_to': '<parent@example.com>',
            'references': '<ref1@example.com> <ref2@example.com>',
            'thread_id': 'thread123'
        }

        thread_info = EmailParser.detect_thread_info(parsed_message)

        assert thread_info['is_reply'] is True
        assert thread_info['parent_message_id'] == 'parent@example.com'
        assert thread_info['in_reply_to'] == '<parent@example.com>'
        assert len(thread_info['references']) == 2

    def test_detect_thread_info_references_only(self):
        """Test thread detection with only references header."""
        parsed_message = {
            'in_reply_to': None,
            'references': '<ref1@example.com>, <ref2@example.com>',
            'thread_id': 'thread123'
        }

        thread_info = EmailParser.detect_thread_info(parsed_message)

        assert thread_info['is_reply'] is True
        assert thread_info['parent_message_id'] == 'ref2@example.com'
        assert len(thread_info['references']) == 2

    def test_extract_sender_info_with_name(self):
        """Test sender extraction with display name."""
        parsed_message = {
            'from': 'John Doe <john@example.com>'
        }

        sender_info = EmailParser.extract_sender_info(parsed_message)

        assert sender_info['email'] == 'john@example.com'
        assert sender_info['name'] == 'John Doe'

    def test_extract_sender_info_email_only(self):
        """Test sender extraction with email only."""
        parsed_message = {
            'from': 'john@example.com'
        }

        sender_info = EmailParser.extract_sender_info(parsed_message)

        assert sender_info['email'] == 'john@example.com'
        assert sender_info['name'] is None

    def test_extract_sender_info_quoted_name(self):
        """Test sender extraction with quoted display name."""
        parsed_message = {
            'from': '"John Doe" <john@example.com>'
        }

        sender_info = EmailParser.extract_sender_info(parsed_message)

        assert sender_info['email'] == 'john@example.com'
        assert sender_info['name'] == 'John Doe'

    def test_parse_timestamp_valid(self):
        """Test timestamp parsing with valid date."""
        date_header = 'Mon, 1 Jan 2024 12:00:00 +0000'

        timestamp = EmailParser.parse_timestamp(date_header)

        assert timestamp is not None
        assert isinstance(timestamp, datetime)
        assert timestamp.year == 2024
        assert timestamp.month == 1
        assert timestamp.day == 1

    def test_parse_timestamp_invalid(self):
        """Test timestamp parsing with invalid date."""
        date_header = 'Invalid Date'

        timestamp = EmailParser.parse_timestamp(date_header)

        assert timestamp is None

    def test_parse_timestamp_none(self):
        """Test timestamp parsing with None."""
        timestamp = EmailParser.parse_timestamp(None)

        assert timestamp is None

    def test_extract_body_fallback_to_snippet(self):
        """Test body extraction falls back to snippet."""
        gmail_message = {
            'snippet': 'This is the snippet',
            'payload': {
                'mimeType': 'text/plain',
                'body': {}  # No data
            }
        }

        body = EmailParser._extract_body(gmail_message)

        assert body == 'This is the snippet'

    def test_extract_body_nested_parts(self):
        """Test body extraction from nested parts."""
        gmail_message = {
            'payload': {
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'multipart/alternative',
                        'parts': [
                            {
                                'mimeType': 'text/plain',
                                'body': {
                                    'data': 'TmVzdGVkIHBsYWluIHRleHQ='  # "Nested plain text"
                                }
                            }
                        ]
                    }
                ]
            }
        }

        body = EmailParser._extract_body(gmail_message)

        assert body == 'Nested plain text'

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        parser = EmailParser()

        # Path traversal attempt
        safe = parser._sanitize_filename('../../../etc/passwd')
        assert '..' not in safe
        assert '/' not in safe

        # Windows path separators
        safe = parser._sanitize_filename('..\\..\\windows\\system32')
        assert '\\' not in safe

        # Long filename
        long_name = 'a' * 300 + '.txt'
        safe = parser._sanitize_filename(long_name)
        assert len(safe) <= 255
        assert safe.endswith('.txt')

    def test_collect_attachments_recursive(self):
        """Test recursive attachment collection."""
        part = {
            'parts': [
                {
                    'filename': 'doc1.pdf',
                    'mimeType': 'application/pdf',
                    'body': {
                        'attachmentId': 'attach1',
                        'size': 1000
                    }
                },
                {
                    'parts': [
                        {
                            'filename': 'doc2.pdf',
                            'mimeType': 'application/pdf',
                            'body': {
                                'attachmentId': 'attach2',
                                'size': 2000
                            }
                        }
                    ]
                }
            ]
        }

        attachments = []
        EmailParser._collect_attachments(part, attachments)

        assert len(attachments) == 2
        assert attachments[0]['filename'] == 'doc1.pdf'
        assert attachments[1]['filename'] == 'doc2.pdf'

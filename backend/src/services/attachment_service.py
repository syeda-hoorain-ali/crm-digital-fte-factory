"""Attachment handling service for email messages."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from ..channels.gmail_client import GmailClient
from ..database.models import MessageAttachment

logger = logging.getLogger(__name__)

# Allowed file types (MIME types)
ALLOWED_MIME_TYPES = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
    # Archives
    'application/zip',
    'application/x-zip-compressed',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
    'application/gzip',
}

# Blocked file extensions (executables and scripts)
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
    '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
    '.sh', '.bash', '.ps1', '.msi', '.dll', '.so'
}

# Maximum attachment size (10MB)
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB in bytes


class AttachmentService:
    """Service for handling email attachments."""

    def __init__(
        self,
        gmail_client: GmailClient,
        storage_path: str | Path
    ):
        """Initialize attachment service.

        Args:
            gmail_client: Gmail API client for downloading attachments
            storage_path: Base directory for storing attachments
        """
        self.gmail_client = gmail_client
        self.storage_path = Path(storage_path)

        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def process_attachments(
        self,
        message_id: UUID,
        gmail_message_id: str,
        attachments: list[dict[str, Any]]
    ) -> list[MessageAttachment]:
        """Process and store email attachments.

        Args:
            message_id: Database message UUID
            gmail_message_id: Gmail message ID
            attachments: List of attachment metadata from email parser

        Returns:
            List of MessageAttachment models

        Raises:
            ValueError: If attachment validation fails
        """
        processed_attachments = []

        for attachment_meta in attachments:
            try:
                # Validate attachment
                self._validate_attachment(attachment_meta)

                # Download attachment from Gmail
                attachment_data = await self._download_attachment(
                    gmail_message_id,
                    attachment_meta['attachment_id']
                )

                # Calculate checksum
                checksum = self._calculate_checksum(attachment_data)

                # Generate storage path
                storage_path = self._generate_storage_path(
                    message_id,
                    attachment_meta['filename']
                )

                # Save to disk
                await self._save_attachment(storage_path, attachment_data)

                # Create database record
                attachment_record = MessageAttachment(
                    message_id=message_id,
                    filename=attachment_meta['filename'],
                    content_type=attachment_meta['mime_type'],
                    size_bytes=attachment_meta['size'],
                    storage_path=str(storage_path),
                    checksum=checksum,
                    is_malicious=False  # TODO: Add malware scanning
                )

                processed_attachments.append(attachment_record)

                logger.info(
                    f"Processed attachment: {attachment_meta['filename']}",
                    extra={
                        "message_id": str(message_id),
                        "filename": attachment_meta['filename'],
                        "size": attachment_meta['size'],
                        "checksum": checksum
                    }
                )

            except Exception as e:
                logger.error(
                    f"Failed to process attachment: {attachment_meta.get('filename', 'unknown')}",
                    extra={
                        "message_id": str(message_id),
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Continue processing other attachments
                continue

        return processed_attachments

    def _validate_attachment(self, attachment_meta: dict[str, Any]) -> None:
        """Validate attachment size and type.

        Args:
            attachment_meta: Attachment metadata

        Raises:
            ValueError: If validation fails
        """
        filename = attachment_meta.get('filename', '')
        mime_type = attachment_meta.get('mime_type', '')
        size = attachment_meta.get('size', 0)

        # Check size limit
        if size > MAX_ATTACHMENT_SIZE:
            raise ValueError(
                f"Attachment '{filename}' exceeds maximum size of {MAX_ATTACHMENT_SIZE / 1024 / 1024}MB"
            )

        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext in BLOCKED_EXTENSIONS:
            raise ValueError(
                f"Attachment '{filename}' has blocked extension: {file_ext}"
            )

        # Check MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Attachment '{filename}' has disallowed MIME type: {mime_type}",
                extra={"filename": filename, "mime_type": mime_type}
            )
            raise ValueError(
                f"Attachment '{filename}' has disallowed file type: {mime_type}"
            )

    async def _download_attachment(
        self,
        message_id: str,
        attachment_id: str
    ) -> bytes:
        """Download attachment from Gmail API.

        Args:
            message_id: Gmail message ID
            attachment_id: Gmail attachment ID

        Returns:
            Attachment data as bytes

        Raises:
            Exception: If download fails
        """
        if not self.gmail_client.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            attachment = self.gmail_client.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()

            # Decode base64url-encoded data
            import base64
            data = attachment['data']
            file_data = base64.urlsafe_b64decode(data)

            logger.info(
                f"Downloaded attachment from Gmail",
                extra={
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "size": len(file_data)
                }
            )

            return file_data

        except Exception as e:
            logger.error(
                f"Failed to download attachment: {e}",
                extra={
                    "message_id": message_id,
                    "attachment_id": attachment_id
                },
                exc_info=True
            )
            raise

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum of attachment data.

        Args:
            data: Attachment data

        Returns:
            Hex-encoded SHA-256 checksum
        """
        return hashlib.sha256(data).hexdigest()

    def _generate_storage_path(
        self,
        message_id: UUID,
        filename: str
    ) -> Path:
        """Generate storage path for attachment.

        Args:
            message_id: Database message UUID
            filename: Original filename

        Returns:
            Path object for storage location
        """
        # Organize by message ID to avoid directory bloat
        # Structure: storage_path/message_id/filename
        message_dir = self.storage_path / str(message_id)
        message_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename to prevent path traversal
        safe_filename = self._sanitize_filename(filename)

        return message_dir / safe_filename

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path separators and parent directory references
        safe_name = filename.replace('/', '_').replace('\\', '_')
        safe_name = safe_name.replace('..', '_')

        # Limit filename length
        if len(safe_name) > 255:
            # Keep extension
            name_part = safe_name[:240]
            ext_part = Path(safe_name).suffix[:15]
            safe_name = name_part + ext_part

        return safe_name

    async def _save_attachment(
        self,
        storage_path: Path,
        data: bytes
    ) -> None:
        """Save attachment data to disk.

        Args:
            storage_path: Path to save attachment
            data: Attachment data

        Raises:
            Exception: If save fails
        """
        try:
            # Write file atomically using temporary file
            temp_path = storage_path.with_suffix('.tmp')

            with open(temp_path, 'wb') as f:
                f.write(data)

            # Rename to final path (atomic on POSIX systems)
            temp_path.rename(storage_path)

            logger.info(
                f"Saved attachment to disk",
                extra={
                    "path": str(storage_path),
                    "size": len(data)
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to save attachment: {e}",
                extra={"path": str(storage_path)},
                exc_info=True
            )
            # Clean up temporary file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def get_attachment(
        self,
        attachment: MessageAttachment
    ) -> bytes:
        """Retrieve attachment data from storage.

        Args:
            attachment: MessageAttachment model

        Returns:
            Attachment data as bytes

        Raises:
            FileNotFoundError: If attachment file not found
            Exception: If read fails
        """
        if not attachment.storage_path:
            raise ValueError("Attachment has no storage path")

        storage_path = Path(attachment.storage_path)

        if not storage_path.exists():
            raise FileNotFoundError(f"Attachment file not found: {storage_path}")

        try:
            with open(storage_path, 'rb') as f:
                data = f.read()

            # Verify checksum
            if attachment.checksum:
                calculated_checksum = self._calculate_checksum(data)
                if calculated_checksum != attachment.checksum:
                    logger.error(
                        "Attachment checksum mismatch",
                        extra={
                            "attachment_id": str(attachment.id),
                            "expected": attachment.checksum,
                            "calculated": calculated_checksum
                        }
                    )
                    raise ValueError("Attachment checksum verification failed")

            return data

        except Exception as e:
            logger.error(
                f"Failed to read attachment: {e}",
                extra={"attachment_id": str(attachment.id)},
                exc_info=True
            )
            raise

    async def delete_attachment(
        self,
        attachment: MessageAttachment
    ) -> None:
        """Delete attachment from storage.

        Args:
            attachment: MessageAttachment model

        Raises:
            Exception: If deletion fails
        """
        if not attachment.storage_path:
            logger.warning(
                "Attachment has no storage path",
                extra={"attachment_id": str(attachment.id)}
            )
            return

        storage_path = Path(attachment.storage_path)

        if not storage_path.exists():
            logger.warning(
                "Attachment file not found for deletion",
                extra={"path": str(storage_path)}
            )
            return

        try:
            storage_path.unlink()
            logger.info(
                "Deleted attachment from storage",
                extra={
                    "attachment_id": str(attachment.id),
                    "path": str(storage_path)
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to delete attachment: {e}",
                extra={"attachment_id": str(attachment.id)},
                exc_info=True
            )
            raise

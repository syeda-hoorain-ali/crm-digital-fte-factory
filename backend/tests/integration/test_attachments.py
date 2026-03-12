"""Integration tests for attachment handling."""

import pytest
import hashlib
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.attachment_service import AttachmentService, MAX_ATTACHMENT_SIZE
from src.database.models import MessageAttachment


@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    """Create temporary storage directory."""
    storage_path = tmp_path / "attachments"
    storage_path.mkdir()
    return storage_path


@pytest.fixture
def mock_gmail_client() -> MagicMock:
    """Mock Gmail client for testing."""
    client = MagicMock()
    client.service = MagicMock()
    return client


@pytest.fixture
def attachment_service(mock_gmail_client: MagicMock, temp_storage_path: Path) -> AttachmentService:
    """Create attachment service instance."""
    return AttachmentService(
        gmail_client=mock_gmail_client,
        storage_path=temp_storage_path
    )


@pytest.fixture
def sample_attachment_data() -> bytes:
    """Sample attachment data."""
    return b"This is a test PDF file content"


@pytest.fixture
def sample_attachment_meta():
    """Sample attachment metadata."""
    return {
        'filename': 'document.pdf',
        'mime_type': 'application/pdf',
        'size': 1024,
        'attachment_id': 'attach_123'
    }


class TestAttachmentService:
    """Test suite for AttachmentService."""

    @pytest.mark.asyncio
    async def test_process_attachments_success(
        self,
        attachment_service: AttachmentService,
        sample_attachment_data: bytes,
        sample_attachment_meta: dict,
        mock_gmail_client: MagicMock
    ):
        """Test successful attachment processing."""
        message_id = uuid4()

        # Mock Gmail API attachment download
        mock_gmail_client.service.users().messages().attachments().get().execute.return_value = {
            'data': 'VGhpcyBpcyBhIHRlc3QgUERGIGZpbGUgY29udGVudA=='  # Base64 encoded
        }

        attachments = await attachment_service.process_attachments(
            message_id=message_id,
            gmail_message_id='msg_123',
            attachments=[sample_attachment_meta]
        )

        assert len(attachments) == 1
        attachment = attachments[0]
        assert attachment.message_id == message_id
        assert attachment.filename == 'document.pdf'
        assert attachment.content_type == 'application/pdf'
        assert attachment.size_bytes == 1024
        assert attachment.storage_path is not None
        assert attachment.checksum is not None
        assert attachment.is_malicious is False

        # Verify file was saved
        storage_path = Path(attachment.storage_path)
        assert storage_path.exists()
        assert storage_path.read_bytes() == sample_attachment_data

    @pytest.mark.asyncio
    async def test_process_attachments_multiple(
        self,
        attachment_service: AttachmentService,
        mock_gmail_client: MagicMock
    ):
        """Test processing multiple attachments."""
        message_id = uuid4()

        attachments_meta = [
            {
                'filename': 'doc1.pdf',
                'mime_type': 'application/pdf',
                'size': 1024,
                'attachment_id': 'attach_1'
            },
            {
                'filename': 'image.png',
                'mime_type': 'image/png',
                'size': 2048,
                'attachment_id': 'attach_2'
            }
        ]

        # Mock Gmail API responses
        mock_gmail_client.service.users().messages().attachments().get().execute.side_effect = [
            {'data': 'UERGIGNvbnRlbnQ='},  # "PDF content"
            {'data': 'UE5HIGNvbnRlbnQ='}   # "PNG content"
        ]

        attachments = await attachment_service.process_attachments(
            message_id=message_id,
            gmail_message_id='msg_123',
            attachments=attachments_meta
        )

        assert len(attachments) == 2
        assert attachments[0].filename == 'doc1.pdf'
        assert attachments[1].filename == 'image.png'

        # Verify both files saved
        for attachment in attachments:
            assert attachment.storage_path
            storage_path = Path(attachment.storage_path)
            assert storage_path.exists()

    @pytest.mark.asyncio
    async def test_validate_attachment_size_limit(
        self,
        attachment_service: AttachmentService
    ):
        """Test attachment size validation."""
        oversized_meta = {
            'filename': 'large_file.pdf',
            'mime_type': 'application/pdf',
            'size': MAX_ATTACHMENT_SIZE + 1,
            'attachment_id': 'attach_123'
        }

        with pytest.raises(ValueError, match="exceeds maximum size"):
            attachment_service._validate_attachment(oversized_meta)

    @pytest.mark.asyncio
    async def test_validate_attachment_blocked_extension(
        self,
        attachment_service: AttachmentService
    ):
        """Test blocked file extension validation."""
        blocked_meta = {
            'filename': 'malware.exe',
            'mime_type': 'application/x-msdownload',
            'size': 1024,
            'attachment_id': 'attach_123'
        }

        with pytest.raises(ValueError, match="blocked extension"):
            attachment_service._validate_attachment(blocked_meta)

    @pytest.mark.asyncio
    async def test_validate_attachment_disallowed_mime_type(
        self,
        attachment_service: AttachmentService
    ):
        """Test disallowed MIME type validation."""
        disallowed_meta = {
            'filename': 'script.js',
            'mime_type': 'application/javascript',
            'size': 1024,
            'attachment_id': 'attach_123'
        }

        with pytest.raises(ValueError, match="disallowed file type"):
            attachment_service._validate_attachment(disallowed_meta)

    @pytest.mark.asyncio
    async def test_validate_attachment_allowed_types(
        self,
        attachment_service: AttachmentService
    ):
        """Test validation passes for allowed file types."""
        allowed_types = [
            ('document.pdf', 'application/pdf'),
            ('spreadsheet.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('image.png', 'image/png'),
            ('archive.zip', 'application/zip'),
            ('text.txt', 'text/plain')
        ]

        for filename, mime_type in allowed_types:
            meta = {
                'filename': filename,
                'mime_type': mime_type,
                'size': 1024,
                'attachment_id': 'attach_123'
            }
            # Should not raise exception
            attachment_service._validate_attachment(meta)

    @pytest.mark.asyncio
    async def test_calculate_checksum(
        self,
        attachment_service: AttachmentService,
        sample_attachment_data: bytes
    ):
        """Test checksum calculation."""
        checksum = attachment_service._calculate_checksum(sample_attachment_data)

        # Verify it's a valid SHA-256 hex string
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

        # Verify consistency
        checksum2 = attachment_service._calculate_checksum(sample_attachment_data)
        assert checksum == checksum2

        # Verify correctness
        expected = hashlib.sha256(sample_attachment_data).hexdigest()
        assert checksum == expected

    @pytest.mark.asyncio
    async def test_sanitize_filename(
        self,
        attachment_service: AttachmentService
    ):
        """Test filename sanitization."""
        # Path traversal
        safe = attachment_service._sanitize_filename('../../../etc/passwd')
        assert '..' not in safe
        assert '/' not in safe
        assert '\\' not in safe

        # Windows paths
        safe = attachment_service._sanitize_filename('..\\..\\windows\\system32')
        assert '\\' not in safe

        # Normal filename
        safe = attachment_service._sanitize_filename('document.pdf')
        assert safe == 'document.pdf'

        # Long filename
        long_name = 'a' * 300 + '.pdf'
        safe = attachment_service._sanitize_filename(long_name)
        assert len(safe) <= 255
        assert safe.endswith('.pdf')

    @pytest.mark.asyncio
    async def test_generate_storage_path(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path
    ):
        """Test storage path generation."""
        message_id = uuid4()
        filename = 'document.pdf'

        storage_path = attachment_service._generate_storage_path(message_id, filename)

        # Verify path structure
        assert storage_path.parent.name == str(message_id)
        assert storage_path.name == filename
        assert storage_path.parent.parent == temp_storage_path

        # Verify directory created
        assert storage_path.parent.exists()

    @pytest.mark.asyncio
    async def test_save_attachment(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path,
        sample_attachment_data: bytes
    ):
        """Test attachment saving to disk."""
        storage_path = temp_storage_path / "test_file.pdf"

        await attachment_service._save_attachment(storage_path, sample_attachment_data)

        # Verify file exists and content matches
        assert storage_path.exists()
        assert storage_path.read_bytes() == sample_attachment_data

    @pytest.mark.asyncio
    async def test_get_attachment(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path,
        sample_attachment_data: bytes
    ):
        """Test retrieving attachment from storage."""
        message_id = uuid4()
        storage_path = temp_storage_path / str(message_id) / "document.pdf"
        storage_path.parent.mkdir(parents=True)
        storage_path.write_bytes(sample_attachment_data)

        # Create attachment record
        checksum = attachment_service._calculate_checksum(sample_attachment_data)
        attachment = MessageAttachment(
            message_id=message_id,
            filename='document.pdf',
            content_type='application/pdf',
            size_bytes=len(sample_attachment_data),
            storage_path=str(storage_path),
            checksum=checksum
        )

        # Retrieve attachment
        data = await attachment_service.get_attachment(attachment)

        assert data == sample_attachment_data

    @pytest.mark.asyncio
    async def test_get_attachment_checksum_mismatch(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path,
        sample_attachment_data: bytes
    ):
        """Test attachment retrieval with checksum mismatch."""
        message_id = uuid4()
        storage_path = temp_storage_path / str(message_id) / "document.pdf"
        storage_path.parent.mkdir(parents=True)
        storage_path.write_bytes(sample_attachment_data)

        # Create attachment record with wrong checksum
        attachment = MessageAttachment(
            message_id=message_id,
            filename='document.pdf',
            content_type='application/pdf',
            size_bytes=len(sample_attachment_data),
            storage_path=str(storage_path),
            checksum='wrong_checksum_1234567890abcdef'
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="checksum verification failed"):
            await attachment_service.get_attachment(attachment)

    @pytest.mark.asyncio
    async def test_get_attachment_file_not_found(
        self,
        attachment_service: AttachmentService
    ):
        """Test attachment retrieval when file doesn't exist."""
        message_id = uuid4()
        attachment = MessageAttachment(
            message_id=message_id,
            filename='missing.pdf',
            content_type='application/pdf',
            size_bytes=1024,
            storage_path='/nonexistent/path/missing.pdf',
            checksum='abc123'
        )

        with pytest.raises(FileNotFoundError):
            await attachment_service.get_attachment(attachment)

    @pytest.mark.asyncio
    async def test_delete_attachment(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path,
        sample_attachment_data: bytes
    ):
        """Test attachment deletion."""
        message_id = uuid4()
        storage_path = temp_storage_path / str(message_id) / "document.pdf"
        storage_path.parent.mkdir(parents=True)
        storage_path.write_bytes(sample_attachment_data)

        attachment = MessageAttachment(
            message_id=message_id,
            filename='document.pdf',
            content_type='application/pdf',
            size_bytes=len(sample_attachment_data),
            storage_path=str(storage_path),
            checksum='abc123'
        )

        # Delete attachment
        await attachment_service.delete_attachment(attachment)

        # Verify file deleted
        assert not storage_path.exists()

    @pytest.mark.asyncio
    async def test_delete_attachment_already_deleted(
        self,
        attachment_service: AttachmentService
    ):
        """Test deleting attachment that doesn't exist."""
        message_id = uuid4()
        attachment = MessageAttachment(
            message_id=message_id,
            filename='missing.pdf',
            content_type='application/pdf',
            size_bytes=1024,
            storage_path='/nonexistent/path/missing.pdf',
            checksum='abc123'
        )

        # Should not raise exception (logs warning)
        await attachment_service.delete_attachment(attachment)

    @pytest.mark.asyncio
    async def test_process_attachments_partial_failure(
        self,
        attachment_service: AttachmentService,
        mock_gmail_client: MagicMock
    ):
        """Test processing attachments with partial failures."""
        message_id = uuid4()

        attachments_meta = [
            {
                'filename': 'valid.pdf',
                'mime_type': 'application/pdf',
                'size': 1024,
                'attachment_id': 'attach_1'
            },
            {
                'filename': 'invalid.exe',  # Blocked extension
                'mime_type': 'application/x-msdownload',
                'size': 1024,
                'attachment_id': 'attach_2'
            },
            {
                'filename': 'valid2.png',
                'mime_type': 'image/png',
                'size': 2048,
                'attachment_id': 'attach_3'
            }
        ]

        # Mock Gmail API responses
        mock_gmail_client.service.users().messages().attachments().get().execute.side_effect = [
            {'data': 'UERGIGNvbnRlbnQ='},  # "PDF content"
            {'data': 'RVhFIGNvbnRlbnQ='},  # Won't be used (validation fails)
            {'data': 'UE5HIGNvbnRlbnQ='}   # "PNG content"
        ]

        attachments = await attachment_service.process_attachments(
            message_id=message_id,
            gmail_message_id='msg_123',
            attachments=attachments_meta
        )

        # Should process valid attachments and skip invalid one
        assert len(attachments) == 2
        assert attachments[0].filename == 'valid.pdf'
        assert attachments[1].filename == 'valid2.png'

    @pytest.mark.asyncio
    async def test_storage_path_organization(
        self,
        attachment_service: AttachmentService,
        temp_storage_path: Path
    ):
        """Test that attachments are organized by message ID."""
        message_id_1 = uuid4()
        message_id_2 = uuid4()

        path1 = attachment_service._generate_storage_path(message_id_1, 'file1.pdf')
        path2 = attachment_service._generate_storage_path(message_id_2, 'file2.pdf')

        # Verify different message IDs create different directories
        assert path1.parent != path2.parent
        assert path1.parent.name == str(message_id_1)
        assert path2.parent.name == str(message_id_2)

        # Verify both under storage path
        assert path1.parent.parent == temp_storage_path
        assert path2.parent.parent == temp_storage_path

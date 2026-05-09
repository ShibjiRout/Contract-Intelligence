"""Unit tests for validate_upload() from contracts_platform.file_handling.validator."""
import pytest

from contracts_platform.core.exceptions import FileValidationError
from contracts_platform.file_handling.validator import MAX_SIZE_BYTES, validate_upload

# Minimal PDF and DOCX byte samples
SAMPLE_PDF_BYTES = b"%PDF-1.4 minimal test content"
SAMPLE_DOCX_BYTES = b"PK\x03\x04" + b"\x00" * 100

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_valid_pdf():
    """Valid PDF bytes + correct MIME → no exception."""
    validate_upload(SAMPLE_PDF_BYTES, "contract.pdf", PDF_MIME)


def test_valid_docx():
    """Valid DOCX bytes + correct MIME → no exception."""
    validate_upload(SAMPLE_DOCX_BYTES, "contract.docx", DOCX_MIME)


def test_invalid_mime():
    """image/png MIME → raises FileValidationError."""
    with pytest.raises(FileValidationError, match="not allowed"):
        validate_upload(SAMPLE_PDF_BYTES, "contract.pdf", "image/png")


def test_oversized_file():
    """File larger than 50MB → raises FileValidationError."""
    oversized = b"x" * (MAX_SIZE_BYTES + 1)
    with pytest.raises(FileValidationError, match="exceeds"):
        validate_upload(oversized, "contract.pdf", PDF_MIME)


def test_empty_file():
    """0 bytes → raises FileValidationError."""
    with pytest.raises(FileValidationError, match="empty"):
        validate_upload(b"", "contract.pdf", PDF_MIME)


def test_invalid_extension():
    """filename 'contract.txt' with valid PDF MIME → raises FileValidationError."""
    with pytest.raises(FileValidationError, match="extension"):
        validate_upload(SAMPLE_PDF_BYTES, "contract.txt", PDF_MIME)


def test_boundary_size_exactly_50mb():
    """Exactly 50MB → valid (no exception)."""
    exactly_50mb = b"x" * MAX_SIZE_BYTES
    validate_upload(exactly_50mb, "contract.pdf", PDF_MIME)


def test_docx_mime_with_pdf_extension_is_valid():
    """DOCX MIME with .pdf extension → valid, since both MIME and extension are individually allowed."""
    # The validator checks MIME and extension independently — no cross-check
    validate_upload(SAMPLE_DOCX_BYTES, "contract.pdf", DOCX_MIME)


def test_pdf_mime_with_docx_extension_is_valid():
    """PDF MIME with .docx extension → valid for same reason."""
    validate_upload(SAMPLE_PDF_BYTES, "contract.docx", PDF_MIME)

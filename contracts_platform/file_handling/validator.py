from __future__ import annotations

import os

from contracts_platform.core.exceptions import FileValidationError

ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_upload(file_bytes: bytes, filename: str, content_type: str) -> None:
    """Raise FileValidationError if the upload does not meet requirements."""
    if not file_bytes:
        raise FileValidationError("Uploaded file is empty.")

    if content_type not in ALLOWED_MIMES:
        raise FileValidationError(
            f"Content type '{content_type}' is not allowed. Must be PDF or DOCX."
        )

    if len(file_bytes) > MAX_SIZE_BYTES:
        raise FileValidationError(
            f"File size {len(file_bytes)} bytes exceeds the 50 MB limit."
        )

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"File extension '{ext}' is not allowed. Must be .pdf or .docx."
        )

"""File/image attachment validation, storage, and text extraction for the
Coffee Core Router (Brew 38). See docs/design/attachments-design.md.

Storage layout: router/uploads/<request_id>/<attachment_id>-<filename> -
request_id is generated client-side the moment a file is first attached
(before /v1/order exists for that draft) and threaded through both
/v1/upload and /v1/order, so uploads and the eventual order share one id.
Cleaned up in router/app/main.py's run_order() `finally` block once the
request completes, and swept here on a TTL basis for abandoned drafts that
were never sent. router/uploads/ is Spill Guard-ignored (.gitignore,
.cursorignore, .cursorindexingignore) in the same diff that introduced it.

No new Python dependency: pypdf and python-multipart (needed by FastAPI's
UploadFile) were both already installed before this Brew - verified
directly, not assumed.
"""

from __future__ import annotations

import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from charset_normalizer import from_bytes
from pypdf import PdfReader

DEFAULT_UPLOADS_ROOT = Path(__file__).resolve().parent.parent / "uploads"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".py", ".r", ".sas", ".json"}
ALL_ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS

# Content-Type cross-check applies only to images and PDFs (Section 2, Gap
# 2 of the design doc) - browsers unreliably report MIME types for .r/.sas
# and other text-like extensions, so those are validated by extension only.
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", ""}


class UploadValidationError(Exception):
    """Raised for a rejected upload: bad extension, MIME mismatch, or size."""


class PdfExtractionError(Exception):
    """Raised when a PDF yields near-zero extractable text (likely scanned)."""


@dataclass(frozen=True)
class UploadRecord:
    attachment_id: str
    request_id: str
    filename: str
    content_type: str
    kind: str  # "image" | "pdf" | "text"
    size_bytes: int
    file_path: Path
    extracted_text: Optional[str]  # None for images


def classify_extension(filename: str) -> str:
    """Returns "image" | "pdf" | "text". Raises UploadValidationError for
    any extension not in the allowlist."""

    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    raise UploadValidationError(
        f"File type {suffix!r} is not allowed. Allowed extensions: "
        f"{sorted(ALL_ALLOWED_EXTENSIONS)}."
    )


def validate_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
    *,
    max_upload_size_bytes: int,
) -> str:
    """Validates extension, Content-Type (images/PDF only), and size.
    Returns the classified kind. Raises UploadValidationError."""

    kind = classify_extension(filename)

    if kind == "image" and not content_type.startswith("image/"):
        raise UploadValidationError(
            f"{filename!r} has extension for an image but Content-Type "
            f"{content_type!r} does not start with 'image/'."
        )
    if kind == "pdf" and content_type not in PDF_CONTENT_TYPES:
        raise UploadValidationError(
            f"{filename!r} has a .pdf extension but Content-Type "
            f"{content_type!r} is not a recognized PDF type."
        )

    if size_bytes > max_upload_size_bytes:
        raise UploadValidationError(
            f"{filename!r} is {size_bytes} bytes, exceeding the "
            f"{max_upload_size_bytes}-byte cap."
        )

    return kind


def extract_pdf_text(file_bytes: bytes, *, min_extracted_chars: int) -> str:
    """Extracts text from every page. Raises PdfExtractionError if the
    result is near-empty (likely a scanned PDF with no text layer)."""

    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    page_texts = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(page_texts)

    if len(text.strip()) < min_extracted_chars:
        raise PdfExtractionError(
            f"PDF has no extractable text (likely a scanned image). "
            f"Extracted {len(text.strip())} characters from {len(reader.pages)} pages."
        )

    return text


def extract_text_file(file_bytes: bytes) -> str:
    """Decodes a text-like file using charset_normalizer (already
    installed) rather than assuming UTF-8, since uploaded .py/.csv/.txt
    files may use other encodings."""

    best_match = from_bytes(file_bytes).best()
    if best_match is None:
        return file_bytes.decode("utf-8", errors="replace")
    return str(best_match)


def truncate_inline_text(text: str, *, max_inline_text_chars: int) -> str:
    if len(text) <= max_inline_text_chars:
        return text
    return text[:max_inline_text_chars] + "\n...[truncated]"


def save_upload(
    request_id: str,
    attachment_id: str,
    filename: str,
    file_bytes: bytes,
    *,
    uploads_root: Path = DEFAULT_UPLOADS_ROOT,
) -> Path:
    request_dir = uploads_root / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    # attachment_id prefix avoids collisions when two files in the same
    # request share a filename.
    file_path = request_dir / f"{attachment_id}-{filename}"
    file_path.write_bytes(file_bytes)
    return file_path


def cleanup_request_uploads(request_id: str, *, uploads_root: Path = DEFAULT_UPLOADS_ROOT) -> None:
    """Removes router/uploads/<request_id>/ entirely. Called from
    run_order()'s finally block once a request completes, errors, or is
    cancelled - success and failure paths alike."""

    request_dir = uploads_root / request_id
    if request_dir.is_dir():
        shutil.rmtree(request_dir, ignore_errors=True)


def sweep_stale_uploads(
    *,
    uploads_root: Path = DEFAULT_UPLOADS_ROOT,
    ttl_seconds: int,
    now: Optional[float] = None,
) -> List[str]:
    """Removes router/uploads/<request_id>/ directories whose most recent
    file modification is older than ttl_seconds - for drafts where files
    were attached but the message was never sent (so run_order()'s
    cleanup never ran). Returns the request_ids removed, for logging/tests.
    Called opportunistically at the top of the /v1/upload handler - no
    background scheduler or new dependency."""

    if not uploads_root.is_dir():
        return []

    current_time = now if now is not None else time.time()
    removed: List[str] = []

    for request_dir in uploads_root.iterdir():
        if not request_dir.is_dir():
            continue
        newest_mtime = _newest_mtime(request_dir)
        if newest_mtime is None or (current_time - newest_mtime) > ttl_seconds:
            shutil.rmtree(request_dir, ignore_errors=True)
            removed.append(request_dir.name)

    return removed


def _newest_mtime(directory: Path) -> Optional[float]:
    mtimes = [f.stat().st_mtime for f in directory.rglob("*") if f.is_file()]
    if not mtimes:
        # Empty directory (e.g. mkdir raced ahead of the first file write) -
        # fall back to the directory's own mtime.
        try:
            return directory.stat().st_mtime
        except OSError:
            return None
    return max(mtimes)


def new_attachment_id() -> str:
    return str(uuid.uuid4())

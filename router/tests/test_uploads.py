import time
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from router.app.uploads import (
    PdfExtractionError,
    UploadValidationError,
    classify_extension,
    cleanup_request_uploads,
    extract_pdf_text,
    extract_text_file,
    new_attachment_id,
    save_upload,
    sweep_stale_uploads,
    truncate_inline_text,
    validate_upload,
)

MAX_SIZE = 20_971_520


def _text_bearing_pdf_bytes(text: str = "Hello test PDF text") -> bytes:
    """Builds a real, minimal, valid single-page PDF with an actual text
    content stream (a Helvetica font resource + a Tj text-drawing
    operator), so pypdf's extract_text() has something real to find - not
    a mocked/fake PDF. No new dependency: reportlab is not installed, so
    this hand-builds the content stream via pypdf's own generic objects."""

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)

    font_dict = DictionaryObject()
    font_dict[NameObject("/Type")] = NameObject("/Font")
    font_dict[NameObject("/Subtype")] = NameObject("/Type1")
    font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font_dict)

    resources = DictionaryObject()
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font_ref
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources

    stream_obj = DecodedStreamObject()
    stream_obj.set_data(f"BT /F1 24 Tf 20 250 Td ({text}) Tj ET".encode("latin-1"))
    page.replace_contents(stream_obj)

    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _blank_pdf_bytes(page_count: int = 2) -> bytes:
    """A real, valid PDF with pages but no content stream at all - the
    same shape a scanned-image-only PDF produces when pypdf tries to
    extract text: zero characters, not an error."""

    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


class ClassifyExtensionTests(unittest.TestCase):
    def test_image_extensions(self):
        for name in ["photo.png", "photo.jpg", "photo.jpeg", "photo.webp"]:
            self.assertEqual(classify_extension(name), "image")

    def test_pdf_extension(self):
        self.assertEqual(classify_extension("report.pdf"), "pdf")

    def test_text_extensions_including_r_and_sas(self):
        for name in ["notes.md", "notes.txt", "data.csv", "script.py", "analysis.r", "analysis.sas", "data.json"]:
            self.assertEqual(classify_extension(name), "text")

    def test_disallowed_extension_raises(self):
        with self.assertRaises(UploadValidationError):
            classify_extension("archive.zip")

    def test_case_insensitive(self):
        self.assertEqual(classify_extension("REPORT.PDF"), "pdf")


class ValidateUploadTests(unittest.TestCase):
    def test_valid_image_passes(self):
        kind = validate_upload("photo.png", "image/png", 1000, max_upload_size_bytes=MAX_SIZE)
        self.assertEqual(kind, "image")

    def test_valid_pdf_passes(self):
        kind = validate_upload("report.pdf", "application/pdf", 1000, max_upload_size_bytes=MAX_SIZE)
        self.assertEqual(kind, "pdf")

    def test_r_file_passes_regardless_of_reported_content_type(self):
        """Section 2, Gap 2: browsers unreliably report MIME types for
        .r/.sas - Content-Type is never cross-checked for text-like
        extensions."""

        kind = validate_upload("analysis.r", "application/octet-stream", 500, max_upload_size_bytes=MAX_SIZE)
        self.assertEqual(kind, "text")

    def test_sas_file_passes_with_empty_content_type(self):
        kind = validate_upload("analysis.sas", "", 500, max_upload_size_bytes=MAX_SIZE)
        self.assertEqual(kind, "text")

    def test_image_extension_with_non_image_content_type_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_upload("fake.png", "application/zip", 1000, max_upload_size_bytes=MAX_SIZE)

    def test_pdf_extension_with_bad_content_type_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_upload("fake.pdf", "image/png", 1000, max_upload_size_bytes=MAX_SIZE)

    def test_disallowed_extension_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_upload("virus.exe", "application/octet-stream", 100, max_upload_size_bytes=MAX_SIZE)

    def test_oversized_file_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_upload("huge.png", "image/png", MAX_SIZE + 1, max_upload_size_bytes=MAX_SIZE)

    def test_exact_size_cap_is_allowed(self):
        kind = validate_upload("edge.png", "image/png", MAX_SIZE, max_upload_size_bytes=MAX_SIZE)
        self.assertEqual(kind, "image")


class PdfExtractionTests(unittest.TestCase):
    def test_happy_path_extracts_real_text(self):
        pdf_bytes = _text_bearing_pdf_bytes("Hello test PDF text with plenty of margin")
        text = extract_pdf_text(pdf_bytes, min_extracted_chars=20)
        self.assertIn("Hello test PDF text with plenty of margin", text)

    def test_scanned_pdf_raises_extraction_error(self):
        pdf_bytes = _blank_pdf_bytes(page_count=3)
        with self.assertRaises(PdfExtractionError) as ctx:
            extract_pdf_text(pdf_bytes, min_extracted_chars=20)
        self.assertIn("3 pages", str(ctx.exception))

    def test_extraction_error_message_reports_extracted_char_count(self):
        pdf_bytes = _blank_pdf_bytes(page_count=1)
        with self.assertRaises(PdfExtractionError) as ctx:
            extract_pdf_text(pdf_bytes, min_extracted_chars=20)
        self.assertIn("0 characters", str(ctx.exception))

    def test_threshold_is_configurable(self):
        # Short real text that would fail a high threshold but pass a low one.
        pdf_bytes = _text_bearing_pdf_bytes("Hi")
        with self.assertRaises(PdfExtractionError):
            extract_pdf_text(pdf_bytes, min_extracted_chars=20)
        text = extract_pdf_text(pdf_bytes, min_extracted_chars=1)
        self.assertIn("Hi", text)


class ExtractTextFileTests(unittest.TestCase):
    def test_utf8_text_decodes(self):
        text = extract_text_file("hello café".encode("utf-8"))
        self.assertEqual(text, "hello café")

    def test_latin1_text_decodes_without_crashing(self):
        # A realistic-length sample - charset detection on a handful of
        # bytes (e.g. just "café") has too little signal for any
        # statistical detector, including charset_normalizer, to work
        # reliably; that is a detection-theory limit, not a product bug.
        sample = "Le café est très chaud aujourd'hui, n'est-ce pas?"
        text = extract_text_file(sample.encode("latin-1"))
        self.assertIn("caf", text)


class TruncateInlineTextTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate_inline_text("short", max_inline_text_chars=100), "short")

    def test_long_text_truncated_with_marker(self):
        long_text = "x" * 200
        result = truncate_inline_text(long_text, max_inline_text_chars=50)
        self.assertTrue(result.startswith("x" * 50))
        self.assertIn("[truncated]", result)
        self.assertLess(len(result), 200)


class SaveAndCleanupUploadTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.uploads_root = Path(self._tmp_dir.name)

    def test_save_upload_creates_request_scoped_path(self):
        attachment_id = new_attachment_id()
        path = save_upload(
            "req-1", attachment_id, "photo.png", b"fake-bytes", uploads_root=self.uploads_root
        )
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent.name, "req-1")
        self.assertIn(attachment_id, path.name)
        self.assertIn("photo.png", path.name)

    def test_same_filename_twice_does_not_collide(self):
        id1, id2 = new_attachment_id(), new_attachment_id()
        path1 = save_upload("req-1", id1, "same.txt", b"one", uploads_root=self.uploads_root)
        path2 = save_upload("req-1", id2, "same.txt", b"two", uploads_root=self.uploads_root)
        self.assertNotEqual(path1, path2)
        self.assertEqual(path1.read_bytes(), b"one")
        self.assertEqual(path2.read_bytes(), b"two")

    def test_cleanup_removes_entire_request_directory(self):
        save_upload("req-1", new_attachment_id(), "a.txt", b"a", uploads_root=self.uploads_root)
        save_upload("req-1", new_attachment_id(), "b.txt", b"b", uploads_root=self.uploads_root)
        self.assertTrue((self.uploads_root / "req-1").is_dir())

        cleanup_request_uploads("req-1", uploads_root=self.uploads_root)

        self.assertFalse((self.uploads_root / "req-1").exists())

    def test_cleanup_of_nonexistent_request_does_not_raise(self):
        cleanup_request_uploads("never-existed", uploads_root=self.uploads_root)  # should not raise


class SweepStaleUploadsTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.uploads_root = Path(self._tmp_dir.name)

    def test_sweep_removes_stale_directory(self):
        save_upload("stale-req", new_attachment_id(), "a.txt", b"a", uploads_root=self.uploads_root)
        old_time = time.time() - 10_000

        removed = sweep_stale_uploads(uploads_root=self.uploads_root, ttl_seconds=3600, now=old_time + 20_000)
        self.assertIn("stale-req", removed)
        self.assertFalse((self.uploads_root / "stale-req").exists())

    def test_sweep_keeps_fresh_directory(self):
        save_upload("fresh-req", new_attachment_id(), "a.txt", b"a", uploads_root=self.uploads_root)

        removed = sweep_stale_uploads(uploads_root=self.uploads_root, ttl_seconds=3600, now=time.time())
        self.assertEqual(removed, [])
        self.assertTrue((self.uploads_root / "fresh-req").exists())

    def test_sweep_on_missing_root_returns_empty(self):
        missing_root = self.uploads_root / "does-not-exist"
        self.assertEqual(sweep_stale_uploads(uploads_root=missing_root, ttl_seconds=3600), [])


if __name__ == "__main__":
    unittest.main()

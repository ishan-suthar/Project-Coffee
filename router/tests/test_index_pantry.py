import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.pantry import connect
from router.tools.index_pantry import index_pantry


class IndexPantryTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.root = Path(self._tmp_dir.name) / "knowledge"
        self.root.mkdir()
        self.index_path = Path(self._tmp_dir.name) / "pantry_index.db"

    def _chunk_count(self) -> int:
        with connect(self.index_path) as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]

    def _file_row(self, rel_path: str):
        with connect(self.index_path) as conn:
            return conn.execute("SELECT * FROM files WHERE path = ?", (rel_path,)).fetchone()

    def test_indexes_a_fixture_directory(self):
        (self.root / "a.md").write_text("The zephyr constant is forty-two.", encoding="utf-8")
        (self.root / "b.md").write_text("Coffee brewing needs hot water.", encoding="utf-8")

        stats = index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        self.assertEqual(stats.files_indexed, 2)
        self.assertGreater(stats.chunks_written, 0)
        self.assertGreater(self._chunk_count(), 0)

    def test_skips_unsafe_and_non_text_files(self):
        (self.root / "a.md").write_text("real content", encoding="utf-8")
        (self.root / "image.png").write_bytes(b"\x89PNG\r\n")
        secrets_dir = self.root / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "notes.md").write_text("do not index me", encoding="utf-8")

        stats = index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        self.assertEqual(stats.files_indexed, 1)
        self.assertGreaterEqual(stats.files_skipped_unsafe_or_binary, 2)
        with connect(self.index_path) as conn:
            paths = {row["path"] for row in conn.execute("SELECT DISTINCT path FROM chunks").fetchall()}
        self.assertFalse(any("secrets" in p for p in paths))
        self.assertFalse(any(p.endswith(".png") for p in paths))

    def test_incremental_reindex_skips_unchanged_files(self):
        target = self.root / "a.md"
        target.write_text("original content", encoding="utf-8")
        index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        stats = index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        self.assertEqual(stats.files_indexed, 0)
        self.assertEqual(stats.files_skipped_unchanged, 1)

    def test_incremental_reindex_picks_up_changed_content(self):
        target = self.root / "a.md"
        target.write_text("original content mentioning zephyr", encoding="utf-8")
        index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        # Ensure a strictly newer mtime (some filesystems have coarse
        # mtime resolution) and change the content.
        time.sleep(0.05)
        new_mtime = time.time() + 1
        target.write_text("updated content mentioning coffee instead", encoding="utf-8")
        import os

        os.utime(target, (new_mtime, new_mtime))

        stats = index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        self.assertEqual(stats.files_indexed, 1)
        with connect(self.index_path) as conn:
            rows = conn.execute("SELECT text FROM chunks WHERE path LIKE '%a.md'").fetchall()
        combined = " ".join(row["text"] for row in rows)
        self.assertIn("updated content", combined)
        self.assertNotIn("original content", combined)

    def test_deleted_file_is_removed_from_index_on_reindex(self):
        target = self.root / "a.md"
        target.write_text("will be deleted", encoding="utf-8")
        index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))
        self.assertGreater(self._chunk_count(), 0)

        target.unlink()
        stats = index_pantry(self.root, self.index_path, chunk_size_chars=1200, overlap_chars=200, repo_root=Path(self._tmp_dir.name))

        self.assertEqual(stats.files_removed, 1)
        self.assertEqual(self._chunk_count(), 0)
        self.assertIsNone(self._file_row("knowledge/a.md"))

    def test_missing_root_directory_does_not_crash(self):
        missing_root = Path(self._tmp_dir.name) / "does-not-exist"
        stats = index_pantry(missing_root, self.index_path, chunk_size_chars=1200, overlap_chars=200)
        self.assertEqual(stats.files_indexed, 0)


if __name__ == "__main__":
    unittest.main()

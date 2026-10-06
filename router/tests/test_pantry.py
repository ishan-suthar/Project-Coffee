import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.pantry import (
    PantryChunk,
    build_fts_query,
    chunk_text,
    connect,
    is_indexable_file,
    resolve_pantry_file_path,
    retrieve_chunks,
)


class ChunkTextTests(unittest.TestCase):
    def test_short_text_yields_one_chunk(self):
        chunks = chunk_text("hello world", chunk_size_chars=1200, overlap_chars=200)
        self.assertEqual(chunks, ["hello world"])

    def test_empty_text_yields_no_chunks(self):
        self.assertEqual(chunk_text("   ", chunk_size_chars=100, overlap_chars=10), [])
        self.assertEqual(chunk_text("", chunk_size_chars=100, overlap_chars=10), [])

    def test_long_text_splits_into_overlapping_windows(self):
        text = "abcdefghij" * 5  # 50 chars
        chunks = chunk_text(text, chunk_size_chars=20, overlap_chars=5)
        self.assertGreater(len(chunks), 1)
        # Overlap: the tail of one chunk should reappear at the head of the next.
        self.assertEqual(chunks[0][-5:], chunks[1][:5])

    def test_rejects_non_positive_chunk_size(self):
        with self.assertRaises(ValueError):
            chunk_text("hello", chunk_size_chars=0, overlap_chars=0)


class BuildFtsQueryTests(unittest.TestCase):
    def test_tokenizes_and_quotes_terms(self):
        query = build_fts_query("What is the Ledger's cost_usd column for?")
        self.assertIn('"What"', query)
        self.assertIn('"cost_usd"', query)
        self.assertIn(" OR ", query)

    def test_none_for_punctuation_only_text(self):
        self.assertIsNone(build_fts_query("... ??? !!!"))

    def test_none_for_empty_text(self):
        self.assertIsNone(build_fts_query(""))

    def test_escapes_embedded_quotes(self):
        # Must not produce a syntactically broken FTS5 query string.
        query = build_fts_query('he said "hi"')
        self.assertIsNotNone(query)


class IsIndexableFileTests(unittest.TestCase):
    def test_allows_markdown(self):
        self.assertTrue(is_indexable_file(Path("knowledge/00_index.md")))

    def test_rejects_non_text_extension(self):
        self.assertFalse(is_indexable_file(Path("knowledge/diagram.png")))

    def test_rejects_unsafe_path_even_with_text_extension(self):
        self.assertFalse(is_indexable_file(Path("knowledge/secrets/notes.md")))
        self.assertFalse(is_indexable_file(Path("knowledge/.env.md")))


class RetrieveChunksTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.index_path = Path(self._tmp_dir.name) / "pantry_index.db"

    def _seed(self, rows):
        with connect(self.index_path) as conn:
            for path, chunk_index, text in rows:
                conn.execute(
                    "INSERT INTO chunks (path, chunk_index, text) VALUES (?, ?, ?)",
                    (path, chunk_index, text),
                )

    def test_finds_matching_chunk_by_distinctive_term(self):
        self._seed(
            [
                ("knowledge/a.md", 0, "The zephyr constant equals forty-two exactly."),
                ("knowledge/b.md", 0, "Unrelated content about coffee brewing temperatures."),
            ]
        )
        with connect(self.index_path) as conn:
            results = retrieve_chunks(conn, "what is the zephyr constant?", top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, "knowledge/a.md")
        self.assertIsInstance(results[0], PantryChunk)

    def test_respects_top_k(self):
        self._seed([(f"knowledge/{i}.md", 0, "widget widget widget") for i in range(10)])
        with connect(self.index_path) as conn:
            results = retrieve_chunks(conn, "widget", top_k=3)
        self.assertEqual(len(results), 3)

    def test_no_tokens_returns_empty_list_not_an_error(self):
        self._seed([("knowledge/a.md", 0, "some content")])
        with connect(self.index_path) as conn:
            results = retrieve_chunks(conn, "???", top_k=5)
        self.assertEqual(results, [])

    def test_no_match_returns_empty_list(self):
        self._seed([("knowledge/a.md", 0, "some content")])
        with connect(self.index_path) as conn:
            results = retrieve_chunks(conn, "nonexistentwordxyz", top_k=5)
        self.assertEqual(results, [])


class ResolvePantryFilePathTests(unittest.TestCase):
    """Fully sandboxed: repo_root/pantry_root both point into a temp
    fixture tree, never the real repository."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.repo_root = Path(self._tmp_dir.name)
        self.pantry_root = self.repo_root / "knowledge"
        self.pantry_root.mkdir()
        (self.pantry_root / "00_index.md").write_text("hello", encoding="utf-8")
        (self.pantry_root / "sub").mkdir()
        (self.pantry_root / "sub" / "nested.md").write_text("nested", encoding="utf-8")
        (self.repo_root / "router_config").mkdir()
        (self.repo_root / "router_config" / "settings.yaml").write_text("secret: no", encoding="utf-8")
        (self.pantry_root / "secrets").mkdir()
        (self.pantry_root / "secrets" / "notes.md").write_text("shh", encoding="utf-8")

    def _resolve(self, requested):
        return resolve_pantry_file_path(requested, repo_root=self.repo_root, pantry_root=self.pantry_root)

    def test_resolves_a_real_file_inside_the_root(self):
        result = self._resolve("knowledge/00_index.md")
        self.assertIsNotNone(result)
        self.assertTrue(result.is_file())

    def test_resolves_a_nested_real_file(self):
        result = self._resolve("knowledge/sub/nested.md")
        self.assertIsNotNone(result)

    def test_rejects_absolute_path(self):
        self.assertIsNone(self._resolve("C:/Windows/System32/config"))
        self.assertIsNone(self._resolve("/etc/passwd"))

    def test_rejects_parent_traversal(self):
        self.assertIsNone(self._resolve("knowledge/../router_config/settings.yaml"))
        self.assertIsNone(self._resolve("../router_config/settings.yaml"))

    def test_rejects_unsafe_path_marker(self):
        self.assertIsNone(self._resolve("knowledge/secrets/notes.md"))

    def test_rejects_nonexistent_file(self):
        self.assertIsNone(self._resolve("knowledge/does-not-exist.md"))

    def test_rejects_path_outside_pantry_root_but_inside_repo(self):
        self.assertIsNone(self._resolve("router_config/settings.yaml"))

    def test_rejects_empty_path(self):
        self.assertIsNone(self._resolve(""))


if __name__ == "__main__":
    unittest.main()

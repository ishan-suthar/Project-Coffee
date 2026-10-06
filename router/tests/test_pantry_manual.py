"""Retrieval tests for knowledge/coffee-manual.md (Brew 56).

These index the REAL manual - not a fixture - into a temporary FTS5
index, then run the real questions a user would ask Coffee about itself
and assert the right section comes back. The point is not to test the
chunker (test_pantry.py already does) but to catch the manual itself
regressing: a section rewritten in a way that stops answering the
question it exists to answer would fail here, which no other test in the
repo would notice.

The manual is a single hand-maintained document, so its sections do not
align with the chunker's fixed-width windows. That is accepted: these
tests assert the answering text is present in the retrieved set (what
actually reaches the Bean), not that it lands in any particular chunk
index.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from router.app.config import Settings
from router.app.pantry import DEFAULT_PANTRY_ROOT, REPO_ROOT, connect, retrieve_chunks
from router.tools.index_pantry import index_pantry

MANUAL_PATH = DEFAULT_PANTRY_ROOT / "coffee-manual.md"


class CoffeeManualRetrievalTests(unittest.TestCase):
    """Each test is one of the four questions Brew 56 was specified
    against."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.index_path = Path(cls._tmpdir.name) / "pantry_index.db"
        settings = Settings.from_yaml()
        cls.top_k = settings.pantry_top_k
        index_pantry(
            root=DEFAULT_PANTRY_ROOT,
            index_path=cls.index_path,
            chunk_size_chars=settings.pantry_chunk_size_chars,
            overlap_chars=settings.pantry_chunk_overlap_chars,
            repo_root=REPO_ROOT,
        )

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def _retrieve(self, question: str) -> str:
        """Returns the concatenated text of what a real request for this
        question would actually put in front of a Bean."""

        with connect(self.index_path) as conn:
            chunks = retrieve_chunks(conn, question, top_k=self.top_k)
        self.assertTrue(chunks, f"no chunks retrieved for {question!r}")
        return "\n".join(chunk.text for chunk in chunks)

    def test_the_manual_exists_and_is_indexable(self):
        self.assertTrue(MANUAL_PATH.is_file())
        with connect(self.index_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM chunks WHERE path = ?",
                ("knowledge/coffee-manual.md",),
            ).fetchone()
        self.assertGreater(row["n"], 0)

    def test_who_made_this(self):
        text = self._retrieve("who made this?")
        self.assertIn("Ishan Suthar", text)
        self.assertIn("July 2026", text)

    def test_how_does_routing_work(self):
        text = self._retrieve("how does routing work?")
        lowered = text.lower()
        self.assertIn("Bean", text)
        # The routing answer has to name the actual mechanism, not just
        # the word "routing".
        self.assertIn("classif", lowered)
        self.assertIn("cheapest", lowered)

    def test_how_do_i_stop_it_forgetting_my_document(self):
        """The honesty test. A retrieved answer that omits the trimming
        behaviour, or omits the Pantry as the fix, is the falsely
        reassuring answer this manual exists to prevent."""

        text = self._retrieve("how do I stop it forgetting my document?")
        lowered = text.lower()
        self.assertIn("oldest whole turns", lowered)
        self.assertIn("pantry", lowered)
        self.assertTrue(
            "does not tell you" in lowered or "silent" in lowered,
            "the retrieved memory answer does not disclose that trimming is silent",
        )

    def test_what_is_a_bean(self):
        text = self._retrieve("what is a Bean?")
        self.assertIn("one configured model", text)
        self.assertIn("alias", text.lower())

    def test_manual_never_leaks_a_raw_provider_model_id(self):
        """Same aliases-only rule the event contract is held to - the
        manual is read back to users, so a raw model ID here would leak
        exactly what every other surface forbids."""

        text = MANUAL_PATH.read_text(encoding="utf-8")
        for vendor_prefix in (
            "anthropic/",
            "google/",
            "openai/",
            "deepseek/",
            "moonshotai/",
            "nvidia/",
            "cohere/",
            "poolside/",
        ):
            self.assertNotIn(vendor_prefix, text)

    def test_manual_records_the_brew_it_was_written_against(self):
        """Part 3's anti-staleness marker - if this is ever dropped, the
        manual has no way to tell a reader how old it is."""

        text = MANUAL_PATH.read_text(encoding="utf-8")
        self.assertRegex(text, r"Brew \d+")
        self.assertIn("index_pantry.py", text)


if __name__ == "__main__":
    unittest.main()

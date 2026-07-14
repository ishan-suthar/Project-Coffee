import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.aliases import Bean, BeanRegistry
from router.app.memory_proposals import (
    ALLOWED_PATHS,
    MemoryProposalError,
    MemoryProposalGuardrailError,
    approve_memory_proposal,
    build_generation_prompt,
    build_transcript_text,
    check_over_deletion,
    check_path_allowed,
    compute_unified_diff,
    generate_memory_proposal,
    parse_proposal_response,
    read_current_content,
)
from router.app.openrouter_client import StreamChunk
from router.app.sessions import SessionStore


def _make_bean_registry() -> BeanRegistry:
    return BeanRegistry(
        [
            Bean(
                alias="House Blend",
                role="default",
                model_id="vendor/default:free",
                vision=False,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            )
        ]
    )


VALID_RESPONSE = """### FILE: brew-log/active_context.md
# Active Context

Updated during the session.
### END FILE

### FILE: brew-log/progress.md
# Progress

- Did a thing.
### END FILE
"""


class ParseProposalResponseTests(unittest.TestCase):
    def test_parses_both_blocks(self):
        parsed = parse_proposal_response(VALID_RESPONSE)
        self.assertEqual(set(parsed.keys()), set(ALLOWED_PATHS))
        self.assertIn("Updated during the session.", parsed["brew-log/active_context.md"])

    def test_missing_end_marker_raises(self):
        broken = "### FILE: brew-log/active_context.md\nsome content\n"
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response(broken)

    def test_disallowed_path_raises(self):
        bad = (
            "### FILE: memory-bank/activeContext.md\ncontent\n### END FILE\n\n"
            "### FILE: brew-log/progress.md\ncontent\n### END FILE\n"
        )
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response(bad)

    def test_path_escape_attempt_raises(self):
        bad = (
            "### FILE: brew-log/../secrets.env\ncontent\n### END FILE\n\n"
            "### FILE: brew-log/progress.md\ncontent\n### END FILE\n"
        )
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response(bad)

    def test_duplicate_block_for_same_path_raises(self):
        dup = (
            "### FILE: brew-log/active_context.md\nfirst\n### END FILE\n\n"
            "### FILE: brew-log/active_context.md\nsecond\n### END FILE\n\n"
            "### FILE: brew-log/progress.md\ncontent\n### END FILE\n"
        )
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response(dup)

    def test_missing_one_of_two_required_files_raises(self):
        only_one = "### FILE: brew-log/active_context.md\ncontent\n### END FILE\n"
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response(only_one)

    def test_no_blocks_at_all_raises(self):
        with self.assertRaises(MemoryProposalError):
            parse_proposal_response("Sorry, I can't help with that.")


class CheckPathAllowedTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.repo_root = Path(self._tmp_dir.name)
        (self.repo_root / "brew-log").mkdir()

    def test_allowed_path_passes(self):
        self.assertIsNone(check_path_allowed("brew-log/active_context.md", repo_root=self.repo_root))

    def test_near_miss_memory_bank_path_rejected(self):
        self.assertIsNotNone(check_path_allowed("memory-bank/activeContext.md", repo_root=self.repo_root))

    def test_arbitrary_path_under_brew_log_rejected(self):
        """Requirement 3 is a literal two-file allowlist, not a
        `brew-log/` prefix rule - any other file under brew-log/ (even a
        real one) must be rejected."""

        self.assertIsNotNone(check_path_allowed("brew-log/decisions.md", repo_root=self.repo_root))

    def test_path_traversal_rejected(self):
        self.assertIsNotNone(
            check_path_allowed("brew-log/../../etc/passwd", repo_root=self.repo_root)
        )


class CheckOverDeletionTests(unittest.TestCase):
    def test_small_edit_passes(self):
        old = "line one\nline two\nline three\n"
        new = "line one\nline two\nline three\nline four\n"
        self.assertIsNone(check_over_deletion(old, new))

    def test_over_half_deletion_is_rejected(self):
        old = "line one\nline two\nline three\nline four\n"
        new = "line one\n"
        reason = check_over_deletion(old, new)
        self.assertIsNotNone(reason)
        self.assertIn("stale-memory-protection", reason)

    def test_wipe_and_replace_with_one_new_line_is_rejected(self):
        old = "a\nb\nc\nd\n"
        new = "completely different single line\n"
        self.assertIsNotNone(check_over_deletion(old, new))

    def test_empty_original_content_never_blocked(self):
        self.assertIsNone(check_over_deletion("", "brand new content\n"))

    def test_exactly_at_boundary_passes(self):
        old = "a\nb\n"
        new = "a\n"  # deletes 1 of 2 lines = 50%, not > 50%
        self.assertIsNone(check_over_deletion(old, new))


class ComputeUnifiedDiffTests(unittest.TestCase):
    def test_diff_shows_added_line(self):
        diff = compute_unified_diff("a\n", "a\nb\n", "brew-log/progress.md")
        self.assertIn("+b", diff)
        self.assertIn("brew-log/progress.md", diff)


class BuildTranscriptTextTests(unittest.TestCase):
    def test_truncates_from_the_start_keeping_most_recent(self):
        class _Msg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        messages = [_Msg("user", "x" * 50), _Msg("assistant", "RECENT_MARKER")]
        text = build_transcript_text(messages, max_chars=20)
        self.assertIn("RECENT_MARKER", text)
        self.assertLessEqual(len(text), 20)


class GenerateAndApproveMemoryProposalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.repo_root = Path(self._tmp_dir.name)
        (self.repo_root / "brew-log").mkdir()
        (self.repo_root / "brew-log" / "active_context.md").write_text(
            "# Active Context\n\nOriginal line.\n", encoding="utf-8"
        )
        (self.repo_root / "brew-log" / "progress.md").write_text(
            "# Progress\n\nOriginal progress line.\n", encoding="utf-8"
        )
        self.session_store = SessionStore(self.repo_root / "sessions.db")
        self.session_id = self.session_store.create_session("default")
        self.session_store.add_message(
            self.session_id, request_id="r1", role="user", content="Implement the widget."
        )
        self.session_store.add_message(
            self.session_id, request_id="r1", role="assistant", content="Done, widget implemented."
        )
        self.bean_registry = _make_bean_registry()

    async def _fake_stream(self, model_id, prompt, **_kwargs):
        yield StreamChunk(content_delta=VALID_RESPONSE)
        yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 42})
        yield StreamChunk(is_final=True)

    async def test_generate_returns_diffs_for_both_files(self):
        proposal = await generate_memory_proposal(
            session_id=self.session_id,
            session_store=self.session_store,
            bean_registry=self.bean_registry,
            bean_alias="House Blend",
            max_transcript_chars=20_000,
            stream_order_fn=self._fake_stream,
            repo_root=self.repo_root,
        )
        self.assertEqual({f.path for f in proposal.files}, set(ALLOWED_PATHS))
        active_context_file = next(f for f in proposal.files if f.path == "brew-log/active_context.md")
        self.assertIn("+", active_context_file.diff)
        self.assertEqual(proposal.tokens_out, 42)

    async def test_generate_raises_on_unparseable_response(self):
        async def _bad_stream(model_id, prompt, **_kwargs):
            yield StreamChunk(content_delta="not the right format at all")
            yield StreamChunk(is_final=True)

        with self.assertRaises(MemoryProposalError):
            await generate_memory_proposal(
                session_id=self.session_id,
                session_store=self.session_store,
                bean_registry=self.bean_registry,
                bean_alias="House Blend",
                max_transcript_chars=20_000,
                stream_order_fn=_bad_stream,
                repo_root=self.repo_root,
            )

    async def test_generate_raises_guardrail_error_on_over_deletion(self):
        async def _wipe_stream(model_id, prompt, **_kwargs):
            wipe_response = (
                "### FILE: brew-log/active_context.md\nsingle new line\n### END FILE\n\n"
                "### FILE: brew-log/progress.md\n# Progress\n\nOriginal progress line.\n### END FILE\n"
            )
            # Make active_context.md's original content long enough that
            # replacing it with one line is unambiguously over 50% deletion.
            yield StreamChunk(content_delta=wipe_response)
            yield StreamChunk(is_final=True)

        (self.repo_root / "brew-log" / "active_context.md").write_text(
            "line one\nline two\nline three\nline four\n", encoding="utf-8"
        )

        with self.assertRaises(MemoryProposalGuardrailError):
            await generate_memory_proposal(
                session_id=self.session_id,
                session_store=self.session_store,
                bean_registry=self.bean_registry,
                bean_alias="House Blend",
                max_transcript_chars=20_000,
                stream_order_fn=_wipe_stream,
                repo_root=self.repo_root,
            )

    async def test_approve_writes_both_files_and_leaves_no_proposal_state_here(self):
        proposal = await generate_memory_proposal(
            session_id=self.session_id,
            session_store=self.session_store,
            bean_registry=self.bean_registry,
            bean_alias="House Blend",
            max_transcript_chars=20_000,
            stream_order_fn=self._fake_stream,
            repo_root=self.repo_root,
        )

        approve_memory_proposal(proposal, repo_root=self.repo_root)

        self.assertIn(
            "Updated during the session.",
            read_current_content("brew-log/active_context.md", repo_root=self.repo_root),
        )
        self.assertIn(
            "Did a thing.",
            read_current_content("brew-log/progress.md", repo_root=self.repo_root),
        )

    async def test_approve_re_checks_guardrails_against_current_disk_content(self):
        """Defense-in-depth: if the on-disk file changed (grew) between
        generation and approval such that the already-generated
        new_content now represents an over-deletion, approval must refuse
        - not blindly trust the snapshot taken at generation time."""

        proposal = await generate_memory_proposal(
            session_id=self.session_id,
            session_store=self.session_store,
            bean_registry=self.bean_registry,
            bean_alias="House Blend",
            max_transcript_chars=20_000,
            stream_order_fn=self._fake_stream,
            repo_root=self.repo_root,
        )

        # Simulate a concurrent edit that added a lot of content the
        # proposal's new_content (captured before this edit) would wipe out.
        (self.repo_root / "brew-log" / "active_context.md").write_text(
            "line one\nline two\nline three\nline four\nline five\nline six\n", encoding="utf-8"
        )

        with self.assertRaises(MemoryProposalGuardrailError):
            approve_memory_proposal(proposal, repo_root=self.repo_root)

        # Nothing was written - all-or-nothing.
        self.assertIn(
            "line six", read_current_content("brew-log/active_context.md", repo_root=self.repo_root)
        )


if __name__ == "__main__":
    unittest.main()

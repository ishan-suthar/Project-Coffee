import json
import unittest

from router.app.history import (
    EMPTY_HISTORY_RESULT,
    IMAGE_HISTORY_NOTE,
    assemble_history,
    format_attachment_block,
    pair_turns,
)
from router.app.sessions import MessageRecord


def _message(
    *,
    request_id: str,
    role: str,
    content: str,
    created_at: str,
    draft_quality: bool = False,
    attachments_json: str = None,
) -> MessageRecord:
    return MessageRecord(
        id=f"{request_id}-{role}",
        session_id="session-1",
        request_id=request_id,
        role=role,
        content=content,
        bean_alias="House Blend" if role == "assistant" else None,
        task_type="explain" if role == "assistant" else None,
        complexity="espresso_shot" if role == "assistant" else None,
        cost_usd=0.0 if role == "assistant" else None,
        latency_ms=100 if role == "assistant" else None,
        escalated=False if role == "assistant" else None,
        draft_quality=draft_quality if role == "assistant" else None,
        rating=None,
        created_at=created_at,
        attachments_json=attachments_json,
    )


def _turn_messages(request_id: str, ts: str, *, user_text="hi", assistant_text="hello", **kwargs):
    return [
        _message(request_id=request_id, role="user", content=user_text, created_at=ts + "0"),
        _message(
            request_id=request_id, role="assistant", content=assistant_text, created_at=ts + "1", **kwargs
        ),
    ]


class PairTurnsTests(unittest.TestCase):
    def test_pairs_user_and_assistant_by_request_id_oldest_first(self):
        messages = _turn_messages("r1", "2026-01-01T00:00:00") + _turn_messages("r2", "2026-01-01T00:01:00")
        turns = pair_turns(messages)
        self.assertEqual([t.request_id for t in turns], ["r1", "r2"])

    def test_incomplete_turn_missing_assistant_is_dropped(self):
        messages = [_message(request_id="r1", role="user", content="hi", created_at="2026-01-01T00:00:00")]
        turns = pair_turns(messages)
        self.assertEqual(turns, [])

    def test_incomplete_turn_missing_user_is_dropped(self):
        messages = [
            _message(request_id="r1", role="assistant", content="hi", created_at="2026-01-01T00:00:00")
        ]
        turns = pair_turns(messages)
        self.assertEqual(turns, [])

    def test_draft_quality_message_is_included_when_it_is_the_only_response(self):
        # Under the current one-assistant-row-per-request_id architecture
        # this is always true (docs/design/conversation-memory-design.md
        # Section 2, Open Question 2) - included here as a real assertion,
        # not just a comment.
        messages = _turn_messages("r1", "2026-01-01T00:00:00", draft_quality=True)
        turns = pair_turns(messages)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].assistant_content, "hello")

    def test_reattaches_stored_pdf_text_with_the_standard_delimiter(self):
        attachments = json.dumps(
            [{"filename": "notes.pdf", "kind": "pdf", "content_type": "application/pdf", "extracted_text": "The quarterly numbers."}]
        )
        messages = [
            _message(
                request_id="r1",
                role="user",
                content="what does this say",
                created_at="2026-01-01T00:00:00",
                attachments_json=attachments,
            ),
            _message(request_id="r1", role="assistant", content="It says...", created_at="2026-01-01T00:00:01"),
        ]
        turns = pair_turns(messages)
        self.assertEqual(len(turns), 1)
        self.assertIn(format_attachment_block("notes.pdf", "The quarterly numbers."), turns[0].user_content)
        self.assertIn("what does this say", turns[0].user_content)

    def test_image_attachment_never_reattaches_bytes_but_adds_a_note(self):
        attachments = json.dumps([{"filename": "photo.png", "kind": "image", "content_type": "image/png"}])
        messages = [
            _message(
                request_id="r1",
                role="user",
                content="what is this",
                created_at="2026-01-01T00:00:00",
                attachments_json=attachments,
            ),
            _message(request_id="r1", role="assistant", content="A cat.", created_at="2026-01-01T00:00:01"),
        ]
        turns = pair_turns(messages)
        self.assertIn(IMAGE_HISTORY_NOTE, turns[0].user_content)
        self.assertNotIn("base64", turns[0].user_content)
        self.assertNotIn("data:image", turns[0].user_content)

    def test_malformed_attachments_json_falls_back_to_plain_content(self):
        messages = [
            _message(
                request_id="r1",
                role="user",
                content="hi",
                created_at="2026-01-01T00:00:00",
                attachments_json="not valid json",
            ),
            _message(request_id="r1", role="assistant", content="hello", created_at="2026-01-01T00:00:01"),
        ]
        turns = pair_turns(messages)
        self.assertEqual(turns[0].user_content, "hi")


class AssembleHistoryTests(unittest.TestCase):
    def _turns(self, n):
        turns = []
        for turn in pair_turns(
            [m for i in range(n) for m in _turn_messages(f"r{i}", f"2026-01-01T00:0{i}:00")]
        ):
            turns.append(turn)
        return turns

    def test_empty_turns_returns_empty_result(self):
        result = assemble_history([], current_prompt_chars=10, max_messages=20, max_chars=24000)
        self.assertEqual(result.messages, [])
        self.assertEqual(result.turns_included, 0)
        self.assertEqual(result.tokens_est, 0)

    def test_oldest_first_ordering_with_current_prompt_implicitly_last(self):
        turns = self._turns(3)
        result = assemble_history(turns, current_prompt_chars=10, max_messages=20, max_chars=24000)
        roles = [m["role"] for m in result.messages]
        self.assertEqual(roles, ["user", "assistant", "user", "assistant", "user", "assistant"])
        contents = [m["content"] for m in result.messages if m["role"] == "user"]
        self.assertEqual(contents, ["hi", "hi", "hi"])  # all identical fixture text, ordering checked via count/turns

    def test_max_messages_limit_drops_oldest_whole_turns(self):
        turns = self._turns(5)  # 5 turns = 10 messages
        result = assemble_history(turns, current_prompt_chars=10, max_messages=4, max_chars=24000)
        # 4 messages = 2 turns, newest kept
        self.assertEqual(result.turns_included, 2)
        self.assertEqual(len(result.messages), 4)

    def test_never_splits_a_user_assistant_pair(self):
        turns = self._turns(3)
        result = assemble_history(turns, current_prompt_chars=10, max_messages=3, max_chars=24000)
        # max_messages=3 can't fit a whole second turn (needs 2, budget for
        # 1 turn is fine, but 3 messages allows only 1 whole turn, not 1.5)
        self.assertEqual(len(result.messages) % 2, 0)

    def test_max_chars_limit_drops_oldest_turns(self):
        turns = self._turns(3)
        one_turn_chars = turns[0].chars
        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=one_turn_chars + 1
        )
        self.assertEqual(result.turns_included, 1)
        self.assertEqual(result.messages[0]["content"], turns[-1].user_content)

    def test_oversized_current_prompt_yields_zero_history(self):
        turns = self._turns(3)
        result = assemble_history(turns, current_prompt_chars=999_999, max_messages=20, max_chars=24000)
        self.assertEqual(result.turns_included, 0)
        self.assertEqual(result.messages, [])

    def test_current_prompt_reserved_before_history_budget(self):
        turns = self._turns(1)
        turn_chars = turns[0].chars
        # Budget exactly enough for the turn if 0 chars reserved for the
        # prompt, but the prompt itself eats it all.
        result = assemble_history(
            turns, current_prompt_chars=turn_chars, max_messages=20, max_chars=turn_chars
        )
        self.assertEqual(result.turns_included, 0)

    def test_tokens_est_is_chars_included_divided_by_four(self):
        turns = self._turns(1)
        result = assemble_history(turns, current_prompt_chars=0, max_messages=20, max_chars=24000)
        self.assertEqual(result.tokens_est, result.chars_included // 4)


class HistoryTrimReportingTests(unittest.TestCase):
    """Brew 57: assemble_history() reports what it dropped, so the UI can
    surface trimming instead of the user experiencing a model that
    silently forgot something they sent."""

    def _turns(self, n, *, user_text="hi", assistant_text="hello"):
        return pair_turns(
            [
                m
                for i in range(n)
                for m in _turn_messages(
                    f"r{i}",
                    f"2026-01-01T00:0{i}:00",
                    user_text=user_text,
                    assistant_text=assistant_text,
                )
            ]
        )

    # --- nothing dropped ------------------------------------------------

    def test_zero_trim_reports_nothing_dropped_and_no_reason(self):
        turns = self._turns(3)
        result = assemble_history(
            turns, current_prompt_chars=10, max_messages=20, max_chars=24000
        )
        self.assertEqual(result.turns_included, 3)
        self.assertEqual(result.turns_dropped, 0)
        self.assertEqual(result.chars_dropped, 0)
        self.assertIsNone(result.drop_reason)

    def test_empty_turns_reports_nothing_dropped(self):
        """No history at all is not a trim - drop_reason must stay None so
        a UI never renders a drop notice on turn one."""

        result = assemble_history([], current_prompt_chars=10, max_messages=20, max_chars=24000)
        self.assertEqual(result.turns_dropped, 0)
        self.assertEqual(result.chars_dropped, 0)
        self.assertIsNone(result.drop_reason)

    def test_empty_history_result_constant_reports_nothing_dropped(self):
        """The remember_chat=False path never calls assemble_history at
        all - the constant it uses instead must carry the same values."""

        self.assertEqual(EMPTY_HISTORY_RESULT.turns_dropped, 0)
        self.assertEqual(EMPTY_HISTORY_RESULT.chars_dropped, 0)
        self.assertIsNone(EMPTY_HISTORY_RESULT.drop_reason)

    # --- ordinary window exhaustion -------------------------------------

    def test_char_cap_trim_reports_accurate_counts_and_window_full(self):
        turns = self._turns(4)
        one_turn_chars = turns[0].chars
        # Room for exactly two turns.
        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=one_turn_chars * 2
        )

        self.assertEqual(result.turns_included, 2)
        self.assertEqual(result.turns_dropped, 2)
        # Exact, not an estimate - whole turns are dropped, never truncated.
        self.assertEqual(result.chars_dropped, turns[0].chars + turns[1].chars)
        self.assertEqual(result.drop_reason, "window_full")

    def test_message_cap_trim_also_reports_window_full(self):
        """Both caps report the same reason on purpose - the user's
        experience and remedy are identical regardless of which fired."""

        turns = self._turns(5)
        result = assemble_history(
            turns, current_prompt_chars=10, max_messages=4, max_chars=24000
        )

        self.assertEqual(result.turns_included, 2)
        self.assertEqual(result.turns_dropped, 3)
        self.assertEqual(result.chars_dropped, sum(t.chars for t in turns[:3]))
        self.assertEqual(result.drop_reason, "window_full")

    def test_dropped_counts_always_reconcile_with_included_counts(self):
        turns = self._turns(6)
        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=turns[0].chars * 3
        )

        self.assertEqual(result.turns_included + result.turns_dropped, len(turns))
        self.assertEqual(
            result.chars_included + result.chars_dropped, sum(t.chars for t in turns)
        )

    # --- the oversized single turn --------------------------------------

    def test_single_oversized_turn_reports_its_own_reason(self):
        """The motivating case: a long document pasted as turn one."""

        turns = self._turns(1, user_text="x" * 40_000)
        result = assemble_history(
            turns, current_prompt_chars=10, max_messages=20, max_chars=24000
        )

        self.assertEqual(result.turns_included, 0)
        self.assertEqual(result.turns_dropped, 1)
        self.assertEqual(result.chars_dropped, turns[0].chars)
        self.assertEqual(result.drop_reason, "single_turn_too_large")

    def test_oversized_turn_behind_smaller_turns_still_reports_too_large(self):
        """Deliberate precedence: the huge document is reported even when
        a small turn is what technically halted the walk. Calling this
        ordinary exhaustion would be true but would point the user at the
        wrong fix."""

        big = self._turns(1, user_text="x" * 40_000)
        small = self._turns(3)
        turns = big + small  # oldest-first: the document is turn one

        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=small[0].chars * 2
        )

        self.assertGreater(result.turns_dropped, 1)
        self.assertEqual(result.drop_reason, "single_turn_too_large")

    def test_oversized_reason_not_used_when_every_dropped_turn_could_fit_alone(self):
        """Guards the boundary directly: many ordinary turns dropped, none
        of them individually too big - must stay window_full."""

        turns = self._turns(6)
        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=turns[0].chars * 2
        )

        self.assertGreater(result.turns_dropped, 0)
        for turn in turns[: result.turns_dropped]:
            self.assertLessEqual(turn.chars, turns[0].chars * 2)
        self.assertEqual(result.drop_reason, "window_full")

    # --- the current prompt filling the window --------------------------

    def test_current_prompt_filling_window_reports_its_own_reason(self):
        turns = self._turns(3)
        result = assemble_history(
            turns, current_prompt_chars=999_999, max_messages=20, max_chars=24000
        )

        self.assertEqual(result.turns_included, 0)
        self.assertEqual(result.turns_dropped, 3)
        self.assertEqual(result.chars_dropped, sum(t.chars for t in turns))
        self.assertEqual(result.drop_reason, "current_prompt_fills_window")

    def test_current_prompt_reason_wins_over_oversized_turn(self):
        """Precedence matters: when the current prompt eats the whole
        budget, no historical turn could have fit whatever its size, so
        blaming a past turn would send the user to fix the wrong thing."""

        turns = self._turns(1, user_text="x" * 40_000)
        result = assemble_history(
            turns, current_prompt_chars=24_000, max_messages=20, max_chars=24_000
        )

        self.assertEqual(result.drop_reason, "current_prompt_fills_window")

    def test_no_drop_reason_when_prompt_fills_window_but_there_was_no_history(self):
        """An oversized prompt on turn one dropped nothing - there was
        nothing to drop. Must not claim a trim happened."""

        result = assemble_history(
            [], current_prompt_chars=999_999, max_messages=20, max_chars=24000
        )
        self.assertEqual(result.turns_dropped, 0)
        self.assertIsNone(result.drop_reason)

    # --- additive-only proof --------------------------------------------

    def test_existing_included_fields_unchanged_by_this_brew(self):
        """The v1.5 fields must behave exactly as before in every case -
        this Brew only adds reporting, it never changes what is sent."""

        turns = self._turns(4)
        one_turn_chars = turns[0].chars
        result = assemble_history(
            turns, current_prompt_chars=0, max_messages=20, max_chars=one_turn_chars * 2
        )

        self.assertEqual(result.turns_included, 2)
        self.assertEqual(result.chars_included, one_turn_chars * 2)
        self.assertEqual(result.tokens_est, result.chars_included // 4)
        self.assertEqual(len(result.messages), 4)
        # The surviving messages are the newest turns, oldest-first.
        self.assertEqual(result.messages[0]["content"], turns[2].user_content)


if __name__ == "__main__":
    unittest.main()

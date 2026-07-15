import unittest

from router.app.classifier import (
    Attachment,
    ClassificationResult,
    classify,
    classify_heuristic,
)


class HeuristicTaskTypeTests(unittest.TestCase):
    def test_code_request(self):
        result = classify_heuristic("Implement a function that reverses a string and add a unit test.")
        self.assertEqual(result.task_type, "code")

    def test_refactor_request(self):
        result = classify_heuristic("Please refactor this code to extract method for validation.\n```python\ndef f(): pass\n```")
        self.assertEqual(result.task_type, "refactor")

    def test_doc_request(self):
        result = classify_heuristic("Write documentation and a docstring for this module.")
        self.assertEqual(result.task_type, "doc")

    def test_research_request(self):
        result = classify_heuristic("Can you research and compare the pros and cons of SQLite vs Postgres?")
        self.assertEqual(result.task_type, "research")

    def test_explain_request(self):
        result = classify_heuristic("What does this function do? Explain how it works.")
        self.assertEqual(result.task_type, "explain")

    def test_analysis_request(self):
        result = classify_heuristic("Please analyze this code and find bugs or risk issues.")
        self.assertEqual(result.task_type, "analysis")

    def test_unmatched_text_falls_back_to_default_task_type(self):
        result = classify_heuristic("hello there")
        self.assertEqual(result.task_type, "explain")
        self.assertLess(result.confidence, 0.5)


class ComplexityTests(unittest.TestCase):
    def test_short_request_is_espresso_shot(self):
        result = classify_heuristic("Fix this typo.")
        self.assertEqual(result.complexity, "espresso_shot")

    def test_long_prompt_is_cold_brew(self):
        long_text = "Please review this. " * 100
        result = classify_heuristic(long_text)
        self.assertEqual(result.complexity, "cold_brew")

    def test_multi_step_keyword_is_cold_brew(self):
        result = classify_heuristic("Refactor across the codebase, step by step, every module.")
        self.assertEqual(result.complexity, "cold_brew")

    def test_many_attachments_is_cold_brew(self):
        attachments = [
            Attachment(filename=f"f{i}.py", content_type="text/plain") for i in range(4)
        ]
        result = classify_heuristic("Look at these files.", attachments)
        self.assertEqual(result.complexity, "cold_brew")

    def test_single_attachment_is_also_cold_brew(self):
        """Brew 38 (docs/design/attachments-design.md Section 7, Decision
        3): any attachment at all pushes toward cold_brew, not just
        multiple - simpler and more predictable than a size/kind table."""

        attachments = [Attachment(filename="photo.png", content_type="image/png")]
        result = classify_heuristic("What is this?", attachments)
        self.assertEqual(result.complexity, "cold_brew")

    def test_short_prompt_with_no_attachments_stays_espresso_shot(self):
        """Confirms the new any-attachment rule did not accidentally
        change the no-attachment path."""

        result = classify_heuristic("Fix this typo.", attachments=None)
        self.assertEqual(result.complexity, "espresso_shot")

    def test_long_history_pushes_to_cold_brew(self):
        """Brew 46 (docs/design/conversation-memory-design.md): the new
        COMPLEXITY_SIGNALS entry - only meaningful when the caller passes
        a real history_turn_count (remember_chat was on)."""

        result = classify_heuristic(
            "Fix this typo.", history_turn_count=10, long_history_turns_threshold=10
        )
        self.assertEqual(result.complexity, "cold_brew")

    def test_short_history_stays_espresso_shot(self):
        result = classify_heuristic(
            "Fix this typo.", history_turn_count=3, long_history_turns_threshold=10
        )
        self.assertEqual(result.complexity, "espresso_shot")

    def test_history_turn_count_defaults_to_zero_no_effect(self):
        """A caller that never passes history_turn_count (remember_chat
        off, or every call site before Brew 46) sees no change from this
        signal - the default must be inert."""

        result = classify_heuristic("Fix this typo.")
        self.assertEqual(result.complexity, "espresso_shot")


class VisionTests(unittest.TestCase):
    def test_image_attachment_sets_needs_vision(self):
        attachments = [Attachment(filename="screenshot.png", content_type="image/png")]
        result = classify_heuristic("What is in this screenshot?", attachments)
        self.assertTrue(result.needs_vision)

    def test_no_attachments_needs_vision_false(self):
        result = classify_heuristic("Explain this.")
        self.assertFalse(result.needs_vision)

    def test_text_attachment_does_not_set_needs_vision(self):
        attachments = [Attachment(filename="notes.txt", content_type="text/plain")]
        result = classify_heuristic("Summarize this file.", attachments)
        self.assertFalse(result.needs_vision)


class ModelFallbackTests(unittest.TestCase):
    def test_fallback_not_used_when_disabled(self):
        calls = []

        def fake_model_classify(text):
            calls.append(text)
            return ClassificationResult(
                task_type="research", complexity="cold_brew", needs_vision=False, confidence=0.9
            )

        result = classify(
            "hello there",
            model_fallback_enabled=False,
            model_classify_fn=fake_model_classify,
        )
        self.assertEqual(calls, [])
        self.assertFalse(result.used_model_fallback)

    def test_fallback_used_when_enabled_and_confidence_low(self):
        def fake_model_classify(text):
            return ClassificationResult(
                task_type="research", complexity="cold_brew", needs_vision=False, confidence=0.9
            )

        result = classify(
            "hello there",
            model_fallback_enabled=True,
            model_classify_fn=fake_model_classify,
        )
        self.assertTrue(result.used_model_fallback)
        self.assertEqual(result.task_type, "research")

    def test_fallback_not_used_when_heuristic_confidence_is_high(self):
        calls = []

        def fake_model_classify(text):
            calls.append(text)
            return ClassificationResult(
                task_type="research", complexity="cold_brew", needs_vision=False, confidence=0.9
            )

        result = classify(
            "Implement a function that reverses a string and add a unit test.",
            model_fallback_enabled=True,
            model_classify_fn=fake_model_classify,
        )
        self.assertEqual(calls, [])
        self.assertEqual(result.task_type, "code")


if __name__ == "__main__":
    unittest.main()

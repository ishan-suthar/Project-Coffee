import io
import unittest
from unittest import mock

from roastery.openrouter_client import OpenRouterResult
from roastery.run_cup_test import (
    format_results_table,
    main,
    openrouter_key_available,
    run_cup_test,
)


class RunCupTestTests(unittest.TestCase):
    def test_openrouter_key_available_checks_presence_only(self):
        self.assertFalse(openrouter_key_available({}))
        self.assertTrue(openrouter_key_available({"OPENROUTER_API_KEY": "dummy-key"}))

    def test_main_fails_gracefully_when_key_is_missing(self):
        output = io.StringIO()

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("sys.stdout", output):
                exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertIn("OPENROUTER_API_KEY is not set", output.getvalue())

    def test_run_cup_test_uses_same_order_for_each_bean(self):
        calls = []

        def fake_runner(model, prompt, timeout_seconds):
            calls.append((model, prompt, timeout_seconds))
            return OpenRouterResult(
                model=model,
                response_text="OK",
                latency_seconds=0.1,
                usage={"total_tokens": 4},
                errors=[],
            )

        progress = []
        results = run_cup_test(
            beans=("bean-a", "bean-b"),
            order="same order",
            timeout_seconds=7,
            runner=fake_runner,
            printer=progress.append,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            calls,
            [
                ("bean-a", "same order", 7),
                ("bean-b", "same order", 7),
            ],
        )
        self.assertEqual(progress[0], "Running Bean 1/2: bean-a")
        self.assertEqual(progress[1], "Running Bean 2/2: bean-b")

    def test_format_results_table_includes_status_and_usage(self):
        table = format_results_table(
            [
                OpenRouterResult(
                    model="bean-ok",
                    response_text="abcd",
                    latency_seconds=1.234,
                    usage={"total_tokens": 10},
                    errors=[],
                ),
                OpenRouterResult(
                    model="bean-error",
                    response_text="",
                    latency_seconds=None,
                    usage=None,
                    errors=["failed"],
                ),
            ]
        )

        self.assertIn("bean-ok", table)
        self.assertIn("ok", table)
        self.assertIn("10 total", table)
        self.assertIn("bean-error", table)
        self.assertIn("failed", table)


if __name__ == "__main__":
    unittest.main()

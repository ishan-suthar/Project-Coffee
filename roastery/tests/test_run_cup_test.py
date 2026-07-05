import io
import unittest
from unittest import mock

from roastery.openrouter_client import OpenRouterResult
from roastery.run_cup_test import (
    DEFAULT_BEANS,
    format_results_table,
    main,
    openrouter_key_available,
    run_cup_test,
)


class RunCupTestTests(unittest.TestCase):
    def test_default_beans_use_current_free_slugs(self):
        self.assertEqual(
            DEFAULT_BEANS,
            (
                "qwen/qwen3-coder:free",
                "deepseek/deepseek-r1-0528-qwen3-8b:free",
                "nvidia/nemotron-3-ultra-550b-a55b:free",
            ),
        )

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
            retry_delay_seconds=0,
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
        self.assertEqual(progress[1], "Finished Bean 1/2: ok")
        self.assertEqual(progress[2], "Running Bean 2/2: bean-b")
        self.assertEqual(progress[3], "Finished Bean 2/2: ok")

    def test_run_cup_test_continues_after_runner_error(self):
        def fake_runner(model, prompt, timeout_seconds):
            if model == "bean-error":
                raise RuntimeError("unavailable")
            return OpenRouterResult(
                model=model,
                response_text="OK",
                latency_seconds=0.1,
                usage=None,
                errors=[],
            )

        results = run_cup_test(
            beans=("bean-error", "bean-ok"),
            order="same order",
            runner=fake_runner,
            printer=lambda message: None,
            retry_delay_seconds=0,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].model, "bean-error")
        self.assertIn("Runner error: unavailable", results[0].errors)
        self.assertEqual(results[1].model, "bean-ok")
        self.assertEqual(results[1].errors, [])

    def test_429_transient_error_gets_one_retry(self):
        calls = []

        def fake_runner(model, prompt, timeout_seconds):
            calls.append(model)
            if len(calls) == 1:
                return OpenRouterResult(
                    model=model,
                    response_text="",
                    latency_seconds=0.1,
                    usage=None,
                    errors=["OpenRouter HTTP error 429: Provider returned error"],
                )
            return OpenRouterResult(
                model=model,
                response_text="OK",
                latency_seconds=0.2,
                usage=None,
                errors=[],
            )

        progress = []
        results = run_cup_test(
            beans=("bean-retry",),
            order="same order",
            runner=fake_runner,
            printer=progress.append,
            retry_delay_seconds=0,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(results[0].response_text, "OK")
        self.assertEqual(results[0].errors, [])
        self.assertIn("Retrying Bean 1/1", progress[1])

    def test_404_unavailable_model_does_not_retry(self):
        calls = []

        def fake_runner(model, prompt, timeout_seconds):
            calls.append(model)
            return OpenRouterResult(
                model=model,
                response_text="",
                latency_seconds=0.1,
                usage=None,
                errors=["OpenRouter HTTP error 404: This model is unavailable for free."],
            )

        results = run_cup_test(
            beans=("bean-404",),
            order="same order",
            runner=fake_runner,
            printer=lambda message: None,
            retry_delay_seconds=0,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(results[0].model, "bean-404")
        self.assertIn("HTTP error 404", results[0].errors[0])

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
        self.assertIn("abcd", table)
        self.assertIn("bean-error", table)
        self.assertIn("failed", table)

    def test_main_prints_completion_message_after_run(self):
        output = io.StringIO()
        result = OpenRouterResult(
            model="bean-ok",
            response_text="OK",
            latency_seconds=0.1,
            usage={"total_tokens": 4},
            errors=[],
        )

        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy-key"}, clear=True):
            with mock.patch("roastery.run_cup_test.run_cup_test", return_value=[result]):
                with mock.patch("sys.stdout", output):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Cup Test completed successfully. Ready for Shot 8F.", output.getvalue())


if __name__ == "__main__":
    unittest.main()

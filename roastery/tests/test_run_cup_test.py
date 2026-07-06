import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from roastery.openrouter_client import OpenRouterResult
from roastery.run_cup_test import (
    DEFAULT_BEANS,
    DEFAULT_ORDER,
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
                "poolside/laguna-m.1:free",
                "cohere/north-mini-code:free",
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

    def test_order_file_reads_prompt_content(self):
        output = io.StringIO()
        result = OpenRouterResult(
            model="bean-ok",
            response_text="OK",
            latency_seconds=0.1,
            usage={"total_tokens": 4},
            errors=[],
        )

        with tempfile.TemporaryDirectory() as temp:
            order_file = Path(temp) / "order.md"
            order_file.write_text("# Order\nUse this prompt.\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy-key"}, clear=True):
                with mock.patch("roastery.run_cup_test.run_cup_test", return_value=[result]) as fake_run:
                    with mock.patch("sys.stdout", output):
                        exit_code = main(["--order-file", str(order_file)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_run.call_args.kwargs["order"], "# Order\nUse this prompt.\n")
        self.assertEqual(fake_run.call_args.kwargs["order_file"], order_file.resolve())
        self.assertIn(f"Order file: {order_file.resolve()}", output.getvalue())

    def test_missing_order_file_fails_clearly_before_key_check(self):
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing.md"
            with mock.patch.dict("os.environ", {}, clear=True):
                with mock.patch("sys.stdout", output):
                    exit_code = main(["--order-file", str(missing)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Order file does not exist", output.getvalue())
        self.assertNotIn("OPENROUTER_API_KEY", output.getvalue())

    def test_empty_order_file_fails_clearly_before_key_check(self):
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as temp:
            order_file = Path(temp) / "empty.md"
            order_file.write_text("", encoding="utf-8")
            with mock.patch.dict("os.environ", {}, clear=True):
                with mock.patch("sys.stdout", output):
                    exit_code = main(["--order-file", str(order_file)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Order file is empty", output.getvalue())
        self.assertNotIn("OPENROUTER_API_KEY", output.getvalue())

    def test_list_cup_tests_lists_markdown_files_without_api_key(self):
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as temp:
            cup_test_dir = Path(temp)
            (cup_test_dir / "001-alpha.md").write_text("# Alpha Order\nBody\n", encoding="utf-8")
            (cup_test_dir / "002-beta.md").write_text("# Beta Order\nBody\n", encoding="utf-8")
            (cup_test_dir / "README.md").write_text("# Pack Docs\n", encoding="utf-8")
            (cup_test_dir / "ignore.txt").write_text("# Not Listed\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {}, clear=True):
                with mock.patch("roastery.run_cup_test.run_cup_test") as fake_run:
                    with mock.patch("sys.stdout", output):
                        exit_code = main(
                            [
                                "--list-cup-tests",
                                "--cup-test-dir",
                                str(cup_test_dir),
                            ]
                        )

        self.assertEqual(exit_code, 0)
        fake_run.assert_not_called()
        self.assertIn("001-alpha.md - Alpha Order", output.getvalue())
        self.assertIn("002-beta.md - Beta Order", output.getvalue())
        self.assertNotIn("README.md", output.getvalue())
        self.assertNotIn("ignore.txt", output.getvalue())

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

    def test_default_mode_does_not_write_output_files(self):
        def fake_runner(model, prompt, timeout_seconds):
            return OpenRouterResult(
                model=model,
                response_text="OK",
                latency_seconds=0.1,
                usage={"total_tokens": 4},
                errors=[],
            )

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "outputs"
            run_cup_test(
                beans=("bean-a",),
                order="same order",
                runner=fake_runner,
                printer=lambda message: None,
                retry_delay_seconds=0,
                output_dir=output_dir,
            )

            self.assertFalse(output_dir.exists())

    def test_save_outputs_writes_successful_outputs_and_manifest(self):
        def fake_runner(model, prompt, timeout_seconds):
            return OpenRouterResult(
                model=model,
                response_text=f"full output for {model}",
                latency_seconds=0.1,
                usage={"total_tokens": 4},
                errors=[],
            )

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "outputs"
            progress = []
            run_cup_test(
                beans=("provider/model-a:free", "model-b"),
                order="same order",
                runner=fake_runner,
                printer=progress.append,
                retry_delay_seconds=0,
                save_outputs=True,
                output_dir=output_dir,
                run_id="run-1",
            )

            run_dir = output_dir / "run-1"
            self.assertTrue(run_dir.is_dir())
            self.assertTrue((run_dir / "manifest.json").is_file())
            output_files = sorted(path.name for path in run_dir.glob("*.txt"))
            self.assertEqual(len(output_files), 2)
            self.assertIn("Full outputs saved to:", progress[-1])

    def test_manifest_includes_order_file_when_outputs_are_saved(self):
        def fake_runner(model, prompt, timeout_seconds):
            return OpenRouterResult(
                model=model,
                response_text="full output",
                latency_seconds=0.1,
                usage={"total_tokens": 4},
                errors=[],
            )

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "outputs"
            order_file = Path(temp) / "order.md"
            order_file.write_text("# Order\nPrompt\n", encoding="utf-8")
            run_cup_test(
                beans=("bean-a",),
                order="same order",
                runner=fake_runner,
                printer=lambda message: None,
                retry_delay_seconds=0,
                save_outputs=True,
                output_dir=output_dir,
                run_id="run-1",
                order_file=order_file,
            )

            manifest = json.loads((output_dir / "run-1" / "manifest.json").read_text())
            self.assertEqual(manifest["order_file"], str(order_file))

    def test_manifest_records_failure_without_successful_output_file(self):
        def fake_runner(model, prompt, timeout_seconds):
            if model == "bean-error":
                return OpenRouterResult(
                    model=model,
                    response_text="should not be saved",
                    latency_seconds=None,
                    usage=None,
                    errors=["failed"],
                )
            return OpenRouterResult(
                model=model,
                response_text="success",
                latency_seconds=0.2,
                usage={"total_tokens": 8},
                errors=[],
            )

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "outputs"
            run_cup_test(
                beans=("bean-error", "bean-ok"),
                order="same order",
                runner=fake_runner,
                printer=lambda message: None,
                retry_delay_seconds=0,
                save_outputs=True,
                output_dir=output_dir,
                run_id="run-1",
            )

            manifest = json.loads((output_dir / "run-1" / "manifest.json").read_text())
            error_entry = manifest["beans"][0]
            ok_entry = manifest["beans"][1]
            self.assertEqual(error_entry["status"], "error")
            self.assertEqual(error_entry["error"], "failed")
            self.assertIsNone(error_entry["output_file"])
            self.assertEqual(ok_entry["status"], "ok")
            self.assertIsNotNone(ok_entry["output_file"])
            self.assertEqual(len(list((output_dir / "run-1").glob("*.txt"))), 1)

    def test_output_filenames_are_safe(self):
        def fake_runner(model, prompt, timeout_seconds):
            return OpenRouterResult(
                model=model,
                response_text="OK",
                latency_seconds=0.1,
                usage=None,
                errors=[],
            )

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "outputs"
            run_cup_test(
                beans=("provider/model:name with spaces",),
                order="same order",
                runner=fake_runner,
                printer=lambda message: None,
                retry_delay_seconds=0,
                save_outputs=True,
                output_dir=output_dir,
                run_id="run-1",
            )

            output_files = list((output_dir / "run-1").glob("*.txt"))
            self.assertEqual(len(output_files), 1)
            name = output_files[0].name
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertNotIn(":", name)
            self.assertIn("provider-model-name-with-spaces", name)

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

    def test_main_uses_default_order_when_order_file_is_not_provided(self):
        output = io.StringIO()
        result = OpenRouterResult(
            model="bean-ok",
            response_text="OK",
            latency_seconds=0.1,
            usage={"total_tokens": 4},
            errors=[],
        )

        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy-key"}, clear=True):
            with mock.patch("roastery.run_cup_test.run_cup_test", return_value=[result]) as fake_run:
                with mock.patch("sys.stdout", output):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_run.call_args.kwargs["order"], DEFAULT_ORDER)
        self.assertIsNone(fake_run.call_args.kwargs["order_file"])
        self.assertIn("Order file: built-in default Order", output.getvalue())

    def test_main_accepts_capture_flags_without_changing_table_output(self):
        output = io.StringIO()
        result = OpenRouterResult(
            model="bean-ok",
            response_text="OK",
            latency_seconds=0.1,
            usage={"total_tokens": 4},
            errors=[],
        )

        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy-key"}, clear=True):
                with mock.patch("roastery.run_cup_test.run_cup_test", return_value=[result]) as fake_run:
                    with mock.patch("sys.stdout", output):
                        exit_code = main(
                            [
                                "--save-outputs",
                                "--output-dir",
                                str(Path(temp) / "outputs"),
                                "--run-id",
                                "run-1",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        fake_run.assert_called_once()
        self.assertTrue(fake_run.call_args.kwargs["save_outputs"])
        self.assertIn("bean-ok", output.getvalue())


if __name__ == "__main__":
    unittest.main()

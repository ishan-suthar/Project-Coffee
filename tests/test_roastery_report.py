import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import roastery_report


class RoasteryReportTests(unittest.TestCase):
    def write_manifest(
        self,
        run_dir: Path,
        *,
        run_id: str = "run-1",
        beans: list[dict] | None = None,
    ) -> Path:
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": run_id,
            "created_at": "2026-07-06T00:00:00+00:00",
            "output_dir": str(run_dir),
            "order_file": str(run_dir / "order.md"),
            "order_sha256": "abc123",
            "beans": beans
            if beans is not None
            else [
                {
                    "bean": "bean-ok",
                    "status": "ok",
                    "latency_seconds": 0.25,
                    "usage": {"total_tokens": 42, "cost": 0},
                    "error": None,
                    "output_file": None,
                }
            ],
        }
        path = run_dir / "manifest.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_tool(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = roastery_report.run(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_single_run_manifest_produces_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            self.write_manifest(run_dir)

            code, stdout, stderr = self.run_tool("--run-dir", str(run_dir))

            self.assertEqual(code, 0, stderr)
            self.assertIn("# Roastery Report Draft", stdout)
            self.assertIn("run-1", stdout)
            self.assertIn("bean-ok", stdout)
            self.assertIn("Human Scoring TODO", stdout)

    def test_parent_directory_with_multiple_runs_produces_combined_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            self.write_manifest(parent / "run-a", run_id="run-a")
            self.write_manifest(parent / "run-b", run_id="run-b")

            code, stdout, stderr = self.run_tool("--run-dir", str(parent))

            self.assertEqual(code, 0, stderr)
            self.assertIn("run-a", stdout)
            self.assertIn("run-b", stdout)

    def test_json_output_is_valid_and_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            self.write_manifest(run_dir)

            code, stdout, stderr = self.run_tool("--run-dir", str(run_dir), "--json")

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["run_count"], 1)
            self.assertEqual(payload["runs"][0]["run_id"], "run-1")
            self.assertEqual(payload["runs"][0]["beans"][0]["bean"], "bean-ok")

    def test_missing_run_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"

            code, stdout, stderr = self.run_tool("--run-dir", str(missing))

            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Run directory does not exist", stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            run_dir.mkdir()

            code, stdout, stderr = self.run_tool("--run-dir", str(run_dir))

            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Manifest not found", stderr)

    def test_previews_are_capped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            output_file = run_dir / "bean.txt"
            output_file.parent.mkdir(parents=True)
            output_file.write_text("x" * 100, encoding="utf-8")
            self.write_manifest(
                run_dir,
                beans=[
                    {
                        "bean": "bean-ok",
                        "status": "ok",
                        "latency_seconds": 0.25,
                        "usage": {"total_tokens": 42, "cost": 0},
                        "error": None,
                        "output_file": str(output_file),
                    }
                ],
            )

            code, stdout, stderr = self.run_tool(
                "--run-dir",
                str(run_dir),
                "--include-previews",
                "--max-preview-chars",
                "20",
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("xxxxxxxxxxxxxxxxx...", stdout)
            self.assertNotIn("x" * 30, stdout)

    def test_previews_are_omitted_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            output_file = run_dir / "bean.txt"
            output_file.parent.mkdir(parents=True)
            output_file.write_text("full raw output text", encoding="utf-8")
            self.write_manifest(
                run_dir,
                beans=[
                    {
                        "bean": "bean-ok",
                        "status": "ok",
                        "latency_seconds": 0.25,
                        "usage": {"total_tokens": 42, "cost": 0},
                        "error": None,
                        "output_file": str(output_file),
                    }
                ],
            )

            code, stdout, stderr = self.run_tool("--run-dir", str(run_dir))

            self.assertEqual(code, 0, stderr)
            self.assertIn("Previews omitted by default", stdout)
            self.assertNotIn("full raw output text", stdout)

    def test_errors_are_included_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            self.write_manifest(
                run_dir,
                beans=[
                    {
                        "bean": "bean-error",
                        "status": "error",
                        "latency_seconds": None,
                        "usage": None,
                        "error": "provider failed",
                        "output_file": None,
                    }
                ],
            )

            code, stdout, stderr = self.run_tool("--run-dir", str(run_dir))

            self.assertEqual(code, 0, stderr)
            self.assertIn("provider failed", stdout)
            self.assertIn("Error Summary", stdout)

    def test_tool_does_not_require_openrouter_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run-1"
            self.write_manifest(run_dir)

            with mock.patch.dict(os.environ, {}, clear=True):
                code, stdout, stderr = self.run_tool("--run-dir", str(run_dir))

            self.assertEqual(code, 0, stderr)
            self.assertIn("run-1", stdout)

    def test_output_file_is_written_when_output_is_provided(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run-1"
            self.write_manifest(run_dir)
            output = root / "draft.md"

            code, stdout, stderr = self.run_tool(
                "--run-dir",
                str(run_dir),
                "--output",
                str(output),
            )

            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, "")
            self.assertTrue(output.is_file())
            self.assertIn("# Roastery Report Draft", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

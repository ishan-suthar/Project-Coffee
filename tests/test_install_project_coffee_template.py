import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.install_project_coffee_template import DOCTOR_FILES, ONBOARDING_FILES, run


class InstallProjectCoffeeTemplateTests(unittest.TestCase):
    def make_template(self, root: Path) -> Path:
        template = root / "templates" / "project-coffee"
        for relative_path in ONBOARDING_FILES:
            path = template / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"template: {relative_path}\n", encoding="utf-8")
        (template / "README.md").write_text("pack docs\n", encoding="utf-8")
        return template

    def run_tool(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = run(list(args))
        return code, stdout.getvalue()

    def create_doctor_files(self, target: Path, files: tuple[str, ...] = DOCTOR_FILES) -> None:
        for relative_path in files:
            path = target / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"doctor: {relative_path}\n", encoding="utf-8")

    def test_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)
            target = root / "target"
            target.mkdir()

            code, output = self.run_tool("--target", str(target), "--template", str(template))

            self.assertEqual(code, 0, output)
            self.assertIn("Dry-run complete", output)
            self.assertFalse((target / "AGENTS.md").exists())

    def test_apply_creates_expected_template_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)
            target = root / "target"
            target.mkdir()

            code, output = self.run_tool(
                "--target",
                str(target),
                "--template",
                str(template),
                "--apply",
            )

            self.assertEqual(code, 0, output)
            for relative_path in ONBOARDING_FILES:
                self.assertTrue((target / relative_path).is_file(), relative_path)
            self.assertFalse((target / "README.md").exists())

    def test_existing_files_are_skipped_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)
            target = root / "target"
            target.mkdir()
            existing = target / "AGENTS.md"
            existing.write_text("keep me\n", encoding="utf-8")

            code, output = self.run_tool(
                "--target",
                str(target),
                "--template",
                str(template),
                "--apply",
            )

            self.assertEqual(code, 0, output)
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep me\n")
            self.assertIn("AGENTS.md", output)
            self.assertIn("Files to skip", output)

    def test_force_overwrites_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)
            target = root / "target"
            target.mkdir()
            existing = target / "AGENTS.md"
            existing.write_text("replace me\n", encoding="utf-8")

            code, output = self.run_tool(
                "--target",
                str(target),
                "--template",
                str(template),
                "--apply",
                "--force",
            )

            self.assertEqual(code, 0, output)
            self.assertEqual(existing.read_text(encoding="utf-8"), "template: AGENTS.md\n")
            self.assertIn("Files that would overwrite only with --force", output)

    def test_missing_target_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)

            code, output = self.run_tool(
                "--target",
                str(root / "missing"),
                "--template",
                str(template),
            )

            self.assertNotEqual(code, 0)
            self.assertIn("Target does not exist", output)

    def test_missing_template_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()

            code, output = self.run_tool(
                "--target",
                str(target),
                "--template",
                str(root / "missing-template"),
            )

            self.assertNotEqual(code, 0)
            self.assertIn("Template does not exist", output)

    def test_generated_summary_includes_create_and_skip_information(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = self.make_template(root)
            target = root / "target"
            target.mkdir()
            (target / "AGENTS.md").write_text("existing\n", encoding="utf-8")

            code, output = self.run_tool("--target", str(target), "--template", str(template))

            self.assertEqual(code, 0, output)
            self.assertIn("Files to create", output)
            self.assertIn("Files to skip", output)
            self.assertIn("AGENTS.md", output)
            self.assertIn("PROJECT_COFFEE.md", output)

    def test_check_complete_target_returns_complete_and_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            self.create_doctor_files(target)

            code, output = self.run_tool("--check", "--target", str(target))

            self.assertEqual(code, 0, output)
            self.assertIn("FOUND files", output)
            self.assertIn("MISSING files", output)
            self.assertIn("COMPLETE", output)

    def test_check_incomplete_target_returns_incomplete_and_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            self.create_doctor_files(target, files=("AGENTS.md",))

            code, output = self.run_tool("--check", "--target", str(target))

            self.assertEqual(code, 2, output)
            self.assertIn("INCOMPLETE", output)

    def test_check_missing_target_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            code, output = self.run_tool("--check", "--target", str(root / "missing"))

            self.assertNotEqual(code, 0)
            self.assertIn("Target does not exist", output)

    def test_check_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()

            code, output = self.run_tool("--check", "--target", str(target))

            self.assertEqual(code, 2, output)
            self.assertIn("INCOMPLETE", output)
            self.assertEqual(list(target.rglob("*")), [])

    def test_check_output_lists_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            self.create_doctor_files(target, files=("AGENTS.md",))

            code, output = self.run_tool("--check", "--target", str(target))

            self.assertEqual(code, 2, output)
            self.assertIn("PROJECT_COFFEE.md", output)
            self.assertIn("brew-log/active_context.md", output)


if __name__ == "__main__":
    unittest.main()

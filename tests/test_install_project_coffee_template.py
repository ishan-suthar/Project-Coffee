import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.install_project_coffee_template import ONBOARDING_FILES, run


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


if __name__ == "__main__":
    unittest.main()

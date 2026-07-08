import io
import os
from pathlib import Path
import unittest
from unittest import mock

from tools import coffee


class FakeCompletedProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


class CoffeeCliTests(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        returncode: int = 0,
        script_exists: bool = True,
    ) -> tuple[int, str, str, list[list[str]]]:
        commands: list[list[str]] = []
        stdout = io.StringIO()
        stderr = io.StringIO()

        def fake_runner(command: list[str]) -> FakeCompletedProcess:
            commands.append(command)
            return FakeCompletedProcess(returncode)

        code = coffee.run(
            list(args),
            runner=fake_runner,
            script_exists=lambda _path: script_exists,
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue(), commands

    def assert_delegates_to(
        self,
        commands: list[list[str]],
        script_name: str,
        expected_args: list[str],
    ) -> None:
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertTrue(command[0].endswith("python.exe") or Path(command[0]).name.startswith("python"))
        self.assertEqual(Path(command[1]).name, script_name)
        self.assertEqual(command[2:], expected_args)

    def test_help_works(self) -> None:
        code, stdout, stderr, commands = self.run_cli("--help")

        self.assertEqual(code, 0, stderr)
        self.assertIn("dashboard", stdout)
        self.assertIn("doctor", stdout)
        self.assertIn("pantry-search", stdout)
        self.assertIn("ledger-summary", stdout)
        self.assertEqual(commands, [])

    def test_version_works(self) -> None:
        code, stdout, stderr, commands = self.run_cli("--version")

        self.assertEqual(code, 0, stderr)
        self.assertIn("Project Coffee CLI", stdout)
        self.assertEqual(commands, [])

    def test_dashboard_subcommand_delegates_correctly(self) -> None:
        code, stdout, stderr, commands = self.run_cli("dashboard", "--root", ".")

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")
        self.assert_delegates_to(commands, "coffee_dashboard.py", ["--root", "."])

    def test_doctor_subcommand_delegates_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli("doctor", "--root", ".")

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(commands, "coffee_doctor.py", ["--root", "."])

    def test_dashboard_section_forwards_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "dashboard",
            "--root",
            ".",
            "--section",
            "tools",
            "--fail-on-missing",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "coffee_dashboard.py",
            ["--root", ".", "--section", "tools", "--fail-on-missing"],
        )

    def test_doctor_section_forwards_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "doctor",
            "--root",
            ".",
            "--section",
            "ignored-paths",
            "--fail-on-issue",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "coffee_doctor.py",
            ["--root", ".", "--section", "ignored-paths", "--fail-on-issue"],
        )

    def test_dashboard_json_forwards_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli("dashboard", "--root", ".", "--json")

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(commands, "coffee_dashboard.py", ["--root", ".", "--json"])

    def test_doctor_json_forwards_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli("doctor", "--root", ".", "--json")

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(commands, "coffee_doctor.py", ["--root", ".", "--json"])

    def test_pantry_search_forwards_query_and_max_results(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "pantry-search",
            "--root",
            "docs",
            "--query",
            "House Blend",
            "--max-results",
            "3",
            "--json",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "pantry_search.py",
            ["--root", "docs", "--query", "House Blend", "--max-results", "3", "--json"],
        )

    def test_roastery_report_forwards_run_dir_json_and_output(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "roastery-report",
            "--run-dir",
            "roastery/local_cup_outputs/latest",
            "--output",
            "roastery/local_reports/latest.md",
            "--json",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "roastery_report.py",
            [
                "--run-dir",
                "roastery/local_cup_outputs/latest",
                "--output",
                "roastery/local_reports/latest.md",
                "--json",
            ],
        )

    def test_template_install_forwards_apply_and_force(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "install-template",
            "--target",
            "scratch",
            "--apply",
            "--force",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "install_project_coffee_template.py",
            ["--target", "scratch", "--apply", "--force"],
        )

    def test_check_onboarding_uses_existing_installer_check_mode(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "check-onboarding",
            "--target",
            "scratch",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "install_project_coffee_template.py",
            ["--target", "scratch", "--check"],
        )

    def test_ledger_summary_delegates_correctly(self) -> None:
        code, _stdout, stderr, commands = self.run_cli(
            "ledger-summary",
            "--root",
            ".",
            "--from",
            "2026-07-01",
            "--to",
            "2026-07-08",
            "--max-entries",
            "4",
            "--json",
        )

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(
            commands,
            "ledger_summary.py",
            [
                "--root",
                ".",
                "--from",
                "2026-07-01",
                "--to",
                "2026-07-08",
                "--max-entries",
                "4",
                "--json",
            ],
        )

    def test_missing_delegated_tool_returns_nonzero_and_helpful_error(self) -> None:
        code, stdout, stderr, commands = self.run_cli(
            "dashboard",
            "--root",
            ".",
            script_exists=False,
        )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Delegated tool is missing", stderr)
        self.assertEqual(commands, [])

    def test_cli_does_not_require_openrouter_api_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _stdout, stderr, commands = self.run_cli("doctor", "--root", ".")

        self.assertEqual(code, 0, stderr)
        self.assert_delegates_to(commands, "coffee_doctor.py", ["--root", "."])

    def test_subcommand_return_code_is_preserved(self) -> None:
        code, _stdout, _stderr, commands = self.run_cli("doctor", "--root", ".", returncode=7)

        self.assertEqual(code, 7)
        self.assertEqual(len(commands), 1)


if __name__ == "__main__":
    unittest.main()

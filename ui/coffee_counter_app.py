"""Streamlit Coffee Counter MVP.

The command adapter in this module is intentionally importable without
Streamlit installed. Streamlit is imported only inside the UI rendering path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
COFFEE_CLI = REPO_ROOT / "tools" / "coffee.py"
DEFAULT_TIMEOUT_SECONDS = 45

ALLOWED_ACTIONS = {
    "dashboard": "Dashboard",
    "doctor": "Doctor",
    "release-check": "Release Check",
    "ledger-summary": "Ledger Summary",
    "evidence-bundle": "Evidence Bundle",
    "fleet-status": "Fleet Status",
}


Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


class CommandAdapterError(ValueError):
    """Raised when the UI tries to build an unsafe or invalid command."""


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False


def default_project_root() -> Path:
    return REPO_ROOT


def validate_root(root: str | Path) -> Path:
    root_path = Path(root).expanduser()
    if not root_path.is_absolute():
        root_path = (Path.cwd() / root_path).resolve()
    else:
        root_path = root_path.resolve()
    if not root_path.exists():
        raise CommandAdapterError(f"Project root does not exist: {root_path}")
    if not root_path.is_dir():
        raise CommandAdapterError(f"Project root is not a directory: {root_path}")
    return root_path


def validate_positive_int(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if value < 1:
        raise CommandAdapterError(f"{name} must be at least 1.")
    return value


def build_command(
    action: str,
    *,
    root: str | Path | None = None,
    query: str | None = None,
    max_results: int | None = None,
    max_entries: int | None = None,
    registry: str | None = None,
    json_output: bool = False,
) -> list[str]:
    if action not in ALLOWED_ACTIONS:
        raise CommandAdapterError(f"Command is not allowlisted: {action}")

    root_path = validate_root(root or default_project_root())
    args = [sys.executable, str(COFFEE_CLI), action, "--root", str(root_path)]

    if action == "evidence-bundle":
        if not query or not query.strip():
            raise CommandAdapterError("Evidence Bundle query is required.")
        args.extend(["--query", query])
        max_results = validate_positive_int(max_results, "max_results")
        if max_results is not None:
            args.extend(["--max-results", str(max_results)])
        if json_output:
            args.append("--json")

    if action == "ledger-summary":
        max_entries = validate_positive_int(max_entries, "max_entries")
        if max_entries is not None:
            args.extend(["--max-entries", str(max_entries)])

    if action == "fleet-status" and registry:
        args.extend(["--registry", registry])

    return args


def default_runner(args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )


def run_coffee_command(
    action: str,
    *,
    root: str | Path | None = None,
    query: str | None = None,
    max_results: int | None = None,
    max_entries: int | None = None,
    registry: str | None = None,
    json_output: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    runner: Runner = default_runner,
) -> CommandResult:
    args = build_command(
        action,
        root=root,
        query=query,
        max_results=max_results,
        max_entries=max_entries,
        registry=registry,
        json_output=json_output,
    )

    try:
        completed = runner(args, timeout)
    except subprocess.TimeoutExpired:
        return CommandResult(
            args=args,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds.",
            return_code=124,
            timed_out=True,
        )
    except OSError as exc:
        return CommandResult(
            args=args,
            stdout="",
            stderr=str(exc),
            return_code=1,
        )

    return CommandResult(
        args=args,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        return_code=completed.returncode,
    )


def format_command(args: Sequence[str]) -> str:
    return subprocess.list2cmdline(list(args))


def render_app() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Install it with: python -m pip install streamlit"
        ) from exc

    st.set_page_config(page_title="Project Coffee Counter", layout="wide")
    st.title("Project Coffee Counter")
    st.caption("Local-first Project Coffee control panel. No remote model calls in this MVP.")

    with st.sidebar:
        st.header("Counter")
        root_input = st.text_input("Project root", value=str(default_project_root()))
        selected_action = st.selectbox(
            "Selected tool/action",
            options=list(ALLOWED_ACTIONS.keys()),
            format_func=lambda value: ALLOWED_ACTIONS[value],
        )
        max_results = st.number_input("Evidence max results", min_value=1, max_value=50, value=5)
        st.info(
            "Local-only MVP. Secrets and raw local outputs are excluded. "
            "Remote Bean calls, file edits, and Git writes are disabled."
        )

    tabs = st.tabs(
        [
            "Home / Overview",
            "Ask Coffee",
            "Evidence Bundle",
            "Ledger",
            "Fleet",
            "Safety / Commands",
        ]
    )

    with tabs[0]:
        render_home_tab(st, root_input)

    with tabs[1]:
        render_ask_tab(st, root_input, int(max_results))

    with tabs[2]:
        render_evidence_tab(st, root_input, int(max_results))

    with tabs[3]:
        render_ledger_tab(st, root_input)

    with tabs[4]:
        render_fleet_tab(st, root_input)

    with tabs[5]:
        render_safety_tab(st, selected_action)


def render_home_tab(st: object, root: str) -> None:
    st.subheader("Home / Overview")
    st.write("Run local Project Coffee status tools. Outputs stay on this machine.")
    columns = st.columns(4)
    actions = ["dashboard", "doctor", "release-check", "fleet-status"]
    for column, action in zip(columns, actions):
        with column:
            if st.button(ALLOWED_ACTIONS[action], key=f"home-{action}"):
                result = safe_run_for_ui(st, action, root=root)
                display_result(st, result, ALLOWED_ACTIONS[action])


def render_ask_tab(st: object, root: str, default_max_results: int) -> None:
    st.subheader("Ask Coffee - local only")
    st.info("This MVP retrieves local evidence only; it does not call a model.")
    question = st.text_area("Question or Coffee Order", height=140)
    max_results = st.number_input(
        "Max evidence results",
        min_value=1,
        max_value=50,
        value=default_max_results,
        key="ask-max-results",
    )
    if st.button("Build local evidence bundle"):
        if not question.strip():
            st.warning("Enter a question or Order first.")
        else:
            result = safe_run_for_ui(
                st,
                "evidence-bundle",
                root=root,
                query=question,
                max_results=int(max_results),
            )
            display_result(st, result, "Local Evidence Bundle")
            st.caption("Coffee can draft commands, but you review and run commits.")


def render_evidence_tab(st: object, root: str, default_max_results: int) -> None:
    st.subheader("Evidence Bundle")
    query = st.text_input("Evidence query", value="current Brew next Shot")
    max_results = st.number_input(
        "Max results",
        min_value=1,
        max_value=50,
        value=default_max_results,
        key="evidence-max-results",
    )
    json_output = st.checkbox("JSON output", value=False)
    if st.button("Run evidence-bundle"):
        result = safe_run_for_ui(
            st,
            "evidence-bundle",
            root=root,
            query=query,
            max_results=int(max_results),
            json_output=json_output,
        )
        display_result(st, result, "Evidence Bundle")


def render_ledger_tab(st: object, root: str) -> None:
    st.subheader("Ledger")
    max_entries = st.number_input("Max recent entries", min_value=1, max_value=50, value=8)
    if st.button("Run ledger-summary"):
        result = safe_run_for_ui(
            st,
            "ledger-summary",
            root=root,
            max_entries=int(max_entries),
        )
        display_result(st, result, "Ledger Summary")


def render_fleet_tab(st: object, root: str) -> None:
    st.subheader("Fleet")
    registry = st.text_input("Optional registry path", value="")
    if st.button("Run fleet-status"):
        result = safe_run_for_ui(
            st,
            "fleet-status",
            root=root,
            registry=registry.strip() or None,
        )
        display_result(st, result, "Fleet Status")


def render_safety_tab(st: object, selected_action: str) -> None:
    st.subheader("Safety / Commands")
    st.write("Allowlisted commands:")
    for action, label in ALLOWED_ACTIONS.items():
        st.code(f"python tools/coffee.py {action} --root PATH", language="text")
        if action == selected_action:
            st.caption(f"Selected: {label}")

    st.write("Non-goals for this MVP:")
    st.markdown(
        """
- no remote model calls
- no OpenRouter calls
- no external API calls
- no file editing from the UI
- no raw Roastery output inspection
- no staging, commits, pushes, or tags
- no arbitrary shell commands
"""
    )

    st.write("Approval gate reminders:")
    st.markdown(
        """
- Remote Bean calls require approval.
- Sending local evidence to a remote Bean requires approval.
- Git operations require human review and approval.
- Dependency installs require approval.
- Secrets and raw local outputs are excluded.
"""
    )


def safe_run_for_ui(st: object, action: str, **kwargs: object) -> CommandResult | None:
    try:
        return run_coffee_command(action, **kwargs)
    except CommandAdapterError as exc:
        st.error(str(exc))
        return None


def display_result(st: object, result: CommandResult | None, title: str) -> None:
    if result is None:
        return
    st.write(f"**{title}**")
    st.code(format_command(result.args), language="text")
    st.write(f"Exit code: `{result.return_code}`")
    if result.timed_out:
        st.warning("Command timed out.")
    with st.expander("stdout", expanded=True):
        st.code(result.stdout or "(empty)", language="text")
    with st.expander("stderr", expanded=bool(result.stderr)):
        st.code(result.stderr or "(empty)", language="text")


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()

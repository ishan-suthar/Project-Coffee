"""Streamlit Coffee Counter MVP.

The command adapter in this module is intentionally importable without
Streamlit installed. Streamlit is imported only inside the UI rendering path.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Sequence


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


@dataclass(frozen=True)
class EvidenceItem:
    source_path: str
    heading: str
    snippet: str
    reason_selected: str
    score: int
    freshness_signal: str
    safety_classification: str
    line_start: int | None = None
    line_end: int | None = None

    @property
    def reference(self) -> str:
        if self.line_start is None:
            return self.source_path
        if self.line_end is not None and self.line_end != self.line_start:
            return f"{self.source_path}:{self.line_start}-{self.line_end}"
        return f"{self.source_path}:{self.line_start}"


@dataclass(frozen=True)
class EvidenceBundle:
    query: str
    total_matches: int
    items: list[EvidenceItem]
    warnings: list[str]
    parse_error: str | None = None


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


def format_display_command(args: Sequence[str]) -> str:
    return subprocess.list2cmdline(list(args))


def format_command(args: Sequence[str]) -> str:
    return format_display_command(args)


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    parsed = _as_int(value, default=-1)
    if parsed < 0:
        return None
    return parsed


def parse_evidence_bundle_json(text: str) -> EvidenceBundle:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return EvidenceBundle(
            query="",
            total_matches=0,
            items=[],
            warnings=[],
            parse_error=f"JSON parse error: {exc.msg}",
        )

    if not isinstance(payload, dict):
        return EvidenceBundle(
            query="",
            total_matches=0,
            items=[],
            warnings=[],
            parse_error="JSON parse error: expected an object.",
        )

    raw_items = payload.get("bundle", [])
    if not isinstance(raw_items, list):
        raw_items = []

    items: list[EvidenceItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        items.append(
            EvidenceItem(
                source_path=str(raw_item.get("source_path", "")),
                heading=str(raw_item.get("heading", "")),
                snippet=str(raw_item.get("snippet", "")),
                reason_selected=str(raw_item.get("reason_selected", "")),
                score=_as_int(raw_item.get("score"), default=0),
                freshness_signal=str(raw_item.get("freshness_signal", "")),
                safety_classification=str(raw_item.get("safety_classification", "")),
                line_start=_as_optional_int(raw_item.get("line_start")),
                line_end=_as_optional_int(raw_item.get("line_end")),
            )
        )

    raw_warnings = payload.get("warnings", [])
    warnings = [str(item) for item in raw_warnings] if isinstance(raw_warnings, list) else []
    total_matches = _as_int(payload.get("total_matches"), default=len(items))
    return EvidenceBundle(
        query=str(payload.get("query", "")),
        total_matches=total_matches,
        items=items,
        warnings=warnings,
    )


def evidence_state(bundle: EvidenceBundle, return_code: int = 0) -> str:
    if return_code != 0:
        return "command-error"
    if bundle.parse_error:
        return "json-parse-error"
    if bundle.total_matches == 0 or not bundle.items:
        return "no-evidence"
    return "success"


def build_local_evidence_draft(question: str, bundle: EvidenceBundle, *, max_items: int = 3) -> str:
    title = "Local evidence draft, not model-generated"
    cleaned_question = question.strip() or "(no question provided)"
    lines = [title, "", f"Question or Order: {cleaned_question}", ""]

    state = evidence_state(bundle)
    if state == "json-parse-error":
        lines.extend(
            [
                "Evidence status: unable to parse Evidence Bundle JSON.",
                f"Parser note: {bundle.parse_error}",
                "",
                "Draft: Evidence is insufficient until the JSON output is inspected.",
            ]
        )
        return "\n".join(lines)

    if state == "no-evidence":
        lines.extend(
            [
                "Evidence status: no local evidence matched the query.",
                "",
                "Draft: Evidence is insufficient. Refine the query, narrow the source, or run a local validation command before answering.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"Evidence status: {bundle.total_matches} local match(es) found; using top {min(max_items, len(bundle.items))}.",
            "",
            "Grounded notes:",
        ]
    )
    for index, item in enumerate(bundle.items[:max_items], start=1):
        heading = item.heading or "(no heading)"
        snippet = item.snippet or "(no snippet)"
        lines.append(f"{index}. {item.reference} - {heading}: {snippet}")

    lines.extend(
        [
            "",
            "Draft: Use the grounded notes above as the answer basis. Verify the cited local files before treating this as final.",
            "",
            "No model call was made.",
        ]
    )
    return "\n".join(lines)


def evidence_table_rows(bundle: EvidenceBundle) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in bundle.items:
        rows.append(
            {
                "Source": item.reference,
                "Heading": item.heading,
                "Score": item.score,
                "Freshness": item.freshness_signal,
                "Safety": item.safety_classification,
                "Snippet": item.snippet,
            }
        )
    return rows


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
    render_evidence_safety_notice(st)
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
                json_output=True,
            )
            display_result(st, result, "Local Evidence Bundle", expand_stdout=False)
            if result is not None:
                bundle = parse_evidence_bundle_json(result.stdout)
                render_evidence_bundle_summary(st, bundle, result.return_code)
                st.subheader("Local evidence draft")
                st.caption("Local evidence draft, not model-generated. No model call was made.")
                if result.return_code == 0:
                    st.code(build_local_evidence_draft(question, bundle), language="markdown")
                else:
                    st.warning("Evidence command failed, so no local evidence draft was created.")
            st.caption("Coffee can draft commands, but you review and run commits.")


def render_evidence_tab(st: object, root: str, default_max_results: int) -> None:
    st.subheader("Evidence Bundle")
    render_evidence_safety_notice(st)
    query = st.text_input("Evidence query", value="current Brew next Shot")
    max_results = st.number_input(
        "Max results",
        min_value=1,
        max_value=50,
        value=default_max_results,
        key="evidence-max-results",
    )
    if st.button("Run evidence-bundle"):
        markdown_result = safe_run_for_ui(
            st,
            "evidence-bundle",
            root=root,
            query=query,
            max_results=int(max_results),
        )
        display_result(st, markdown_result, "Evidence Bundle Markdown")

        json_result = safe_run_for_ui(
            st,
            "evidence-bundle",
            root=root,
            query=query,
            max_results=int(max_results),
            json_output=True,
        )
        display_result(st, json_result, "Evidence Bundle JSON", expand_stdout=False)
        if json_result is not None:
            bundle = parse_evidence_bundle_json(json_result.stdout)
            render_evidence_bundle_summary(st, bundle, json_result.return_code)


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


def render_evidence_safety_notice(st: object) -> None:
    st.info(
        "Local evidence only. Evidence is retrieved from allowlisted local Project Coffee "
        "sources; excluded paths are not searched. Remote Bean calls remain disabled in Brew 28."
    )


def render_evidence_bundle_summary(
    st: object,
    bundle: EvidenceBundle,
    return_code: int,
) -> None:
    state = evidence_state(bundle, return_code)
    if state == "success":
        st.success(f"Evidence found: {bundle.total_matches} local match(es). No model call was made.")
    elif state == "no-evidence":
        st.warning("No local evidence matched this query. No model call was made.")
    elif state == "json-parse-error":
        st.error(f"Evidence JSON could not be parsed: {bundle.parse_error}")
    else:
        st.error("Evidence command returned a nonzero exit code.")

    for warning in bundle.warnings:
        st.warning(warning)

    if bundle.items:
        st.write("Top evidence items")
        st.dataframe(evidence_table_rows(bundle), width="stretch")
        for index, item in enumerate(bundle.items[:5], start=1):
            with st.expander(f"{index}. {item.reference} - {item.heading or '(no heading)'}"):
                st.write(f"Score: `{item.score}`")
                st.write(f"Freshness: `{item.freshness_signal or 'unknown'}`")
                st.write(f"Safety: `{item.safety_classification or 'unknown'}`")
                st.write(f"Reason: {item.reason_selected or '(none recorded)'}")
                st.code(item.snippet or "(no snippet)", language="markdown")


def safe_run_for_ui(st: object, action: str, **kwargs: object) -> CommandResult | None:
    try:
        return run_coffee_command(action, **kwargs)
    except CommandAdapterError as exc:
        st.error(str(exc))
        return None


def display_result(
    st: object,
    result: CommandResult | None,
    title: str,
    *,
    expand_stdout: bool = True,
) -> None:
    if result is None:
        return
    st.write(f"**{title}**")
    st.code(format_display_command(result.args), language="text")
    st.write(f"Exit code: `{result.return_code}`")
    if result.timed_out:
        st.warning("Command timed out.")
    if result.return_code == 0 and not result.timed_out:
        st.success("Command completed.")
    else:
        st.error("Command did not complete cleanly.")
    with st.expander("stdout", expanded=expand_stdout):
        st.code(result.stdout or "(empty)", language="text")
    with st.expander("stderr", expanded=bool(result.stderr)):
        st.code(result.stderr or "(empty)", language="text")


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()

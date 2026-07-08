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

CURRENT_STATE_FILES = [
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "ROADMAP.md",
    "CHANGELOG.md",
]

CURRENT_STATE_TERMS = [
    "current brew",
    "current shot",
    "next shot",
    "what should i do next",
    "what do i do next",
    "what is next",
    "blockers",
    "where are we",
    "current status",
    "project status",
]

PROJECT_ROOT_MARKERS = [
    "tools/coffee.py",
    "brew-log",
    "brew-log/active_context.md",
    "brew-log/progress.md",
    "ledger",
    "roastery",
    "docs",
]

UNSAFE_ROOT_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    ".azure",
    ".gcp",
    ".config",
    "local_cup_outputs",
    "local_reports",
}

UNSAFE_ROOT_SUBSTRINGS = (
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "tokens",
)

ALLOWED_ACTIONS = {
    "dashboard": "Dashboard",
    "doctor": "Doctor",
    "release-check": "Release Check",
    "ledger-summary": "Ledger Summary",
    "evidence-bundle": "Evidence Bundle",
    "fleet-status": "Fleet Status",
}

ROUTE_DECAF = "Decaf / no model"
ROUTE_LOCAL_EVIDENCE = "Local evidence only"
ROUTE_REMOTE_APPROVAL = "Remote Bean requires approval"
ROUTE_ROASTERY_REQUIRED = "Roastery benchmark required"

ROUTING_MODES = [
    ROUTE_DECAF,
    ROUTE_LOCAL_EVIDENCE,
    ROUTE_REMOTE_APPROVAL,
    ROUTE_ROASTERY_REQUIRED,
]


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


@dataclass(frozen=True)
class RoutingDecision:
    request_class: str
    selected_mode: str
    approval_required: bool
    reason: str
    allowed_context: str
    blocked_context: str
    next_safe_action: str


@dataclass(frozen=True)
class CurrentStateItem:
    source_path: str
    status: str
    excerpt: str
    missing: bool = False

    @property
    def label(self) -> str:
        return f"{self.source_path} - {self.status}"


@dataclass(frozen=True)
class ProjectRootMarkerScore:
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.present)

    @property
    def total(self) -> int:
        return len(self.present) + len(self.missing)

    @property
    def summary(self) -> str:
        return f"{self.count}/{self.total} markers present"

    @property
    def looks_like_project_coffee(self) -> bool:
        return self.count >= 2 and (
            "tools/coffee.py" in self.present or "brew-log" in self.present
        )


@dataclass(frozen=True)
class ProjectRootStatus:
    path: Path
    exists: bool
    is_dir: bool
    marker_score: ProjectRootMarkerScore
    unsafe_reason: str | None = None

    @property
    def safe_for_commands(self) -> bool:
        return self.exists and self.is_dir and self.unsafe_reason is None

    @property
    def looks_like_project_coffee(self) -> bool:
        return self.marker_score.looks_like_project_coffee

    @property
    def message(self) -> str:
        if self.unsafe_reason:
            return f"Project root is blocked: {self.unsafe_reason}"
        if self.exists and self.is_dir:
            return f"Using project root: {self.path}"
        if self.exists:
            return f"Path exists but is not a directory: {self.path}"
        return f"Project root does not exist: {self.path}"


def default_project_root() -> Path:
    return REPO_ROOT


def normalize_project_root_input(text: str | Path | None) -> Path | None:
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    root_path = Path(raw).expanduser()
    if not root_path.is_absolute():
        root_path = (Path.cwd() / root_path).resolve()
    else:
        root_path = root_path.resolve()
    return root_path


def _empty_marker_score() -> ProjectRootMarkerScore:
    return ProjectRootMarkerScore(present=(), missing=tuple(PROJECT_ROOT_MARKERS))


def _unsafe_path_reason(path: Path) -> str | None:
    lowered_parts = [part.lower() for part in path.parts]
    for part in lowered_parts:
        if part in UNSAFE_ROOT_PARTS:
            return f"path contains blocked component `{part}`"
        if any(term in part for term in UNSAFE_ROOT_SUBSTRINGS):
            return f"path contains sensitive-looking component `{part}`"
    return None


def score_project_root_markers(path: str | Path | None) -> ProjectRootMarkerScore:
    root_path = normalize_project_root_input(path)
    if root_path is None:
        return _empty_marker_score()
    if _unsafe_path_reason(root_path):
        return _empty_marker_score()
    if not root_path.exists() or not root_path.is_dir():
        return _empty_marker_score()

    present: list[str] = []
    missing: list[str] = []
    for marker in PROJECT_ROOT_MARKERS:
        candidate = root_path / marker
        if candidate.exists():
            present.append(marker)
        else:
            missing.append(marker)
    return ProjectRootMarkerScore(present=tuple(present), missing=tuple(missing))


def validate_project_root(path: str | Path | None) -> ProjectRootStatus:
    root_path = normalize_project_root_input(path) or default_project_root()
    unsafe_reason = _unsafe_path_reason(root_path)
    if unsafe_reason:
        return ProjectRootStatus(
            path=root_path,
            exists=False,
            is_dir=False,
            marker_score=_empty_marker_score(),
            unsafe_reason=unsafe_reason,
        )

    exists = root_path.exists()
    is_dir = root_path.is_dir() if exists else False
    marker_score = score_project_root_markers(root_path) if exists and is_dir else _empty_marker_score()
    return ProjectRootStatus(
        path=root_path,
        exists=exists,
        is_dir=is_dir,
        marker_score=marker_score,
    )


def choose_active_root(input_root: str | Path | None, fallback_root: str | Path | None) -> Path:
    return (
        normalize_project_root_input(input_root)
        or normalize_project_root_input(fallback_root)
        or default_project_root()
    )


def add_recent_root(
    recent_roots: Sequence[str | Path],
    root: str | Path | None,
    max_items: int,
) -> list[str]:
    if max_items < 1:
        return []

    normalized_root = normalize_project_root_input(root)
    ordered: list[str] = []
    if normalized_root is not None:
        ordered.append(str(normalized_root))

    for existing in recent_roots:
        normalized_existing = normalize_project_root_input(existing)
        if normalized_existing is None:
            continue
        existing_text = str(normalized_existing)
        if existing_text not in ordered:
            ordered.append(existing_text)

    return ordered[:max_items]


def validate_root(root: str | Path) -> Path:
    status = validate_project_root(root)
    if status.unsafe_reason:
        raise CommandAdapterError(f"Project root is unsafe: {status.unsafe_reason}")
    if not status.exists:
        raise CommandAdapterError(f"Project root does not exist: {status.path}")
    if not status.is_dir:
        raise CommandAdapterError(f"Project root is not a directory: {status.path}")
    return status.path


def validate_registry_argument(registry: str | None) -> str | None:
    if registry is None:
        return None
    raw = registry.strip()
    if not raw:
        return None
    if any(character in raw for character in "\r\n\0"):
        raise CommandAdapterError("Registry path contains unsupported control characters.")
    registry_path = Path(raw).expanduser()
    reason = _unsafe_path_reason(registry_path)
    if reason:
        raise CommandAdapterError(f"Registry path is unsafe: {reason}")
    return raw


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

    if action == "fleet-status":
        registry_arg = validate_registry_argument(registry)
        if registry_arg is not None:
            args.extend(["--registry", registry_arg])

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


def describe_project_root(root: str | Path) -> ProjectRootStatus:
    return validate_project_root(root)


def is_current_state_question(text: str) -> bool:
    lowered = " ".join(text.lower().strip().split())
    if not lowered:
        return False
    return any(term in lowered for term in CURRENT_STATE_TERMS)


def current_state_priority_files() -> list[str]:
    return list(CURRENT_STATE_FILES)


def _clean_excerpt_line(line: str) -> str:
    return line.strip().strip("|").strip()


def _first_nonempty_line(lines: Sequence[str]) -> str:
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def _section_excerpt(lines: Sequence[str], heading: str, *, max_lines: int = 2) -> str:
    try:
        start = next(index for index, line in enumerate(lines) if line.strip().lower() == heading.lower())
    except StopIteration:
        return ""

    excerpt: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## ") and excerpt:
            break
        if stripped and not stripped.startswith("#"):
            excerpt.append(stripped)
        if len(excerpt) >= max_lines:
            break
    return " ".join(excerpt)


def summarize_current_state_file(relative_path: str, text: str) -> str:
    lines = text.splitlines()
    if relative_path == "brew-log/progress.md":
        for line in lines:
            if line.strip().lower().startswith("current status:"):
                return line.strip()
    if relative_path == "brew-log/active_context.md":
        milestone = _section_excerpt(lines, "## Current milestone", max_lines=1)
        next_action = _section_excerpt(lines, "## Next actions", max_lines=1)
        blockers = _section_excerpt(lines, "## Blockers", max_lines=1)
        return " ".join(part for part in [milestone, next_action, blockers] if part)
    if relative_path == "ROADMAP.md":
        status_lines = [
            _clean_excerpt_line(line)
            for line in lines
            if any(term in line for term in ["| Current shot |", "| Next step |", "| Blockers |"])
        ]
        return " ".join(status_lines[:3])
    if relative_path == "CHANGELOG.md":
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("### "):
                return stripped
    return _first_nonempty_line(lines)


def build_current_state_quick_view(root: str | Path) -> list[CurrentStateItem]:
    root_path = validate_root(root)
    items: list[CurrentStateItem] = []
    for relative_path in CURRENT_STATE_FILES:
        path = root_path / relative_path
        if not path.exists():
            items.append(
                CurrentStateItem(
                    source_path=relative_path,
                    status="missing",
                    excerpt="Status file is missing; fall back to normal Evidence Bundle output.",
                    missing=True,
                )
            )
            continue
        if not path.is_file():
            items.append(
                CurrentStateItem(
                    source_path=relative_path,
                    status="unreadable",
                    excerpt="Expected a file but found a non-file path.",
                    missing=True,
                )
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        excerpt = summarize_current_state_file(relative_path, text)
        items.append(
            CurrentStateItem(
                source_path=relative_path,
                status="found",
                excerpt=excerpt or "File found, but no concise status excerpt was detected.",
            )
        )
    return items


def prioritize_evidence_items_for_question(
    question: str,
    items: Sequence[EvidenceItem],
) -> list[EvidenceItem]:
    if not is_current_state_question(question):
        return list(items)
    priority = {path: index for index, path in enumerate(CURRENT_STATE_FILES)}

    def sort_key(item: EvidenceItem) -> tuple[int, int]:
        priority_rank = priority.get(item.source_path, len(priority))
        return (priority_rank, -item.score)

    return sorted(items, key=sort_key)


def route_badge_text(decision: RoutingDecision) -> list[str]:
    badges: list[str] = []
    if decision.request_class == "commit_or_push":
        badges.append("Manual-only Git")
    if decision.selected_mode == ROUTE_DECAF:
        badges.append("Decaf / no model")
    if decision.selected_mode == ROUTE_LOCAL_EVIDENCE:
        badges.append("Local evidence only")
    if decision.selected_mode == ROUTE_ROASTERY_REQUIRED:
        badges.append("Roastery required")
    if decision.approval_required:
        badges.append("Approval required")
    return badges


def no_evidence_suggestions(query: str = "") -> list[str]:
    suggestions = [
        "Try fewer words.",
        "Search a specific file or source.",
        "Check Brew Log status files.",
        "Run Doctor for repository health.",
        "Ask for current state.",
        "Verify the file exists.",
    ]
    if is_current_state_question(query):
        suggestions.insert(0, "Use Current State Quick View.")
    return suggestions


def command_status_summary(result: CommandResult) -> str:
    if result.timed_out:
        return "Timed out"
    if result.return_code == 0:
        return "Completed successfully"
    return "Returned a nonzero exit code"


@dataclass(frozen=True)
class FleetProjectSummary:
    project_id: str
    name: str
    project_type: str
    status: str
    path: str
    check_status: str


@dataclass(frozen=True)
class FleetStatusSummary:
    status: str
    registry_status: str
    project_count: int
    projects: tuple[FleetProjectSummary, ...]


def _line_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def parse_fleet_status_output(text: str) -> FleetStatusSummary:
    status = _line_value(text, "Status:") or "unknown"
    registry_status = _line_value(text, "Registry status:") or "unknown"
    project_count = _as_int(_line_value(text, "Project count:"), default=0)
    projects: list[FleetProjectSummary] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 6 or cells[0] == "ID":
            continue
        projects.append(
            FleetProjectSummary(
                project_id=cells[0],
                name=cells[1],
                project_type=cells[2],
                status=cells[3],
                path=cells[4],
                check_status=cells[5],
            )
        )
    return FleetStatusSummary(
        status=status,
        registry_status=registry_status,
        project_count=project_count,
        projects=tuple(projects),
    )


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
                "Source / line": item.reference or "(unknown source)",
                "Heading": item.heading or "(no heading)",
                "Match / rank": item.score,
                "Freshness": item.freshness_signal or "unknown",
                "Safety": item.safety_classification or "unknown",
                "Snippet": item.snippet or "(no snippet)",
            }
        )
    return rows


def classify_request_for_routing(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["commit", "push", "tag", "stage this", "git "]):
        return "commit_or_push"
    if "send" in lowered and any(term in lowered for term in ["repo context", "repository context", "to a model", "to model"]):
        return "send_repo_context"
    if any(term in lowered for term in ["benchmark", "cup test", "roastery", "compare beans", "model eval"]):
        return "model_benchmark"
    if any(term in lowered for term in ["fix", "bug", "change code", "edit file", "implement", "refactor"]):
        return "code_change"
    if any(term in lowered for term in ["cost", "token", "ledger", "spend"]):
        return "cost_token"
    if any(term in lowered for term in ["how to", "setup", "guide", "docs", "documentation", "onboard"]):
        return "docs_how_to"
    if is_current_state_question(text):
        return "current_status"
    return "local_evidence_question"


def approval_required_for_route(route: str) -> bool:
    return route in {ROUTE_REMOTE_APPROVAL, ROUTE_ROASTERY_REQUIRED}


def build_routing_decision(
    request_text: str,
    evidence_items: Sequence[EvidenceItem],
) -> RoutingDecision:
    request_class = classify_request_for_routing(request_text)
    evidence_note = (
        "Local Evidence Bundle snippets are available for preview."
        if evidence_items
        else "No evidence snippets are currently selected."
    )
    blocked_context = (
        "Secrets, .env files, credentials, tokens, hidden credential directories, "
        "raw Roastery local outputs, broad repository dumps, and unreviewed private data."
    )

    if request_class == "current_status":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_LOCAL_EVIDENCE,
            approval_required=False,
            reason="Current Brew and next Shot questions are answered from local Brew Log and roadmap evidence.",
            allowed_context=f"Brew Log, Roadmap, Dashboard output, and local evidence snippets. {evidence_note}",
            blocked_context=blocked_context,
            next_safe_action="Run or review the local Evidence Bundle and Dashboard output.",
        )
    if request_class == "docs_how_to":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_LOCAL_EVIDENCE,
            approval_required=False,
            reason="Docs and how-to questions should be grounded in local guides before any model is considered.",
            allowed_context=f"Docs, guides, Brew Log notes, and local evidence snippets. {evidence_note}",
            blocked_context=blocked_context,
            next_safe_action="Use the local evidence draft and verify cited guide paths.",
        )
    if request_class == "cost_token":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_LOCAL_EVIDENCE,
            approval_required=False,
            reason="Cost and token questions should use local Ledger evidence and local summaries.",
            allowed_context=f"Coffee Ledger, Ledger Summary, and local evidence snippets. {evidence_note}",
            blocked_context=blocked_context,
            next_safe_action="Run Ledger Summary and cite Ledger entries.",
        )
    if request_class == "model_benchmark":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_ROASTERY_REQUIRED,
            approval_required=True,
            reason="Model benchmarking can involve remote Beans, cost, and recorded evaluation evidence.",
            allowed_context="Roastery Cup Test prompts, summarized evidence, and approved benchmark metadata.",
            blocked_context=blocked_context,
            next_safe_action="Use Roastery workflow with explicit approval before any model call.",
        )
    if request_class == "code_change":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_REMOTE_APPROVAL,
            approval_required=True,
            reason="Code changes may require sending local context to a remote Bean later, but Brew 29 keeps remote execution disabled.",
            allowed_context=f"Local evidence snippets and human-approved file excerpts only. {evidence_note}",
            blocked_context=blocked_context,
            next_safe_action="Stay local-first: plan, review evidence, and ask before any remote context is sent.",
        )
    if request_class == "send_repo_context":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_REMOTE_APPROVAL,
            approval_required=True,
            reason="Sending repository context to a model is a remote-context action and requires explicit approval.",
            allowed_context="Previewed, allowlisted local snippets only after future approval gates are satisfied.",
            blocked_context=blocked_context,
            next_safe_action="Show the context preview only; do not send anything in this MVP.",
        )
    if request_class == "commit_or_push":
        return RoutingDecision(
            request_class=request_class,
            selected_mode=ROUTE_DECAF,
            approval_required=True,
            reason="Git writes stay human-controlled. The UI may show manual checklists but must not stage, commit, push, or tag.",
            allowed_context="Local status, diff summaries, and manual command reminders.",
            blocked_context=blocked_context,
            next_safe_action="Human reviews the diff, stages intended files, runs the staged secret-pattern check, and commits manually.",
        )
    return RoutingDecision(
        request_class=request_class,
        selected_mode=ROUTE_LOCAL_EVIDENCE,
        approval_required=False,
        reason="Default route is local evidence only until a request clearly requires approval.",
        allowed_context=f"Local Evidence Bundle snippets and public Project Coffee docs. {evidence_note}",
        blocked_context=blocked_context,
        next_safe_action="Run the local Evidence Bundle and verify cited sources.",
    )


def format_context_preview(
    evidence_items: Sequence[EvidenceItem],
    max_items: int = 3,
) -> str:
    if not evidence_items:
        return (
            "Context preview only - not sent anywhere.\n\n"
            "No eligible evidence snippets are selected yet.\n\n"
            "Excluded: secrets, .env files, credentials, raw local outputs, hidden "
            "credential directories, and broad repository dumps."
        )

    lines = [
        "Context preview only - not sent anywhere.",
        "",
        f"Eligible local evidence snippets shown: {min(max_items, len(evidence_items))}",
        "",
    ]
    for index, item in enumerate(evidence_items[:max_items], start=1):
        snippet = item.snippet or "(no snippet available)"
        heading = item.heading or "(no heading)"
        lines.append(f"{index}. {item.reference} - {heading}")
        lines.append(f"   {snippet}")
    lines.extend(
        [
            "",
            "Excluded: secrets, .env files, credentials, raw local outputs, hidden "
            "credential directories, and broad repository dumps.",
        ]
    )
    return "\n".join(lines)


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
        if "recent_roots" not in st.session_state:
            st.session_state["recent_roots"] = []
        fallback_root = st.session_state.get("active_root", str(default_project_root()))
        root_input = st.text_input(
            "Project root",
            value=str(fallback_root),
            help="Local Project Coffee root to inspect. Recent roots are session-only and are not written to disk.",
        )
        active_root_path = choose_active_root(root_input, fallback_root)
        root_status = describe_project_root(active_root_path)
        render_project_root_status(st, root_status)
        if root_status.safe_for_commands:
            st.session_state["active_root"] = str(root_status.path)
            st.session_state["recent_roots"] = add_recent_root(
                st.session_state.get("recent_roots", []),
                root_status.path,
                max_items=5,
            )
        recent_roots = st.session_state.get("recent_roots", [])
        if recent_roots:
            with st.expander("Session recent roots", expanded=False):
                st.caption("Session-only. Resets when the app restarts; nothing is written to disk.")
                for recent_root in recent_roots:
                    st.code(recent_root, language="text")
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
            "Routing / Approval",
            "Ledger",
            "Fleet",
            "Safety / Commands",
        ]
    )

    with tabs[0]:
        render_home_tab(st, str(root_status.path))

    with tabs[1]:
        render_ask_tab(st, str(root_status.path), int(max_results))

    with tabs[2]:
        render_evidence_tab(st, str(root_status.path), int(max_results))

    with tabs[3]:
        render_routing_tab(st, str(root_status.path), int(max_results))

    with tabs[4]:
        render_ledger_tab(st, str(root_status.path))

    with tabs[5]:
        render_fleet_tab(st, str(root_status.path))

    with tabs[6]:
        render_safety_tab(st, selected_action)


def render_project_root_status(st: object, status: ProjectRootStatus) -> None:
    st.caption("Active root")
    st.code(str(status.path), language="text")
    if status.safe_for_commands:
        st.success(status.message)
    else:
        st.warning(status.message)

    if status.looks_like_project_coffee:
        st.success(f"Looks like a Project Coffee root: {status.marker_score.summary}.")
    elif status.safe_for_commands:
        st.warning(f"Root exists, but Project Coffee markers are incomplete: {status.marker_score.summary}.")
    else:
        st.caption(f"Project Coffee markers: {status.marker_score.summary}.")

    with st.expander("Project root marker details", expanded=status.safe_for_commands and not status.looks_like_project_coffee):
        for marker in status.marker_score.present:
            st.markdown(f"- Found: `{marker}`")
        for marker in status.marker_score.missing:
            st.markdown(f"- Missing: `{marker}`")


def render_project_health(st: object, root: str) -> None:
    status = validate_project_root(root)
    st.subheader("Project Health")
    columns = st.columns(4)
    columns[0].metric("Root exists", "yes" if status.exists else "no")
    columns[1].metric("Coffee markers", status.marker_score.summary)
    columns[2].metric("Safe local-only", "yes" if status.safe_for_commands else "no")
    last_status = "No command run this session."
    session_state = getattr(st, "session_state", {})
    if isinstance(session_state, dict):
        last_status = str(session_state.get("last_command_status", last_status))
    else:
        try:
            last_status = str(session_state.get("last_command_status", last_status))
        except AttributeError:
            pass
    columns[3].write("Last command status")
    columns[3].caption(last_status)
    if not status.safe_for_commands:
        st.warning("Commands are blocked until the active root exists, is a directory, and is not a blocked credential-like path.")
    elif not status.looks_like_project_coffee:
        st.warning("This root is usable for local commands, but Project Coffee markers are incomplete.")
    else:
        st.success("Active root is ready for local Project Coffee commands.")


def render_home_tab(st: object, root: str) -> None:
    st.subheader("Home / Overview")
    st.write("Run local Project Coffee status tools. Outputs stay on this machine.")
    render_project_health(st, root)
    columns = st.columns(4)
    actions = ["dashboard", "doctor", "release-check", "fleet-status"]
    for column, action in zip(columns, actions):
        with column:
            if st.button(ALLOWED_ACTIONS[action], key=f"home-{action}"):
                result = safe_run_for_ui(st, action, root=root)
                display_result(st, result, ALLOWED_ACTIONS[action])


def render_active_root_notice(st: object, root: str, *, purpose: str) -> ProjectRootStatus:
    status = validate_project_root(root)
    st.caption(f"Active root for {purpose}: {status.path}")
    if not status.safe_for_commands:
        st.warning("Active root is invalid or blocked; local commands will not run until it is fixed.")
    return status


def render_ask_tab(st: object, root: str, default_max_results: int) -> None:
    st.subheader("Ask Coffee - local only")
    render_evidence_safety_notice(st)
    render_active_root_notice(st, root, purpose="Ask Coffee")
    question = st.text_area("Question or Coffee Order", height=140)
    max_results = st.number_input(
        "Max evidence results",
        min_value=1,
        max_value=50,
        value=default_max_results,
        key="ask-max-results",
    )
    if question.strip():
        st.write("Routing decision")
        render_routing_decision(st, build_routing_decision(question, []))
        if is_current_state_question(question):
            render_current_state_quick_view(st, root)
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
                if not bundle.parse_error:
                    bundle = EvidenceBundle(
                        query=bundle.query,
                        total_matches=bundle.total_matches,
                        items=prioritize_evidence_items_for_question(question, bundle.items),
                        warnings=bundle.warnings,
                    )
                st.write("Routing decision with evidence preview")
                render_routing_decision(st, build_routing_decision(question, bundle.items))
                render_context_preview(st, bundle.items, max_items=3)
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
    render_active_root_notice(st, root, purpose="Evidence Bundle")
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


def render_routing_tab(st: object, root: str, default_max_results: int) -> None:
    st.subheader("Routing / Approval")
    render_active_root_notice(st, root, purpose="Routing preview")
    st.info(
        "Remote model calls are disabled in this MVP. Future remote Bean calls "
        "will require explicit approval."
    )
    selected_mode = st.selectbox(
        "Routing mode choices",
        options=ROUTING_MODES,
        index=ROUTING_MODES.index(ROUTE_LOCAL_EVIDENCE),
    )
    st.caption(f"Default routing mode: {ROUTE_LOCAL_EVIDENCE}. Selected mode is preview-only.")
    request_text = st.text_area(
        "Request to route",
        value="What is the current Brew and next Shot?",
        height=120,
        key="routing-request",
    )
    max_results = st.number_input(
        "Preview evidence items",
        min_value=1,
        max_value=10,
        value=min(default_max_results, 5),
        key="routing-max-results",
    )
    decision = build_routing_decision(request_text, [])
    render_routing_decision(st, decision)

    if st.button("Preview eligible local context"):
        result = safe_run_for_ui(
            st,
            "evidence-bundle",
            root=root,
            query=request_text,
            max_results=int(max_results),
            json_output=True,
        )
        display_result(st, result, "Context Preview Evidence", expand_stdout=False)
        if result is not None:
            bundle = parse_evidence_bundle_json(result.stdout)
            if not bundle.parse_error:
                bundle = EvidenceBundle(
                    query=bundle.query,
                    total_matches=bundle.total_matches,
                    items=prioritize_evidence_items_for_question(request_text, bundle.items),
                    warnings=bundle.warnings,
                )
            render_routing_decision(st, build_routing_decision(request_text, bundle.items))
            render_context_preview(st, bundle.items, max_items=int(max_results))
            render_evidence_bundle_summary(st, bundle, result.return_code)

    st.write("Approval gate copy")
    st.markdown(
        """
- Remote model calls are disabled in this MVP.
- Future remote Bean calls will require explicit approval.
- Secrets, `.env` files, credentials, tokens, and raw local outputs are excluded.
- This tab previews routing decisions only; it does not send context anywhere.
"""
    )
    st.caption(f"Preview-selected mode was `{selected_mode}`; no remote execution exists.")


def render_ledger_tab(st: object, root: str) -> None:
    st.subheader("Ledger")
    render_active_root_notice(st, root, purpose="Ledger")
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
    render_active_root_notice(st, root, purpose="Fleet")
    registry = st.text_input("Optional registry path", value="")
    st.caption("Registry path is passed as a path argument only. It is not executed and is not persisted.")
    if st.button("Run fleet-status"):
        result = safe_run_for_ui(
            st,
            "fleet-status",
            root=root,
            registry=registry.strip() or None,
        )
        display_result(st, result, "Fleet Status")
        if result is not None:
            render_fleet_status_summary(st, parse_fleet_status_output(result.stdout), result.return_code)


def render_fleet_status_summary(
    st: object,
    summary: FleetStatusSummary,
    return_code: int,
) -> None:
    st.subheader("Fleet summary")
    columns = st.columns(3)
    columns[0].metric("Fleet status", summary.status)
    columns[1].metric("Registry", summary.registry_status)
    columns[2].metric("Projects", str(summary.project_count))

    if return_code != 0:
        st.warning("Fleet command returned a nonzero exit code; review stdout and stderr above.")
    if summary.registry_status in {"missing", "unsafe", "invalid-json"}:
        st.warning("Fleet registry is missing, unsafe, or invalid. Use the example registry only after local review.")
    elif summary.project_count == 0:
        st.info("No projects are registered yet.")

    if summary.projects:
        st.write("Registered projects")
        st.dataframe(
            [
                {
                    "ID": project.project_id,
                    "Name": project.name,
                    "Type": project.project_type,
                    "Status": project.status,
                    "Path": project.path,
                    "Check": project.check_status,
                }
                for project in summary.projects
            ],
            width="stretch",
        )
        st.caption("Project cards are based on Fleet Status output only; no extra commands are run for other roots.")


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
- approval gates are visible, but remote execution is disabled
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
- Brew 29 only shows approval scaffolding; it cannot send context remotely.
- Git operations require human review and approval.
- Dependency installs require approval.
- Secrets and raw local outputs are excluded.
"""
    )


def render_evidence_safety_notice(st: object) -> None:
    st.info(
        "Local evidence only. Evidence is retrieved from allowlisted local Project Coffee "
        "sources; excluded paths are not searched. Remote Bean calls remain disabled."
    )


def render_current_state_quick_view(st: object, root: str) -> None:
    st.subheader("Current State Quick View")
    st.caption(
        "Local current-state quick view from allowlisted status files only. "
        "Normal Evidence Bundle output remains available below."
    )
    try:
        items = build_current_state_quick_view(root)
    except CommandAdapterError as exc:
        st.warning(f"Current State Quick View unavailable: {exc}")
        return

    missing = [item for item in items if item.missing]
    if missing:
        st.warning("One or more current-state files are missing; falling back to normal Evidence Bundle output is recommended.")

    for item in items:
        title = f"{item.source_path} ({item.status})"
        with st.expander(title, expanded=not item.missing):
            st.write(item.excerpt or "(no status excerpt found)")


def render_routing_decision(st: object, decision: RoutingDecision) -> None:
    badges = route_badge_text(decision)
    st.markdown(" ".join(f"`{badge}`" for badge in badges))
    st.markdown(
        f"""
- Request class: `{decision.request_class}`
- Selected mode: `{decision.selected_mode}`
- Approval required: `{"yes" if decision.approval_required else "no"}`
- Reason: {decision.reason}
- Allowed context: {decision.allowed_context}
- Blocked context: {decision.blocked_context}
- Next safe action: {decision.next_safe_action}
"""
    )
    if decision.approval_required:
        st.warning("Approval required before this route can use remote context.")
    else:
        st.success("No remote approval needed for this local-only route.")


def render_context_preview(
    st: object,
    evidence_items: Sequence[EvidenceItem],
    max_items: int,
) -> None:
    st.subheader("Context preview")
    st.caption("Preview only. Nothing is sent anywhere.")
    st.code(format_context_preview(evidence_items, max_items=max_items), language="markdown")


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
        st.write("Try next:")
        for suggestion in no_evidence_suggestions(bundle.query):
            st.markdown(f"- {suggestion}")
    elif state == "json-parse-error":
        st.error(
            "Evidence JSON could not be parsed. The raw command output is still visible above; "
            f"retry JSON mode or inspect stdout. Parser note: {bundle.parse_error}"
        )
    else:
        st.error("Evidence command returned a nonzero exit code.")

    for warning in bundle.warnings:
        st.warning(warning)

    if bundle.items:
        st.write("Top evidence items")
        st.dataframe(evidence_table_rows(bundle), width="stretch")
        for index, item in enumerate(bundle.items[:5], start=1):
            source = item.reference or "(unknown source)"
            heading = item.heading or "(no heading)"
            with st.expander(f"{index}. {source} - {heading}"):
                st.markdown(
                    f"""
- Source/path: `{source}`
- Heading: `{heading}`
- Match/rank: `{item.score}`
- Freshness: `{item.freshness_signal or "unknown"}`
- Safety: `{item.safety_classification or "unknown"}`
- Reason: {item.reason_selected or "(none recorded)"}
"""
                )
                st.code(item.snippet or "(no snippet)", language="markdown")


def safe_run_for_ui(st: object, action: str, **kwargs: object) -> CommandResult | None:
    try:
        result = run_coffee_command(action, **kwargs)
    except CommandAdapterError as exc:
        st.error(str(exc))
        return None
    label = ALLOWED_ACTIONS.get(action, action)
    status_text = f"{label}: {command_status_summary(result)} (exit {result.return_code})"
    try:
        st.session_state["last_command_status"] = status_text
    except (AttributeError, TypeError):
        pass
    return result


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
    st.caption(command_status_summary(result))
    if result.timed_out:
        st.warning("Command timed out.")
    if result.return_code == 0 and not result.timed_out:
        st.success("Command completed.")
    else:
        st.error("Command did not complete cleanly.")
    with st.expander("command run", expanded=False):
        st.code(format_display_command(result.args), language="text")
    with st.expander("return code", expanded=False):
        st.write(f"`{result.return_code}`")
    with st.expander("status summary", expanded=True):
        st.write(command_status_summary(result))
    with st.expander("stdout", expanded=expand_stdout):
        st.code(result.stdout or "(empty)", language="text")
    with st.expander("stderr", expanded=bool(result.stderr)):
        st.code(result.stderr or "(empty)", language="text")


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()

"""Workflow certification helpers for Project Coffee."""

from dataclasses import dataclass
from typing import Iterable, Tuple


REQUIRED_WORKFLOW_STEPS: Tuple[str, ...] = (
    "Decaf Mode",
    "Planning",
    "Implementation",
    "Tests",
    "Brew Log update",
    "Roastery entry",
    "Coffee Ledger entry",
    "House Blend usage",
    "Diff review",
    "Human approval",
    "Manual commit",
)


@dataclass(frozen=True)
class CertificationResult:
    """Result of checking completed steps against a required workflow."""

    required_steps: Tuple[str, ...]
    completed_steps: Tuple[str, ...]
    missing_steps: Tuple[str, ...]
    unexpected_steps: Tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.missing_steps and not self.unexpected_steps

    @property
    def completed_count(self) -> int:
        return len(self.completed_steps)

    @property
    def required_count(self) -> int:
        return len(self.required_steps)


def certify_workflow(
    completed_steps: Iterable[str],
    required_steps: Tuple[str, ...] = REQUIRED_WORKFLOW_STEPS,
) -> CertificationResult:
    """Check completed workflow steps against the required certification steps."""

    canonical_by_key = {_step_key(step): step for step in required_steps}
    seen_keys = set()
    completed = []
    unexpected = []
    unexpected_keys = set()

    for raw_step in completed_steps:
        step = raw_step.strip()
        key = _step_key(step)

        if not key:
            continue

        if key in canonical_by_key:
            if key not in seen_keys:
                completed.append(canonical_by_key[key])
                seen_keys.add(key)
            continue

        if key not in unexpected_keys:
            unexpected.append(step)
            unexpected_keys.add(key)

    missing = tuple(step for step in required_steps if _step_key(step) not in seen_keys)

    return CertificationResult(
        required_steps=required_steps,
        completed_steps=tuple(completed),
        missing_steps=missing,
        unexpected_steps=tuple(unexpected),
    )


def format_markdown_report(result: CertificationResult) -> str:
    """Format a certification result as a small Markdown report."""

    status = "COMPLETE" if result.is_complete else "INCOMPLETE"
    lines = [
        "# Coffee Certification Report",
        "",
        f"Status: {status}",
        f"Completed: {result.completed_count} / {result.required_count}",
        "",
        "## Completed",
        *_format_list(result.completed_steps),
        "",
        "## Missing",
        *_format_list(result.missing_steps),
        "",
        "## Unexpected",
        *_format_list(result.unexpected_steps),
    ]
    return "\n".join(lines)


def _format_list(items: Tuple[str, ...]) -> Tuple[str, ...]:
    if not items:
        return ("- None",)
    return tuple(f"- {item}" for item in items)


def _step_key(step: str) -> str:
    normalized = step.strip().lower().replace("-", " ").replace("_", " ")
    return " ".join(normalized.split())

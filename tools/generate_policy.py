"""Generate router/config/routing_policy.yaml from real Roastery evidence.

Reads roastery/tasting_notes.md's per-task score tables (the only committed,
structured Roastery evidence with per-Bean quality scores - see
docs/design/coffee-core-router-design.md Section 3, Gap 2) and computes a
primary/fallback Bean per task_type.

Do not hand-edit router/config/routing_policy.yaml. Re-run this script after
new Roastery evidence lands, then review the diff like any other generated
artifact before committing.

Usage:
    python tools\\generate_policy.py
    python tools\\generate_policy.py --tasting-notes roastery\\tasting_notes.md --beans router\\config\\beans.yaml --output router\\config\\routing_policy.yaml
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASTING_NOTES = REPO_ROOT / "roastery" / "tasting_notes.md"
DEFAULT_BEANS_PATH = REPO_ROOT / "router" / "config" / "beans.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "router" / "config" / "routing_policy.yaml"

# Which Cup Test file corresponds to which router task_type. This is a
# judgment call documented in docs/design/coffee-core-router-design.md
# Section 3 (Gap 2), based on each Cup Test's stated Purpose:
#   001-decaf-repo-map.md      -> codebase understanding / planning -> analysis
#   002-tiny-python-fix.md     -> small Python debugging + test     -> code
#   003-docs-summary.md        -> documentation summary             -> doc
#   004-pantry-assisted-answer.md -> grounded citation answering    -> explain
# research and refactor have no Roastery evidence at all and are always
# emitted as "default" policy entries.
TASK_TYPE_BY_CUP_TEST_FILE: Dict[str, str] = {
    "roastery/cup_tests/001-decaf-repo-map.md": "analysis",
    "roastery/cup_tests/002-tiny-python-fix.md": "code",
    "roastery/cup_tests/003-docs-summary.md": "doc",
    "roastery/cup_tests/004-pantry-assisted-answer.md": "explain",
}

ALL_TASK_TYPES = ["code", "research", "explain", "refactor", "doc", "analysis"]

TASK_FILE_RE = re.compile(r"^Task file:\s*$")
FENCED_PATH_RE = re.compile(r"^roastery/cup_tests/\S+\.md\s*$")
SCORE_TABLE_HEADER_RE = re.compile(
    r"^\|\s*Bean\s*\|\s*Status\s*\|\s*Latency\s*\|\s*Tokens\s*\|\s*Cost\s*\|\s*Captured\s*\|\s*Reviewed\s*\|\s*Score\s*\|\s*Use again\?\s*\|"
)
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
TOKENS_RE = re.compile(r"(\d+)\s+total")
SOURCE_HEADING_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2}) - (.+)$")


@dataclass
class ScoredRun:
    task_type: str
    bean_model_id: str
    score: Optional[int]
    tokens_total: Optional[int]
    source_heading: str
    cup_test_file: str


@dataclass
class TaskTypeEvidence:
    runs: List[ScoredRun] = field(default_factory=list)

    def per_bean_averages(self) -> Dict[str, Dict[str, float]]:
        by_bean: Dict[str, List[ScoredRun]] = {}
        for run in self.runs:
            if run.score is None:
                continue
            by_bean.setdefault(run.bean_model_id, []).append(run)

        result: Dict[str, Dict[str, float]] = {}
        for bean_model_id, runs in by_bean.items():
            scores = [r.score for r in runs if r.score is not None]
            tokens = [r.tokens_total for r in runs if r.tokens_total is not None]
            result[bean_model_id] = {
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "avg_tokens": sum(tokens) / len(tokens) if tokens else float("inf"),
                "run_count": len(runs),
            }
        return result


def parse_tasting_notes(text: str) -> Dict[str, TaskTypeEvidence]:
    lines = text.splitlines()
    evidence: Dict[str, TaskTypeEvidence] = {task_type: TaskTypeEvidence() for task_type in ALL_TASK_TYPES}

    current_heading = ""
    i = 0
    while i < len(lines):
        line = lines[i]

        heading_match = SOURCE_HEADING_RE.match(line)
        if heading_match:
            current_heading = heading_match.group(2)

        if TASK_FILE_RE.match(line.strip()):
            cup_test_file, table_start = _find_cup_test_file_and_table(lines, i)
            if cup_test_file is not None and table_start is not None:
                task_type = TASK_TYPE_BY_CUP_TEST_FILE.get(cup_test_file)
                if task_type is not None:
                    runs = _parse_score_table(lines, table_start, task_type, current_heading, cup_test_file)
                    evidence[task_type].runs.extend(runs)

        i += 1

    return evidence


def _find_cup_test_file_and_table(lines: List[str], task_file_line_index: int):
    cup_test_file = None
    for j in range(task_file_line_index + 1, min(task_file_line_index + 6, len(lines))):
        if FENCED_PATH_RE.match(lines[j].strip()):
            cup_test_file = lines[j].strip()
            break
    if cup_test_file is None:
        return None, None

    for j in range(task_file_line_index, min(task_file_line_index + 40, len(lines))):
        if SCORE_TABLE_HEADER_RE.match(lines[j]):
            return cup_test_file, j
    return cup_test_file, None


def _parse_score_table(
    lines: List[str],
    header_index: int,
    task_type: str,
    source_heading: str,
    cup_test_file: str,
) -> List[ScoredRun]:
    runs: List[ScoredRun] = []
    # header_index+1 is the "| --- | --- | ..." separator row.
    row_index = header_index + 2
    while row_index < len(lines):
        row = lines[row_index]
        if not TABLE_ROW_RE.match(row):
            break
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 8:
            break

        bean_cell, _status, _latency, tokens_cell, _cost, _captured, _reviewed, score_cell = cells[:8]

        bean_match = BACKTICK_RE.search(bean_cell)
        bean_model_id = bean_match.group(1) if bean_match else bean_cell

        tokens_match = TOKENS_RE.search(tokens_cell)
        tokens_total = int(tokens_match.group(1)) if tokens_match else None

        score_value: Optional[int]
        try:
            score_value = int(score_cell)
        except ValueError:
            score_value = None

        runs.append(
            ScoredRun(
                task_type=task_type,
                bean_model_id=bean_model_id,
                score=score_value,
                tokens_total=tokens_total,
                source_heading=source_heading,
                cup_test_file=cup_test_file,
            )
        )
        row_index += 1

    return runs


def _rank_beans(averages: Dict[str, Dict[str, float]]) -> List[str]:
    """Rank bean model IDs best-first: higher avg_score wins; ties broken by
    lower avg_tokens (efficiency), since every current Bean is :free tier
    (cost is 0 for all of them today, so quality-per-dollar collapses to
    quality-per-token as the only real differentiator - see
    docs/design/coffee-core-router-design.md Section 3)."""

    return sorted(
        averages.keys(),
        key=lambda bean_id: (-averages[bean_id]["avg_score"], averages[bean_id]["avg_tokens"]),
    )


def build_policy(evidence: Dict[str, TaskTypeEvidence], beans_config: dict) -> dict:
    alias_by_model_id = {
        bean["model_id"]: bean["alias"] for bean in beans_config["beans"] if bean.get("model_id")
    }
    default_bean_alias = next(
        (bean["alias"] for bean in beans_config["beans"] if bean.get("role") == "default"),
        None,
    )
    premium_bean = next((bean for bean in beans_config["beans"] if bean.get("role") == "premium"), None)
    premium_alias = premium_bean["alias"] if premium_bean and premium_bean.get("model_id") else None

    policy_entries = {}
    for task_type in ALL_TASK_TYPES:
        task_evidence = evidence[task_type]
        averages = task_evidence.per_bean_averages()

        if not averages:
            policy_entries[task_type] = {
                "status": "default",
                "primary_bean_alias": default_bean_alias,
                "fallback_bean_alias": None,
                "premium_bean_alias": premium_alias,
                "evidence": [],
                "reason": (
                    f"No Roastery evidence for task_type={task_type!r}. "
                    "Falling back to the configured House Blend default per "
                    "docs/design/model-routing-policy.md."
                ),
            }
            continue

        ranked_model_ids = _rank_beans(averages)
        primary_model_id = ranked_model_ids[0]
        fallback_model_id = ranked_model_ids[1] if len(ranked_model_ids) > 1 else None

        evidence_refs = sorted(
            {
                f"{run.cup_test_file} ({run.source_heading})"
                for run in task_evidence.runs
            }
        )

        policy_entries[task_type] = {
            "status": "evidence_based",
            "primary_bean_alias": alias_by_model_id.get(primary_model_id, primary_model_id),
            "fallback_bean_alias": (
                alias_by_model_id.get(fallback_model_id, fallback_model_id)
                if fallback_model_id
                else None
            ),
            "premium_bean_alias": premium_alias,
            "evidence": evidence_refs,
            "scores": {
                alias_by_model_id.get(model_id, model_id): {
                    "avg_score": round(stats["avg_score"], 2),
                    "avg_tokens": (
                        round(stats["avg_tokens"], 1) if stats["avg_tokens"] != float("inf") else None
                    ),
                    "run_count": stats["run_count"],
                }
                for model_id, stats in averages.items()
            },
            "reason": (
                f"Primary Bean ranked highest by avg score (tie-broken by lowest avg "
                f"tokens) across {len(task_evidence.runs)} scored Roastery run(s)."
            ),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "tools/generate_policy.py",
        "source": "roastery/tasting_notes.md",
        "note": "Generated policy. Do not hand-edit. Re-run tools/generate_policy.py.",
        "task_types": policy_entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasting-notes", type=Path, default=DEFAULT_TASTING_NOTES)
    parser.add_argument("--beans", type=Path, default=DEFAULT_BEANS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    tasting_notes_text = args.tasting_notes.read_text(encoding="utf-8")
    with open(args.beans, "r", encoding="utf-8") as handle:
        beans_config = yaml.safe_load(handle)

    evidence = parse_tasting_notes(tasting_notes_text)
    policy = build_policy(evidence, beans_config)

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write("# Coffee Core Router - generated routing policy\n")
        handle.write("# Generated by tools/generate_policy.py. Do not hand-edit.\n")
        handle.write("# Re-run the generator after new Roastery evidence lands, then review\n")
        handle.write("# the diff before committing, like any other generated artifact.\n\n")
        yaml.safe_dump(policy, handle, sort_keys=False, default_flow_style=False, allow_unicode=True)

    evidence_based = sum(1 for e in policy["task_types"].values() if e["status"] == "evidence_based")
    default_only = sum(1 for e in policy["task_types"].values() if e["status"] == "default")
    print(f"Wrote {args.output}")
    print(f"Task types with real Roastery evidence: {evidence_based}")
    print(f"Task types on default (no evidence): {default_only}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

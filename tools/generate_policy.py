"""Generate router/config/routing_policy.yaml from real Roastery evidence.

Reads roastery/tasting_notes.md's per-task score tables (the only committed,
structured Roastery evidence with per-Bean quality scores - see
docs/design/coffee-core-router-design.md Section 3, Gap 2) and computes a
primary/fallback Bean per task_type.

Brew 42 (docs/design/learning-loop-and-release-design.md Section 3.1) adds a
second, optional evidence source: real accumulated `POST /v1/rate` outcomes
from ledger/router_requests.csv. A (task_type, bean_alias) pair only
influences ranking once it has at least `min_rating_sample_size` real
ratings - below that, ranking is exactly the pre-Brew-42 Cup-Test-only
behavior. See load_rating_evidence()/RATING_NUMERIC_VALUE for the exact
rating-to-score mapping.

Do not hand-edit router/config/routing_policy.yaml. Re-run this script after
new Roastery evidence lands, then review the diff like any other generated
artifact before committing - or pass --dry-run to preview the diff without
writing anything.

Usage:
    python tools\\generate_policy.py
    python tools\\generate_policy.py --dry-run
    python tools\\generate_policy.py --tasting-notes roastery\\tasting_notes.md --beans router\\config\\beans.yaml --ledger ledger\\router_requests.csv --output router\\config\\routing_policy.yaml
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASTING_NOTES = REPO_ROOT / "roastery" / "tasting_notes.md"
DEFAULT_BEANS_PATH = REPO_ROOT / "router" / "config" / "beans.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "router" / "config" / "routing_policy.yaml"
DEFAULT_LEDGER_PATH = REPO_ROOT / "ledger" / "router_requests.csv"

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

# Brew 42: the numeric mapping applied to POST /v1/rate outcomes
# (router/app/main.py:VALID_RATINGS) before averaging - a judgment call
# stated plainly here, not buried: "good" is a full-credit response,
# "needed_fixing" is a half-credit partial success, "failed" is zero
# credit. Same 0-1 scale draft_quality already gestures at, made
# continuous instead of binary.
RATING_NUMERIC_VALUE: Dict[str, float] = {
    "good": 1.0,
    "needed_fixing": 0.5,
    "failed": 0.0,
}

DEFAULT_MIN_RATING_SAMPLE_SIZE = 5
DEFAULT_ROASTERY_WEIGHT = 0.6
DEFAULT_ESCALATION_RATE_FLAG_THRESHOLD = 0.3

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


@dataclass(frozen=True)
class RatingEvidence:
    rating_count: int
    avg_rating: float


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


def load_ledger_rows(ledger_path: Path) -> List[Dict[str, str]]:
    """Real ledger/router_requests.csv rows, or [] if the file doesn't
    exist yet - the ratings/escalation-rate signals below degrade
    gracefully to "no signal" in that case, matching every other
    graceful-degradation precedent in this repo (Pantry retrieval, Brew
    41)."""

    if not ledger_path.is_file():
        return []
    with open(ledger_path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_rating_evidence(
    ledger_rows: List[Dict[str, str]],
) -> Dict[Tuple[str, str], RatingEvidence]:
    """Groups real Ledger rows by (task_type, bean_alias), averaging each
    pair's non-empty `rating` cells via RATING_NUMERIC_VALUE. A pair with
    zero rated rows is simply absent from the result - callers treat
    "absent" and "below min_rating_sample_size" identically (no rating
    signal yet)."""

    grouped: Dict[Tuple[str, str], List[float]] = {}
    for row in ledger_rows:
        rating = (row.get("rating") or "").strip()
        numeric_value = RATING_NUMERIC_VALUE.get(rating)
        if numeric_value is None:
            continue
        key = (row.get("task_type", ""), row.get("bean_alias", ""))
        grouped.setdefault(key, []).append(numeric_value)

    return {
        key: RatingEvidence(rating_count=len(values), avg_rating=sum(values) / len(values))
        for key, values in grouped.items()
    }


def compute_escalation_rates(ledger_rows: List[Dict[str, str]]) -> Dict[str, float]:
    """Per-task_type escalation rate (escalated=True rows / total rows for
    that task_type) - a signal about whether the task_type itself keeps
    needing escalation, unrelated to any specific Bean. A task_type with
    zero real requests is simply absent from the result."""

    totals: Dict[str, int] = {}
    escalated: Dict[str, int] = {}
    for row in ledger_rows:
        task_type = row.get("task_type", "")
        if not task_type:
            continue
        totals[task_type] = totals.get(task_type, 0) + 1
        if (row.get("escalated") or "").strip().lower() == "true":
            escalated[task_type] = escalated.get(task_type, 0) + 1

    return {task_type: escalated.get(task_type, 0) / count for task_type, count in totals.items()}


def _rank_beans(
    averages: Dict[str, Dict[str, float]],
    *,
    task_type: str,
    alias_by_model_id: Dict[str, str],
    rating_evidence: Dict[Tuple[str, str], RatingEvidence],
    min_rating_sample_size: int,
    roastery_weight: float,
) -> List[str]:
    """Ranks bean model IDs best-first by combined_score, tie-broken by
    lower avg_tokens (efficiency) - since every current Bean is :free
    tier, cost is 0 for all of them today, so a real quality-per-dollar
    metric isn't possible yet and avg_tokens remains the best available
    efficiency proxy (docs/design/coffee-core-router-design.md Section 3).

    combined_score is the Cup Test avg_score (0-10) normalized to 0-1,
    blended with a real accumulated-rating average once that
    (task_type, bean_alias) pair has at least min_rating_sample_size real
    ratings: combined_score = cup_test_normalized * roastery_weight +
    avg_rating * (1 - roastery_weight). Below the sample threshold, a
    pair's combined_score is exactly its cup_test_normalized score - the
    pre-Brew-42 behavior, unchanged (docs/design/learning-loop-and-release-design.md
    Section 3.1)."""

    def combined_score(bean_id: str) -> float:
        cup_test_normalized = averages[bean_id]["avg_score"] / 10.0
        alias = alias_by_model_id.get(bean_id, bean_id)
        evidence = rating_evidence.get((task_type, alias))
        if evidence is None or evidence.rating_count < min_rating_sample_size:
            return cup_test_normalized
        return cup_test_normalized * roastery_weight + evidence.avg_rating * (1 - roastery_weight)

    return sorted(
        averages.keys(),
        key=lambda bean_id: (-combined_score(bean_id), averages[bean_id]["avg_tokens"]),
    )


def build_policy(
    evidence: Dict[str, TaskTypeEvidence],
    beans_config: dict,
    *,
    ledger_rows: Optional[List[Dict[str, str]]] = None,
    min_rating_sample_size: int = DEFAULT_MIN_RATING_SAMPLE_SIZE,
    roastery_weight: float = DEFAULT_ROASTERY_WEIGHT,
    escalation_rate_flag_threshold: float = DEFAULT_ESCALATION_RATE_FLAG_THRESHOLD,
) -> dict:
    ledger_rows = ledger_rows or []
    rating_evidence = load_rating_evidence(ledger_rows)
    escalation_rates = compute_escalation_rates(ledger_rows)

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
    escalation_candidates: List[str] = []

    for task_type in ALL_TASK_TYPES:
        escalation_rate = round(escalation_rates.get(task_type, 0.0), 3)
        if escalation_rate > escalation_rate_flag_threshold:
            escalation_candidates.append(task_type)

        task_evidence = evidence[task_type]
        averages = task_evidence.per_bean_averages()

        if not averages:
            policy_entries[task_type] = {
                "status": "default",
                "primary_bean_alias": default_bean_alias,
                "fallback_bean_alias": None,
                "premium_bean_alias": premium_alias,
                "evidence": [],
                "escalation_rate": escalation_rate,
                "reason": (
                    f"No Roastery evidence for task_type={task_type!r}. "
                    "Falling back to the configured House Blend default per "
                    "docs/design/model-routing-policy.md."
                ),
            }
            continue

        unweighted_ranked_model_ids = sorted(
            averages.keys(),
            key=lambda bean_id: (-averages[bean_id]["avg_score"], averages[bean_id]["avg_tokens"]),
        )
        ranked_model_ids = _rank_beans(
            averages,
            task_type=task_type,
            alias_by_model_id=alias_by_model_id,
            rating_evidence=rating_evidence,
            min_rating_sample_size=min_rating_sample_size,
            roastery_weight=roastery_weight,
        )
        primary_model_id = ranked_model_ids[0]
        fallback_model_id = ranked_model_ids[1] if len(ranked_model_ids) > 1 else None
        primary_alias = alias_by_model_id.get(primary_model_id, primary_model_id)

        evidence_refs = sorted(
            {
                f"{run.cup_test_file} ({run.source_heading})"
                for run in task_evidence.runs
            }
        )

        reason = (
            f"Primary Bean ranked highest by avg score (tie-broken by lowest avg "
            f"tokens) across {len(task_evidence.runs)} scored Roastery run(s)."
        )
        primary_rating_evidence = rating_evidence.get((task_type, primary_alias))
        if primary_rating_evidence is not None and primary_rating_evidence.rating_count >= min_rating_sample_size:
            if unweighted_ranked_model_ids[0] != primary_model_id:
                old_alias = alias_by_model_id.get(unweighted_ranked_model_ids[0], unweighted_ranked_model_ids[0])
                reason += (
                    f" {primary_rating_evidence.rating_count} real rating(s) "
                    f"(avg {primary_rating_evidence.avg_rating:.2f}) shifted the "
                    f"primary Bean from {old_alias} to {primary_alias}."
                )
            else:
                reason += (
                    f" {primary_rating_evidence.rating_count} real rating(s) "
                    f"(avg {primary_rating_evidence.avg_rating:.2f}) confirmed this ranking."
                )

        ratings_section = {
            alias_by_model_id.get(model_id, model_id): {
                "rating_count": ev.rating_count,
                "avg_rating": round(ev.avg_rating, 2),
                "met_sample_threshold": ev.rating_count >= min_rating_sample_size,
            }
            for model_id in averages
            for ev in [rating_evidence.get((task_type, alias_by_model_id.get(model_id, model_id)))]
            if ev is not None
        }

        policy_entries[task_type] = {
            "status": "evidence_based",
            "primary_bean_alias": primary_alias,
            "fallback_bean_alias": (
                alias_by_model_id.get(fallback_model_id, fallback_model_id)
                if fallback_model_id
                else None
            ),
            "premium_bean_alias": premium_alias,
            "evidence": evidence_refs,
            "escalation_rate": escalation_rate,
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
            "ratings": ratings_section,
            "reason": reason,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "tools/generate_policy.py",
        "source": "roastery/tasting_notes.md",
        "note": "Generated policy. Do not hand-edit. Re-run tools/generate_policy.py.",
        "min_rating_sample_size": min_rating_sample_size,
        "roastery_weight": roastery_weight,
        "escalation_rate_flag_threshold": escalation_rate_flag_threshold,
        "escalation_candidates": escalation_candidates,
        "task_types": policy_entries,
    }


def render_policy_yaml(policy: dict) -> str:
    """Shared by the write path and --dry-run's diff path (and by
    router/app/main.py's policy-rebuild endpoints) so a preview and its
    later apply can never drift from each other - the exact text a diff
    was computed against is the exact text that gets written."""

    buf = io.StringIO()
    buf.write("# Coffee Core Router - generated routing policy\n")
    buf.write("# Generated by tools/generate_policy.py. Do not hand-edit.\n")
    buf.write("# Re-run the generator after new Roastery evidence lands, then review\n")
    buf.write("# the diff before committing, like any other generated artifact.\n\n")
    yaml.safe_dump(
        policy, buf, sort_keys=False, default_flow_style=False, allow_unicode=True, width=4096
    )
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasting-notes", type=Path, default=DEFAULT_TASTING_NOTES)
    parser.add_argument("--beans", type=Path, default=DEFAULT_BEANS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--min-rating-sample-size", type=int, default=DEFAULT_MIN_RATING_SAMPLE_SIZE)
    parser.add_argument("--roastery-weight", type=float, default=DEFAULT_ROASTERY_WEIGHT)
    parser.add_argument(
        "--escalation-rate-flag-threshold", type=float, default=DEFAULT_ESCALATION_RATE_FLAG_THRESHOLD
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the diff against the current --output file instead of writing it.",
    )
    args = parser.parse_args()

    tasting_notes_text = args.tasting_notes.read_text(encoding="utf-8")
    with open(args.beans, "r", encoding="utf-8") as handle:
        beans_config = yaml.safe_load(handle)
    ledger_rows = load_ledger_rows(args.ledger)

    evidence = parse_tasting_notes(tasting_notes_text)
    policy = build_policy(
        evidence,
        beans_config,
        ledger_rows=ledger_rows,
        min_rating_sample_size=args.min_rating_sample_size,
        roastery_weight=args.roastery_weight,
        escalation_rate_flag_threshold=args.escalation_rate_flag_threshold,
    )
    new_text = render_policy_yaml(policy)

    if args.dry_run:
        old_text = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        diff = "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=str(args.output),
                tofile=f"{args.output} (proposed)",
            )
        )
        print(diff if diff else "No changes.")
        return 0

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(new_text)

    evidence_based = sum(1 for e in policy["task_types"].values() if e["status"] == "evidence_based")
    default_only = sum(1 for e in policy["task_types"].values() if e["status"] == "default")
    print(f"Wrote {args.output}")
    print(f"Task types with real Roastery evidence: {evidence_based}")
    print(f"Task types on default (no evidence): {default_only}")
    if policy["escalation_candidates"]:
        print(f"Escalation-rate candidates (advisory only): {policy['escalation_candidates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

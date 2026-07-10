"""Heuristic request classifier for the Coffee Core Router.

Produces task_type, complexity (Barista Charter's own "espresso_shot" /
"cold_brew" work-mode vocabulary - see BARISTA_CHARTER.md), and
needs_vision. The heuristic is a data table (TASK_TYPE_RULES,
COMPLEXITY_SIGNALS), not scattered if-statements, so it stays tunable
without touching classification control flow.

An optional cheap-model classification fallback exists behind
settings.classifier_model_fallback_enabled (default off, Requirement 3). It
is only invoked when the heuristic's confidence is low; the caller supplies
the model-call function so this module never makes a network call itself
and stays fully testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Literal, Optional, Sequence

Complexity = Literal["espresso_shot", "cold_brew"]

QUESTION_WORDS = (
    "what",
    "how",
    "why",
    "when",
    "where",
    "who",
    "which",
    "can",
    "could",
    "should",
    "is",
    "are",
    "do",
    "does",
)

MULTI_STEP_KEYWORDS = (
    "step by step",
    "entire repo",
    "whole repo",
    "whole repository",
    "multiple files",
    "end to end",
    "across the codebase",
    "every module",
    "long-running",
)


@dataclass(frozen=True)
class TaskTypeRule:
    task_type: str
    keywords: Sequence[str]
    typical_style: Literal["question", "command", "either"] = "either"
    code_fence_bonus: float = 0.0


# Ordered by specificity: more specific task types first so a prompt that
# matches both "refactor" and generic "code" keywords resolves to the more
# specific one on a tie (see _break_tie).
TASK_TYPE_RULES: List[TaskTypeRule] = [
    TaskTypeRule(
        task_type="refactor",
        keywords=(
            "refactor",
            "clean up this code",
            "restructure",
            "extract method",
            "extract function",
            "simplify this code",
            "rename this",
            "improve readability",
        ),
        typical_style="command",
        code_fence_bonus=1.0,
    ),
    TaskTypeRule(
        task_type="doc",
        keywords=(
            "document",
            "docstring",
            "readme",
            "write documentation",
            "changelog",
            "comment this",
            "write a guide",
        ),
        typical_style="command",
        code_fence_bonus=0.5,
    ),
    TaskTypeRule(
        task_type="code",
        keywords=(
            "implement",
            "write a function",
            "write code",
            "fix the bug",
            "fix this bug",
            "unit test",
            "debug",
            "add a feature",
            "def ",
            "class ",
        ),
        typical_style="command",
        code_fence_bonus=1.0,
    ),
    TaskTypeRule(
        task_type="analysis",
        keywords=(
            "analyze",
            "analyse",
            "review this code",
            "audit",
            "assess",
            "evaluate",
            "find bugs",
            "find issues",
            "risk assessment",
        ),
        typical_style="either",
        code_fence_bonus=0.5,
    ),
    TaskTypeRule(
        task_type="research",
        keywords=(
            "research",
            "compare",
            "investigate",
            "find out",
            "look into",
            "survey",
            "pros and cons",
            "what are the options",
            "which is better",
        ),
        typical_style="question",
    ),
    TaskTypeRule(
        task_type="explain",
        keywords=(
            "explain",
            "what does this do",
            "how does this work",
            "walk me through",
            "describe",
            "help me understand",
        ),
        typical_style="question",
    ),
]

DEFAULT_TASK_TYPE = "explain"


@dataclass(frozen=True)
class Attachment:
    filename: str
    content_type: str


@dataclass(frozen=True)
class ClassificationResult:
    task_type: str
    complexity: Complexity
    needs_vision: bool
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    used_model_fallback: bool = False


def _is_question(text: str) -> bool:
    stripped = text.strip()
    if stripped.endswith("?"):
        return True
    first_word = stripped.split(" ", 1)[0].lower().strip(",.!?") if stripped else ""
    return first_word in QUESTION_WORDS


def _score_rule(rule: TaskTypeRule, lowered_text: str, is_question: bool, has_code_fence: bool) -> float:
    score = float(sum(1 for keyword in rule.keywords if keyword in lowered_text))
    if score == 0:
        return 0.0
    if rule.typical_style != "either":
        style_matches = (rule.typical_style == "question") == is_question
        score += 0.5 if style_matches else 0.0
    if has_code_fence:
        score += rule.code_fence_bonus
    return score


def classify_heuristic(
    text: str,
    attachments: Optional[Sequence[Attachment]] = None,
) -> ClassificationResult:
    attachments = attachments or []
    lowered = text.lower()
    has_code_fence = "```" in text
    is_question = _is_question(text)

    scored = [
        (rule, _score_rule(rule, lowered, is_question, has_code_fence))
        for rule in TASK_TYPE_RULES
    ]
    scored = [(rule, score) for rule, score in scored if score > 0]

    if not scored:
        task_type = DEFAULT_TASK_TYPE
        confidence = 0.2
        matched_keywords: List[str] = []
    else:
        scored.sort(key=lambda pair: pair[1], reverse=True)
        best_rule, best_score = scored[0]
        task_type = best_rule.task_type
        matched_keywords = [kw for kw in best_rule.keywords if kw in lowered]
        # Confidence: normalized by how far ahead the top match is from the
        # runner-up, capped at 1.0. A single unopposed match is still
        # moderately confident; a close tie is not.
        second_score = scored[1][1] if len(scored) > 1 else 0.0
        confidence = min(1.0, 0.5 + (best_score - second_score) * 0.15)

    complexity = _classify_complexity(text, has_code_fence, attachments)
    needs_vision = any(a.content_type.startswith("image/") for a in attachments)

    return ClassificationResult(
        task_type=task_type,
        complexity=complexity,
        needs_vision=needs_vision,
        confidence=confidence,
        matched_keywords=matched_keywords,
    )


def _classify_complexity(
    text: str,
    has_code_fence: bool,
    attachments: Sequence[Attachment],
) -> Complexity:
    lowered = text.lower()
    code_fence_lines = text.count("\n") if has_code_fence else 0

    if len(text) > 1500:
        return "cold_brew"
    if code_fence_lines > 80:
        return "cold_brew"
    # Brew 38 (docs/design/attachments-design.md Section 7, Decision 3):
    # any attachment at all pushes toward cold_brew - simple and
    # predictable rather than a size/kind-dependent table. Refine with
    # real usage data later if this proves too blunt.
    if len(attachments) > 0:
        return "cold_brew"
    if any(keyword in lowered for keyword in MULTI_STEP_KEYWORDS):
        return "cold_brew"
    return "espresso_shot"


def classify(
    text: str,
    attachments: Optional[Sequence[Attachment]] = None,
    *,
    model_fallback_enabled: bool = False,
    model_fallback_confidence_threshold: float = 0.4,
    model_classify_fn: Optional[Callable[[str], ClassificationResult]] = None,
) -> ClassificationResult:
    """Classify a request. Heuristic first, optional cheap-model fallback.

    model_classify_fn is caller-supplied so this module never performs a
    network call itself - tests inject a fake, main.py wires a real one
    only when settings.classifier_model_fallback_enabled is true.
    """

    result = classify_heuristic(text, attachments)
    if (
        model_fallback_enabled
        and model_classify_fn is not None
        and result.confidence < model_fallback_confidence_threshold
    ):
        fallback_result = model_classify_fn(text)
        return ClassificationResult(
            task_type=fallback_result.task_type,
            complexity=fallback_result.complexity,
            needs_vision=result.needs_vision or fallback_result.needs_vision,
            confidence=fallback_result.confidence,
            matched_keywords=fallback_result.matched_keywords,
            used_model_fallback=True,
        )
    return result

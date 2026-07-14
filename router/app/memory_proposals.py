"""Session memory proposals for the Coffee Core Router (Brew 41).

Generates a proposed diff to the two real memory-bank files this repo
uses - `brew-log/active_context.md` and `brew-log/progress.md` (this
repo's equivalent of "memory-bank/activeContext.md"/"progress.md" - see
docs/design/memory-and-pantry-design.md Section 2, Gap 1) - from a
session transcript, using a cheap Bean. Never writes memory without an
explicit POST .../approve call (Constitution's learning-loop rules): a
proposal is inert until a human approves it, and even then both
guardrails below are re-checked against the live on-disk content before
anything is written.
"""

from __future__ import annotations

import difflib
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from router.app.aliases import BeanRegistry
from router.app.openrouter_client import stream_order
from router.app.sessions import MessageRecord, SessionStore

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The *only* two paths a proposal may ever touch (Requirement 3) - not a
# prefix rule over brew-log/, exactly these two literal files.
ALLOWED_PATHS: Tuple[str, ...] = ("brew-log/active_context.md", "brew-log/progress.md")

MAX_DELETED_FRACTION = 0.5

_FILE_BLOCK_PATTERN = re.compile(
    r"### FILE:\s*(?P<path>\S+)\s*\r?\n(?P<content>.*?)\r?\n### END FILE",
    re.DOTALL,
)


class MemoryProposalError(Exception):
    """The model response could not be parsed into the strict two-file format."""


class MemoryProposalGuardrailError(Exception):
    """A proposal (or a re-check at approval time) violates the path
    allowlist or over-deletion guardrail."""


@dataclass(frozen=True)
class MemoryProposalFile:
    path: str
    old_content: str
    new_content: str
    diff: str


@dataclass(frozen=True)
class MemoryProposal:
    proposal_id: str
    session_id: str
    bean_alias: str
    model_id: Optional[str]
    files: List[MemoryProposalFile]
    tokens_in: int
    tokens_out: int
    cost_usd: Optional[float]
    latency_ms: int


def read_current_content(path: str, *, repo_root: Path = REPO_ROOT) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def _non_blank_lines(text: str) -> List[str]:
    return [line for line in text.splitlines() if line.strip()]


def check_path_allowed(path: str, *, repo_root: Path = REPO_ROOT) -> Optional[str]:
    """Guardrail 1 (Requirement 3): the only writable paths are the exact
    literal strings in ALLOWED_PATHS - not a `brew-log/` prefix rule, and
    not `memory-bank/...`-style near-misses. Also confirms the path
    resolves to exactly the expected on-disk location, as defense in
    depth against a symlink escape."""

    if path not in ALLOWED_PATHS:
        return f"{path!r} is not one of the two allowed memory files: {ALLOWED_PATHS}."
    resolved = (repo_root / path).resolve()
    expected = (repo_root.resolve() / path)
    if resolved != expected:
        return f"{path!r} does not resolve to the expected on-disk file."
    return None


def check_over_deletion(
    old_content: str, new_content: str, *, max_deleted_fraction: float = MAX_DELETED_FRACTION
) -> Optional[str]:
    """Guardrail 2 (Requirement 3, stale-memory protection): refuses a
    proposal that deletes more than `max_deleted_fraction` of the
    existing non-blank lines, including the degenerate "wipe the file and
    write one new line" case. An empty/nonexistent original file has
    nothing to lose, so it's never blocked by this check."""

    old_lines = _non_blank_lines(old_content)
    if not old_lines:
        return None
    new_lines = _non_blank_lines(new_content)
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    deleted = len(old_lines) - matched
    fraction = deleted / len(old_lines)
    if fraction > max_deleted_fraction:
        return (
            f"Proposed content for this file deletes {deleted}/{len(old_lines)} "
            f"existing non-blank lines ({fraction:.0%}), over the "
            f"{max_deleted_fraction:.0%} stale-memory-protection guardrail."
        )
    return None


def compute_unified_diff(old_content: str, new_content: str, path: str) -> str:
    diff_lines = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff_lines)


def build_transcript_text(messages: List[MessageRecord], *, max_chars: int) -> str:
    """Plain-text `role: content` transcript, truncated from the start
    (keeping the most recent messages) when it exceeds max_chars - a
    close-out proposal cares most about where the session ended up."""

    lines = [f"{message.role}: {message.content}" for message in messages]
    text = "\n\n".join(lines)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


_PROPOSAL_INSTRUCTIONS = """You are drafting a session close-out proposal for Project Coffee's memory bank.

Below are the CURRENT contents of the two memory files, followed by this session's transcript. Propose the COMPLETE new content for each file - not a diff, not an appended fragment - incorporating anything from this session worth remembering (decisions, progress, open questions) while preserving existing content that is still accurate. If nothing in this session is worth recording, it is fine to return the files unchanged.

Output STRICTLY in this format and nothing else - no commentary before, between, or after the two blocks:

### FILE: brew-log/active_context.md
<complete new file content>
### END FILE

### FILE: brew-log/progress.md
<complete new file content>
### END FILE
"""


def build_generation_prompt(transcript_text: str, current_content: Dict[str, str]) -> str:
    parts = [_PROPOSAL_INSTRUCTIONS]
    for path in ALLOWED_PATHS:
        parts.append(
            f"--- Current content of {path} ---\n{current_content.get(path, '')}\n--- end of {path} ---"
        )
    parts.append(f"--- Session transcript ---\n{transcript_text}\n--- end of transcript ---")
    return "\n\n".join(parts)


def parse_proposal_response(raw_text: str) -> Dict[str, str]:
    """Strict parse of the ### FILE: ... ### END FILE format (Section 3.1,
    step 3). Never guesses which part goes where - any missing marker,
    disallowed path, or duplicate block is a hard MemoryProposalError, not
    a best-effort partial result."""

    matches = _FILE_BLOCK_PATTERN.findall(raw_text)
    if not matches:
        raise MemoryProposalError(
            "Model response did not contain any '### FILE: ... ### END FILE' blocks."
        )

    parsed: Dict[str, str] = {}
    for path, content in matches:
        path = path.strip()
        if path not in ALLOWED_PATHS:
            raise MemoryProposalError(f"Model proposed writing to disallowed path {path!r}.")
        if path in parsed:
            raise MemoryProposalError(f"Model response contained more than one block for {path!r}.")
        stripped_content = content.strip("\n")
        parsed[path] = f"{stripped_content}\n" if stripped_content else ""

    missing = [path for path in ALLOWED_PATHS if path not in parsed]
    if missing:
        raise MemoryProposalError(f"Model response is missing block(s) for: {missing}.")

    return parsed


async def _run_blocking_generation(stream_order_fn, model_id: str, prompt: str) -> Tuple[str, int]:
    """Consumes a full stream_order_fn stream to build one complete
    response - a plain blocking call, not SSE (approved Question 3: no
    multi-minute human-wait phase here, so Brew 40's background-task/
    heartbeat machinery is deliberately not reused)."""

    text = ""
    tokens_out = 0
    async for chunk in stream_order_fn(model_id, prompt):
        if chunk.content_delta:
            text += chunk.content_delta
        if chunk.usage and isinstance(chunk.usage.get("completion_tokens"), int):
            tokens_out = chunk.usage["completion_tokens"]
        if chunk.is_final:
            break
    if not tokens_out:
        tokens_out = max(1, len(text) // 4)
    return text, tokens_out


async def generate_memory_proposal(
    *,
    session_id: str,
    session_store: SessionStore,
    bean_registry: BeanRegistry,
    bean_alias: str,
    max_transcript_chars: int,
    stream_order_fn=stream_order,
    repo_root: Path = REPO_ROOT,
) -> MemoryProposal:
    """Full generation flow (Section 3.1): transcript -> prompt -> one
    model call -> strict parse -> both guardrails -> unified diffs. Raises
    MemoryProposalError (unparseable response) or
    MemoryProposalGuardrailError (guardrail violation) - callers turn
    either into a 422 before the UI ever sees a bad proposal."""

    started_at = time.monotonic()
    messages = session_store.get_messages(session_id)
    transcript_text = build_transcript_text(messages, max_chars=max_transcript_chars)
    current_content = {path: read_current_content(path, repo_root=repo_root) for path in ALLOWED_PATHS}
    prompt = build_generation_prompt(transcript_text, current_content)

    bean = bean_registry.by_alias(bean_alias)
    generated_text, tokens_out = await _run_blocking_generation(stream_order_fn, bean.model_id, prompt)

    parsed = parse_proposal_response(generated_text)

    files: List[MemoryProposalFile] = []
    for path in ALLOWED_PATHS:
        new_content = parsed[path]
        old_content = current_content[path]
        violation = check_path_allowed(path, repo_root=repo_root) or check_over_deletion(
            old_content, new_content
        )
        if violation:
            raise MemoryProposalGuardrailError(violation)
        files.append(
            MemoryProposalFile(
                path=path,
                old_content=old_content,
                new_content=new_content,
                diff=compute_unified_diff(old_content, new_content, path),
            )
        )

    tokens_in = max(1, len(prompt) // 4)
    latency_ms = int((time.monotonic() - started_at) * 1000)
    cost_usd = (
        0.0
        if bean.price_per_1k_input_usd == 0.0 and bean.price_per_1k_output_usd == 0.0
        else None
    )

    return MemoryProposal(
        proposal_id=str(uuid.uuid4()),
        session_id=session_id,
        bean_alias=bean_alias,
        model_id=bean.model_id,
        files=files,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


def approve_memory_proposal(proposal: MemoryProposal, *, repo_root: Path = REPO_ROOT) -> None:
    """Re-runs both guardrails against the CURRENT on-disk content (not
    the proposal's stale snapshot) before writing anything - defense
    against a race where the file changed between generation and
    approval. All-or-nothing: if any file fails, nothing is written."""

    for file in proposal.files:
        current_on_disk = read_current_content(file.path, repo_root=repo_root)
        violation = check_path_allowed(file.path, repo_root=repo_root) or check_over_deletion(
            current_on_disk, file.new_content
        )
        if violation:
            raise MemoryProposalGuardrailError(violation)

    for file in proposal.files:
        (repo_root / file.path).write_text(file.new_content, encoding="utf-8")

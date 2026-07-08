"""Build preview-only Project Coffee context packages.

This module prepares a local review object for future approval-gated remote
work. It does not call models, use network APIs, read credential files, or send
data anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


PACKAGE_VERSION = "context-package-v1"
DEFAULT_BREW_SHOT = "Brew 34 / Shot 34A"
DEFAULT_MAX_CONTEXT_ITEMS = 5

UNSAFE_PATH_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".aws",
    ".gcp",
    ".azure",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".cache",
}

UNSAFE_FILE_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".sqlite",
    ".db",
}

UNSAFE_PATH_MARKERS = (
    "credential",
    "credentials",
    "secret",
    "secrets",
    "token",
    "tokens",
)

SUSPICIOUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenRouter key-like value", re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{12,}\b")),
    ("OpenAI key-like value", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key-like value", re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token-like value", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("GitHub token-like value", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("Bearer token-like value", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.IGNORECASE)),
    ("private key material-like value", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

BROAD_CONTEXT_TERMS = (
    "whole repo",
    "entire repo",
    "full repo",
    "whole repository",
    "entire repository",
    "full repository",
    "repository dump",
    "repo dump",
)

REQUEST_BLOCKED_PATH_PATTERNS = (
    ".env",
    ".env.",
    ".ssh",
    ".aws",
    ".gcp",
    ".azure",
)


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _mapping_from_object(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "__dict__"):
        return value.__dict__
    return {}


def is_unsafe_path(path_text: str) -> tuple[bool, str | None]:
    normalized = path_text.replace("\\", "/").strip()
    if not normalized:
        return False, None

    path = Path(normalized)
    name = path.name.lower()
    parts = [part.lower() for part in Path(normalized).parts]
    posix_parts = [part for chunk in normalized.split("/") for part in chunk.split("\\") if part]
    lowered_posix_parts = [part.lower() for part in posix_parts]

    for part in parts + lowered_posix_parts:
        if part in UNSAFE_PATH_PARTS:
            return True, f"blocked path component `{part}`"
        if part.startswith(".env."):
            return True, "blocked .env.* path"
        if any(marker in part for marker in UNSAFE_PATH_MARKERS):
            return True, f"sensitive-looking path component `{part}`"
    if len(lowered_posix_parts) >= 2 and lowered_posix_parts[0] == "roastery":
        if lowered_posix_parts[1] in {"local_cup_outputs", "local_reports"}:
            return True, f"blocked local Roastery artifact path `{lowered_posix_parts[1]}`"

    if name.startswith(".env."):
        return True, "blocked .env.* path"
    if path.suffix.lower() in UNSAFE_FILE_SUFFIXES:
        return True, f"blocked file suffix `{path.suffix.lower()}`"
    return False, None


def redact_or_label_suspicious_text(text: str, *, location: str = "text") -> dict[str, Any]:
    """Redact suspicious secret-like values and return labels, never values."""

    redacted = _as_text(text)
    labels: list[str] = []
    notes: list[dict[str, str]] = []

    for label, pattern in SUSPICIOUS_PATTERNS:
        if not pattern.search(redacted):
            continue
        labels.append(label)
        notes.append(
            {
                "location": location,
                "label": label,
                "action": "redacted suspicious value",
            }
        )
        redacted = pattern.sub(f"[REDACTED: {label}]", redacted)

    return {
        "text": redacted,
        "labels": sorted(set(labels)),
        "redaction_notes": notes,
    }


def normalize_evidence_item(
    item: Mapping[str, Any] | Any,
    *,
    rank: int,
) -> dict[str, Any]:
    raw = _mapping_from_object(item)
    path = _as_text(raw.get("source_path") or raw.get("path") or raw.get("title"))
    heading = _as_text(raw.get("heading") or raw.get("title") or "")
    title = heading or path or f"Evidence item {rank}"
    snippet_result = redact_or_label_suspicious_text(
        _as_text(raw.get("snippet")),
        location=f"evidence item {rank}",
    )

    unsafe, reason = is_unsafe_path(path)
    suspicious_labels = snippet_result["labels"]
    included = not unsafe and not suspicious_labels
    exclusion_reason = reason if unsafe else None
    if suspicious_labels:
        exclusion_reason = "suspicious content: " + ", ".join(suspicious_labels)

    return {
        "title": title,
        "path": path,
        "heading": heading,
        "snippet": snippet_result["text"],
        "score": _as_int(raw.get("score"), default=_as_int(raw.get("rank"), default=0)),
        "rank": rank,
        "source_type": _as_text(raw.get("source_type") or raw.get("safety_classification") or "local-evidence"),
        "reason_selected": _as_text(raw.get("reason_selected")),
        "freshness_signal": _as_text(raw.get("freshness_signal") or "unknown"),
        "included": included,
        "exclusion_reason": exclusion_reason,
        "redaction_notes": snippet_result["redaction_notes"],
    }


def _normalize_selected_file(file_item: Mapping[str, Any] | str | Any) -> dict[str, Any]:
    if isinstance(file_item, str):
        raw: Mapping[str, Any] = {"path": file_item}
    else:
        raw = _mapping_from_object(file_item)
    path = _as_text(raw.get("path") or raw.get("source_path"))
    unsafe, reason = is_unsafe_path(path)
    return {
        "path": path,
        "reason": _as_text(raw.get("reason") or "selected for context preview"),
        "safety_classification": _as_text(raw.get("safety_classification") or raw.get("source_type") or "local-evidence"),
        "freshness_signal": _as_text(raw.get("freshness_signal") or "unknown"),
        "included": not unsafe,
        "exclusion_reason": reason,
    }


def run_context_safety_gate(
    *,
    request_text: str = "",
    selected_files: Sequence[Mapping[str, Any] | str | Any] | None = None,
    evidence_items: Sequence[Mapping[str, Any] | Any] | None = None,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    excluded_paths: list[dict[str, str]] = []
    redaction_notes: list[dict[str, str]] = []

    request_scan = redact_or_label_suspicious_text(request_text, location="request_text")
    if request_scan["labels"]:
        blocked_reasons.append("Suspicious content detected in request_text.")
        redaction_notes.extend(request_scan["redaction_notes"])

    lowered_request = request_text.lower()
    if any(term in lowered_request for term in BROAD_CONTEXT_TERMS):
        blocked_reasons.append("Request asks for broad repository context; narrow to selected evidence or files first.")
        excluded_paths.append(
            {
                "path": "whole repository",
                "reason": "broad repository dumps are not allowed in context packages",
            }
        )

    for pattern in REQUEST_BLOCKED_PATH_PATTERNS:
        if pattern in lowered_request:
            blocked_reasons.append(f"Request asks for blocked path pattern `{pattern}`.")
            excluded_paths.append(
                {
                    "path": pattern,
                    "reason": "blocked path pattern requested",
                }
            )

    for file_item in selected_files or []:
        normalized = _normalize_selected_file(file_item)
        if not normalized["included"]:
            blocked_reasons.append(f"Selected file is unsafe: {normalized['path']}")
            excluded_paths.append(
                {
                    "path": normalized["path"],
                    "reason": normalized["exclusion_reason"] or "unsafe path",
                }
            )

    for index, raw_item in enumerate(evidence_items or [], start=1):
        item = normalize_evidence_item(raw_item, rank=index)
        if not item["included"]:
            if item["exclusion_reason"] and item["exclusion_reason"].startswith("suspicious content"):
                blocked_reasons.append(f"Suspicious content detected in evidence item {index}.")
            else:
                warnings.append(f"Evidence item {index} excluded by path safety.")
            if item["path"]:
                excluded_paths.append(
                    {
                        "path": item["path"],
                        "reason": item["exclusion_reason"] or "unsafe evidence item",
                    }
                )
        redaction_notes.extend(item["redaction_notes"])

    status = "passed"
    if blocked_reasons:
        status = "blocked"
    elif warnings or excluded_paths or redaction_notes:
        status = "warning"

    return {
        "status": status,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "excluded_paths": excluded_paths,
        "redaction_notes": redaction_notes,
    }


def estimate_context_tokens(value: Any) -> int:
    if isinstance(value, str):
        character_count = len(value)
    else:
        character_count = len(json.dumps(value, sort_keys=True, ensure_ascii=False))
    return int(math.ceil(character_count / 4))


def _normalize_route_decision(route_decision: Mapping[str, Any] | Any) -> dict[str, Any]:
    raw = _mapping_from_object(route_decision)
    return {
        "request_class": _as_text(raw.get("request_class") or "unknown"),
        "selected_mode": _as_text(raw.get("selected_mode") or raw.get("mode") or "local evidence only"),
        "approval_required": bool(raw.get("approval_required", False)),
        "reason": _as_text(raw.get("reason")),
        "allowed_context": _as_text(raw.get("allowed_context")),
        "blocked_context": _as_text(raw.get("blocked_context")),
        "next_safe_action": _as_text(raw.get("next_safe_action")),
    }


def _included_selected_files(
    selected_files: Sequence[Mapping[str, Any] | str | Any] | None,
    evidence_items: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_files = [_normalize_selected_file(item) for item in selected_files or []]
    if not normalized_files:
        seen: set[str] = set()
        for item in evidence_items:
            path = item["path"]
            if not item["included"] or not path or path in seen:
                continue
            seen.add(path)
            normalized_files.append(
                {
                    "path": path,
                    "reason": "evidence item source",
                    "safety_classification": item["source_type"],
                    "freshness_signal": item["freshness_signal"],
                    "included": True,
                    "exclusion_reason": None,
                }
            )
    return [item for item in normalized_files if item["included"]]


def build_context_package(
    *,
    request_text: str,
    route_decision: Mapping[str, Any] | Any,
    active_root: str | Path,
    evidence_items: Sequence[Mapping[str, Any] | Any] | None = None,
    selected_files: Sequence[Mapping[str, Any] | str | Any] | None = None,
    max_context_items: int = DEFAULT_MAX_CONTEXT_ITEMS,
    brew_shot: str = DEFAULT_BREW_SHOT,
    package_version: str = PACKAGE_VERSION,
) -> dict[str, Any]:
    if max_context_items < 1:
        max_context_items = 1

    route = _normalize_route_decision(route_decision)
    raw_evidence = list(evidence_items or [])[:max_context_items]
    normalized_evidence = [
        normalize_evidence_item(item, rank=index)
        for index, item in enumerate(raw_evidence, start=1)
    ]
    included_evidence = [item for item in normalized_evidence if item["included"]]
    selected = _included_selected_files(selected_files, included_evidence)

    gate = run_context_safety_gate(
        request_text=request_text,
        selected_files=selected_files,
        evidence_items=raw_evidence,
    )

    package: dict[str, Any] = {
        "package_version": package_version,
        "package_status": "preview_only" if gate["status"] != "blocked" else "blocked",
        "request_text": redact_or_label_suspicious_text(request_text, location="request_text")["text"],
        "route_decision": route,
        "active_root": str(active_root),
        "selected_files": selected,
        "evidence_items": normalized_evidence,
        "excluded_paths": gate["excluded_paths"],
        "safety_checks": gate,
        "estimated_tokens": 0,
        "max_context_items": max_context_items,
        "user_approval": {
            "approved": False,
            "approval_timestamp": None,
            "approved_context_hash": None,
        },
        "timestamp": timestamp(),
        "brew_shot": brew_shot,
        "provider_model": {
            "provider": None,
            "model": None,
            "status": "not_selected",
        },
        "ledger_plan": {
            "ledger_path": "ledger/cost_log.md",
            "status": "preview_only",
            "planned_fields": [
                "date/time",
                "Brew/Shot",
                "request",
                "route",
                "approval status",
                "provider",
                "model",
                "estimated tokens",
                "actual tokens",
                "estimated cost",
                "actual cost",
                "Safety Gate result",
                "context summary",
                "included count",
                "excluded count",
                "outcome",
                "no-secrets confirmation",
            ],
        },
    }
    package["estimated_tokens"] = estimate_context_tokens(
        {
            "request_text": package["request_text"],
            "route_decision": package["route_decision"],
            "selected_files": package["selected_files"],
            "evidence_items": [
                {
                    "path": item["path"],
                    "heading": item["heading"],
                    "snippet": item["snippet"],
                }
                for item in package["evidence_items"]
                if item["included"]
            ],
        }
    )
    return package


def summarize_context_package(package: Mapping[str, Any]) -> dict[str, Any]:
    evidence_items = list(package.get("evidence_items", []))
    selected_files = list(package.get("selected_files", []))
    excluded_paths = list(package.get("excluded_paths", []))
    included_items = [item for item in evidence_items if isinstance(item, Mapping) and item.get("included")]
    excluded_items = [item for item in evidence_items if isinstance(item, Mapping) and not item.get("included")]
    safety = package.get("safety_checks", {})
    safety_status = safety.get("status", "unknown") if isinstance(safety, Mapping) else "unknown"
    route = package.get("route_decision", {})
    route_mode = route.get("selected_mode", "unknown") if isinstance(route, Mapping) else "unknown"
    return {
        "package_status": package.get("package_status", "unknown"),
        "active_root": package.get("active_root", ""),
        "route_decision": route_mode,
        "estimated_tokens": package.get("estimated_tokens", 0),
        "evidence_item_count": len(evidence_items),
        "included_item_count": len(included_items),
        "excluded_item_count": len(excluded_items) + len(excluded_paths),
        "selected_file_count": len(selected_files),
        "safety_status": safety_status,
        "provider_model_status": (
            package.get("provider_model", {}).get("status", "unknown")
            if isinstance(package.get("provider_model"), Mapping)
            else "unknown"
        ),
        "approval_status": "approved" if package.get("user_approval", {}).get("approved") else "not_approved",
    }

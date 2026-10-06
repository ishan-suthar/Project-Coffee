"""Dry-run approval helpers for Project Coffee context packages.

The helpers in this module model local approval state only. They do not call
models, use network APIs, write Ledger entries, or send context anywhere.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


APPROVAL_LOCAL_ONLY = "local_only_no_approval"
APPROVAL_NEEDED = "approval_needed"
APPROVAL_CONTEXT_READY = "context_preview_ready"
APPROVAL_BLOCKED = "blocked_by_safety_gate"
APPROVAL_DRY_RUN_APPROVED = "dry_run_approved"
APPROVAL_DRY_RUN_CANCELLED = "dry_run_cancelled"
APPROVAL_SEND_DISABLED = "send_disabled_future_brew"

REQUIRED_CHECKLIST_ITEMS: tuple[str, ...] = (
    "I reviewed the request text.",
    "I reviewed included evidence.",
    "I reviewed excluded paths.",
    "I reviewed safety warnings.",
    "I understand no model call will happen in Brew 35.",
    "I understand this is a dry-run approval only.",
)


def _package_mapping(package: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return package if isinstance(package, Mapping) else {}


def _route_mapping(package: Mapping[str, Any]) -> Mapping[str, Any]:
    route = package.get("route_decision", {})
    return route if isinstance(route, Mapping) else {}


def _safety_mapping(package: Mapping[str, Any]) -> Mapping[str, Any]:
    safety = package.get("safety_checks", {})
    return safety if isinstance(safety, Mapping) else {}


def _provider_model_mapping(package: Mapping[str, Any]) -> Mapping[str, Any]:
    provider_model = package.get("provider_model", {})
    return provider_model if isinstance(provider_model, Mapping) else {}


def build_approval_checklist_state(
    checked_items: Mapping[str, bool] | Sequence[str] | None = None,
) -> dict[str, bool]:
    if checked_items is None:
        checked: set[str] = set()
    elif isinstance(checked_items, Mapping):
        checked = {item for item, value in checked_items.items() if bool(value)}
    else:
        checked = {str(item) for item in checked_items}
    return {item: item in checked for item in REQUIRED_CHECKLIST_ITEMS}


def checklist_complete(checklist_state: Mapping[str, bool]) -> bool:
    return all(bool(checklist_state.get(item, False)) for item in REQUIRED_CHECKLIST_ITEMS)


def can_dry_run_approve(
    package: Mapping[str, Any] | None,
    checklist_state: Mapping[str, bool] | None,
) -> bool:
    package_map = _package_mapping(package)
    if not package_map:
        return False
    if _safety_mapping(package_map).get("status") == "blocked":
        return False
    if not _route_mapping(package_map).get("approval_required", False):
        return False
    return checklist_complete(checklist_state or {})


def determine_approval_state(
    package: Mapping[str, Any] | None,
    checklist_state: Mapping[str, bool] | None = None,
    *,
    dry_run_approved: bool = False,
    dry_run_cancelled: bool = False,
) -> str:
    package_map = _package_mapping(package)
    if dry_run_cancelled:
        return APPROVAL_DRY_RUN_CANCELLED
    if not package_map:
        return APPROVAL_NEEDED
    if _safety_mapping(package_map).get("status") == "blocked":
        return APPROVAL_BLOCKED
    route = _route_mapping(package_map)
    if not route.get("approval_required", False):
        return APPROVAL_LOCAL_ONLY
    if dry_run_approved and can_dry_run_approve(package_map, checklist_state or {}):
        return APPROVAL_DRY_RUN_APPROVED
    return APPROVAL_CONTEXT_READY


def summarize_approval_requirements(
    package: Mapping[str, Any] | None,
    checklist_state: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    package_map = _package_mapping(package)
    checklist = checklist_state or {}
    safety = _safety_mapping(package_map)
    return {
        "has_package": bool(package_map),
        "safety_status": safety.get("status", "missing"),
        "checklist_complete": checklist_complete(checklist),
        "can_dry_run_approve": can_dry_run_approve(package_map, checklist),
        "send_state": APPROVAL_SEND_DISABLED,
        "missing_checklist_items": [
            item for item in REQUIRED_CHECKLIST_ITEMS if not bool(checklist.get(item, False))
        ],
    }


def build_dry_run_ledger_preview(
    package: Mapping[str, Any] | None,
    approval_state: str,
) -> dict[str, Any]:
    package_map = _package_mapping(package)
    route = _route_mapping(package_map)
    safety = _safety_mapping(package_map)
    provider_model = _provider_model_mapping(package_map)
    evidence_items = package_map.get("evidence_items", [])
    excluded_paths = package_map.get("excluded_paths", [])
    included_count = 0
    if isinstance(evidence_items, Sequence):
        included_count = sum(
            1 for item in evidence_items if isinstance(item, Mapping) and bool(item.get("included"))
        )
    excluded_count = len(excluded_paths) if isinstance(excluded_paths, Sequence) else 0
    return {
        "brew_shot": package_map.get("brew_shot"),
        "request_summary": str(package_map.get("request_text", ""))[:180],
        "route": route.get("selected_mode"),
        "approval_state": approval_state,
        "provider": provider_model.get("provider"),
        "model": provider_model.get("model"),
        "provider_model_status": provider_model.get("status", "not_selected"),
        "estimated_tokens": package_map.get("estimated_tokens"),
        "estimated_cost": None,
        "safety_status": safety.get("status", "missing"),
        "included_evidence_count": included_count,
        "excluded_path_count": excluded_count,
        "outcome": "dry_run_only",
        "ledger_write_status": "preview_only_not_written",
        "send_state": APPROVAL_SEND_DISABLED,
    }

"""Coffee Core Router configuration loading and startup safety checks.

Loads config/beans.yaml, config/routing_policy.yaml, and config/settings.yaml
once and shares validated settings across routing.py, escalation.py,
ledger.py, aliases.py, and main.py.

Run this router only from the repository root (see router/README.md) so
`tools.coffee_context_package` and `router.app.*` both resolve as
importable packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel

from tools.coffee_context_package import redact_or_label_suspicious_text

ROUTER_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BEANS_PATH = ROUTER_ROOT / "config" / "beans.yaml"
DEFAULT_ROUTING_POLICY_PATH = ROUTER_ROOT / "config" / "routing_policy.yaml"
DEFAULT_SETTINGS_PATH = ROUTER_ROOT / "config" / "settings.yaml"


class StartupSafetyError(Exception):
    """Raised when a config file appears to contain a key-like value."""


class Settings(BaseModel):
    escalation_cost_cap_usd: float = 0.50
    generating_tick_tokens: int = 20
    generating_tick_seconds: float = 2.0
    request_timeout_seconds: int = 60
    classifier_model_fallback_enabled: bool = False
    classifier_model_fallback_bean_alias: str = "House Blend"
    truncation_min_expected_tokens: int = 32
    refusal_keywords: List[str] = []
    max_upload_size_bytes: int = 20_971_520
    pdf_min_extracted_chars: int = 20
    max_inline_text_chars: int = 50_000
    upload_ttl_seconds: int = 3600

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_SETTINGS_PATH) -> "Settings":
        data = _load_yaml(path)
        return cls(**data)


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def assert_no_key_like_strings(paths: List[Path]) -> None:
    """Fail loudly if any config file text matches a known key-like pattern.

    Reuses tools.coffee_context_package's SUSPICIOUS_PATTERNS instead of
    re-implementing secret-pattern matching (see docs/design/
    coffee-core-router-design.md Section 7). Unlike a chat request, a
    key-like value found inside a *config file* means a real key was
    probably committed somewhere it should never be - so this does not
    redact-and-continue, it stops startup.
    """

    for path in paths:
        if not path.is_file():
            continue
        raw_text = path.read_text(encoding="utf-8")
        result = redact_or_label_suspicious_text(raw_text, location=str(path))
        if result["redaction_notes"]:
            labels = ", ".join(note["label"] for note in result["redaction_notes"])
            raise StartupSafetyError(
                f"Refusing to start: {path} contains a key-like value ({labels}). "
                "Remove it and set the real key only via the OPENROUTER_API_KEY "
                "environment variable."
            )


def load_router_config_paths() -> List[Path]:
    return [DEFAULT_BEANS_PATH, DEFAULT_ROUTING_POLICY_PATH, DEFAULT_SETTINGS_PATH]

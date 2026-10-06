"""Raw OpenRouter model ID <-> coffee alias mapping.

This module is the only place raw model IDs are allowed to cross into
alias form. Raw IDs themselves are permitted in exactly three places
(config/beans.yaml, the Coffee Ledger, and outbound OpenRouter requests) -
never in an SSE event or API response field. See EVENT_CONTRACT.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

BEANS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "beans.yaml"


class AliasError(Exception):
    """Raised when a bean alias or raw model ID cannot be resolved."""


class BeanPricingError(Exception):
    """Raised by assert_active_beans_priced() when an active Bean has no
    pricing configured - see that function's docstring."""


@dataclass(frozen=True)
class Bean:
    alias: str
    role: str
    model_id: Optional[str]
    vision: bool
    code: bool
    price_per_1k_input_usd: Optional[float]
    price_per_1k_output_usd: Optional[float]
    status: str
    # Brew 47 (docs/design/openai-compat-endpoint-design.md Section 1):
    # whether this Bean has verified tool-calling support - data only this
    # Brew (a warning is logged when tools are sent to a Bean with this
    # False, but routing does not yet avoid such Beans automatically).
    # Defaults False - unverified/free-tier Beans stay conservative, and
    # every pre-Brew-47 Bean() fixture across the test suite keeps working
    # unchanged.
    tool_calling: bool = False

    @property
    def is_available(self) -> bool:
        return self.model_id is not None and self.status == "active"


class BeanRegistry:
    """Loads config/beans.yaml and resolves aliases <-> raw model IDs."""

    def __init__(self, beans: List[Bean]):
        self._beans = beans
        self._by_alias: Dict[str, Bean] = {bean.alias: bean for bean in beans}
        self._by_model_id: Dict[str, Bean] = {
            bean.model_id: bean for bean in beans if bean.model_id is not None
        }

    @classmethod
    def from_yaml(cls, path: Path = BEANS_CONFIG_PATH) -> "BeanRegistry":
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        beans: List[Bean] = []
        for entry in data.get("beans", []):
            capabilities = entry.get("capabilities") or {}
            beans.append(
                Bean(
                    alias=entry["alias"],
                    role=entry["role"],
                    model_id=entry.get("model_id"),
                    vision=bool(capabilities.get("vision", False)),
                    code=bool(capabilities.get("code", False)),
                    tool_calling=bool(capabilities.get("tool_calling", False)),
                    price_per_1k_input_usd=entry.get("price_per_1k_input_usd"),
                    price_per_1k_output_usd=entry.get("price_per_1k_output_usd"),
                    status=entry.get("status", "active"),
                )
            )
        return cls(beans)

    def all_beans(self) -> List[Bean]:
        return list(self._beans)

    def by_alias(self, alias: str) -> Bean:
        try:
            return self._by_alias[alias]
        except KeyError as exc:
            raise AliasError(f"Unknown bean alias: {alias!r}") from exc

    def by_role(self, role: str) -> Optional[Bean]:
        for bean in self._beans:
            if bean.role == role:
                return bean
        return None

    def alias_for_model_id(self, model_id: str) -> str:
        try:
            return self._by_model_id[model_id].alias
        except KeyError as exc:
            raise AliasError(f"Unknown raw model ID: {model_id!r}") from exc

    def model_id_for_alias(self, alias: str) -> Optional[str]:
        return self.by_alias(alias).model_id

    def known_model_ids(self) -> List[str]:
        return [bean.model_id for bean in self._beans if bean.model_id is not None]

    def known_aliases(self) -> List[str]:
        return [bean.alias for bean in self._beans]

    def vision_capable_beans(self) -> List[Bean]:
        """Available Beans with capabilities.vision: true (Brew 38). As of
        this Brew, config/beans.yaml has none - see docs/design/
        attachments-design.md Section 2, Gap 1 and Section 7 Decision 1:
        vision routing ships structurally correct but inert until a real
        vision-capable Bean is added and Roastery-tested."""

        return [bean for bean in self._beans if bean.vision and bean.is_available]

    def default_vision_bean(self) -> Optional[Bean]:
        """The Bean vision-constrained routing should escalate to: the
        first available vision-capable Bean, preferring one with
        role="default" if more than one qualifies. Returns None when no
        vision-capable Bean is configured - callers must handle that
        explicitly (never silently proceed without the image)."""

        candidates = self.vision_capable_beans()
        if not candidates:
            return None
        for bean in candidates:
            if bean.role == "default":
                return bean
        return candidates[0]

    def capable_bean(
        self, *, tool_calling: bool = False, vision: bool = False, prefer_alias: Optional[str] = None
    ) -> Optional[Bean]:
        """The cheapest available Bean satisfying the given capability
        filters (web-search Brew) - by beans.yaml pricing (combined
        per-1k input+output), not by role. Unlike default_vision_bean(),
        this never prefers role="default": a default Bean isn't
        capability-qualified just for being the default, and a caller
        asking for a real capability wants the cheapest Bean that actually
        has it. Returns None when no available Bean satisfies every
        requested filter - callers must handle that explicitly.

        prefer_alias (web search cost optimization Brew): an explicit,
        opt-in override for one named call site that wants a specific Bean
        as the effective default even when it isn't the cheapest candidate
        - e.g. use_web routing preferring "Kimi K2" (tuned for agentic
        tool use) over a cheaper but less agentic-tuned candidate. When
        given and that alias is among the qualifying candidates, it wins
        outright, no price comparison. When absent, unmatched, or not
        itself a qualifying candidate, falls through to plain
        cheapest-price selection - this is how a preferred Bean's own
        removal or a capability/availability change makes the next
        cheapest candidate a genuine fallback, not just a decorative
        second entry. Every caller before this Brew passes nothing and
        gets unchanged cheapest-price-only behavior."""

        candidates = [
            bean
            for bean in self._beans
            if bean.is_available
            and (not tool_calling or bean.tool_calling)
            and (not vision or bean.vision)
        ]
        if not candidates:
            return None
        if prefer_alias is not None:
            for bean in candidates:
                if bean.alias == prefer_alias:
                    return bean
        return min(
            candidates,
            key=lambda bean: (bean.price_per_1k_input_usd or 0.0) + (bean.price_per_1k_output_usd or 0.0),
        )


def assert_active_beans_priced(registry: BeanRegistry) -> None:
    """Startup guard (cost-inconsistency fix): raises BeanPricingError if
    any status="active" Bean has no price_per_1k_input_usd/
    price_per_1k_output_usd configured. An active, unpriced Bean is exactly
    what makes resolve_cost() (router/app/ledger.py) fall through to a
    genuinely-unknown cost_usd for every request routed to it - this
    catches that misconfiguration at startup instead of silently
    accumulating "unknown" Ledger rows. A Bean with status != "active"
    (e.g. "not_yet_selected") is exempt - it cannot be routed to, so its
    pricing being unset is not yet a real gap. Called only from
    create_app()'s real-startup branch (router/app/main.py), never when a
    test injects its own RouterState - test fixtures may deliberately use
    an unpriced placeholder premium Bean."""

    unpriced = [
        bean.alias
        for bean in registry.all_beans()
        if bean.status == "active"
        and (bean.price_per_1k_input_usd is None or bean.price_per_1k_output_usd is None)
    ]
    if unpriced:
        raise BeanPricingError(
            f"Active Bean(s) missing price_per_1k_input_usd/price_per_1k_output_usd in "
            f"config/beans.yaml: {', '.join(unpriced)}. Every active Bean must have real "
            f"pricing (0.0 for free-tier) so the Ledger can compute a real cost_usd."
        )

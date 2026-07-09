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

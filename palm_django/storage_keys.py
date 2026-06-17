"""
Parse Palm colon-separated storage keys into typed routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RouteKind = Literal["definition", "instance", "kv"]

_DEFINITION_KINDS = frozenset({"flow", "process", "resource", "state_schema"})


@dataclass(frozen=True)
class ParsedStorageKey:
    route: RouteKind
    key: str = ""
    definition_kind: str = ""
    entity_id: str = ""


def namespace_for_key(key: str) -> str:
    parts = [segment for segment in key.split(":") if segment]
    if len(parts) >= 2:
        return parts[1]
    return "other"


def parse_storage_key(key: str) -> ParsedStorageKey:
    parts = [segment for segment in key.split(":") if segment]
    if (
        len(parts) == 4
        and parts[0] == "palm"
        and parts[1] == "definitions"
        and parts[2] in _DEFINITION_KINDS
    ):
        return ParsedStorageKey(
            route="definition",
            key=key,
            definition_kind=parts[2],
            entity_id=parts[3],
        )
    if len(parts) == 3 and parts[0] == "palm" and parts[1] == "instances" and parts[2] != "index":
        return ParsedStorageKey(route="instance", key=key, entity_id=parts[2])
    return ParsedStorageKey(route="kv", key=key)
"""
pokemon_utils.py - Helper functions for loading and normalizing Pokémon data.
"""

from __future__ import annotations

import ast
import math
from typing import Any, Dict, Iterable, List, Optional


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_types(
    raw_types: Optional[Iterable[Any]], primary: Optional[Any], secondary: Optional[Any]
) -> List[str]:
    types: List[str] = []

    def add_type(candidate: Any) -> None:
        if isinstance(candidate, str):
            stripped = candidate.strip()
            if stripped and stripped not in types:
                types.append(stripped)

    if raw_types:
        for entry in raw_types:
            add_type(entry)

    add_type(primary)
    add_type(secondary)

    return types


def _normalize_abilities(raw: Any) -> List[str]:
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, (list, tuple)):
                entries = list(parsed)
            else:
                entries = [raw]
        except (ValueError, SyntaxError):
            entries = [raw]
    else:
        entries = []

    normalized: List[str] = []
    for entry in entries:
        text = str(entry).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def normalize_pokemon_record(raw: Dict[str, Any], fallback_name: str = "Unknown") -> Dict[str, Any]:
    """
    Convert the raw dictionary returned by load_pokemon.Pokedex into plain
    Python data structures that are safe to serialize.
    """
    return {
        "name": raw.get("name", fallback_name) or fallback_name,
        "type": _normalize_types(raw.get("type"), raw.get("type1"), raw.get("type2")),
        "hp": _to_int(raw.get("hp"), 50),
        "attack": _to_int(raw.get("attack"), 50),
        "defense": _to_int(raw.get("defense"), 50),
        "special_attack": _to_int(raw.get("special_attack"), 50),
        "special_defense": _to_int(raw.get("special_defense"), 50),
        "speed": _to_int(raw.get("speed"), 50),
        "abilities": _normalize_abilities(raw.get("abilities")),
    }



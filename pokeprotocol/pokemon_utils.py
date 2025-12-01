"""
pokemon_utils.py - Helper functions for loading and normalizing Pokémon data.
"""
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


def normalize_pokemon_record(raw_record: Dict[str, Any], name: str) -> Dict[str, Any]:
    """
    Takes a raw dictionary record from the CSV loading process and
    formats it into a standard battle-ready dictionary, ensuring all
    essential keys are present.
    """
    
    # Ensure essential type and stats keys are present with safe defaults
    normalized = {
        # Required keys for BattleSystem
        'name': raw_record.get('Name', name),
        'pokedex_number': raw_record.get('Pokedex_Number', 0),
        'type1': raw_record.get('Type_1', 'Normal'),  # <-- CRITICAL: Default to 'Normal'
        'type2': raw_record.get('Type_2', None),     # <-- CRITICAL: Default to None
        
        # Stats (use default if missing from raw data)
        'hp': int(raw_record.get('HP', 1)),
        'attack': int(raw_record.get('Attack', 1)),
        'defense': int(raw_record.get('Defense', 1)),
        'special_attack': int(raw_record.get('Sp_Atk', 1)),
        'special_defense': int(raw_record.get('Sp_Def', 1)),
        'speed': int(raw_record.get('Speed', 1)),
    }
    
    # Ensure Type 2 is None if it's an empty string or 'NaN' from CSV
    if normalized['type2'] in ('', 'nan', None):
        normalized['type2'] = None
        
    return normalized



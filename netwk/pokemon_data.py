"""
pokemon_data.py - Handles loading and accessing Pokémon data from CSV.
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Optional


class PokemonDatabase:
    """Database for Pokémon stats and information loaded from CSV."""

    def __init__(self, csv_path: str = "pokemon.csv"):
        self.pokemon_data: Dict[int, Dict[str, Any]] = {}
        self.csv_path = csv_path
        self.load_data()

    def load_data(self) -> None:
        """Load Pokémon data from CSV file."""
        csv_full_path = self.csv_path
        if not os.path.isabs(csv_full_path):
            csv_full_path = os.path.join(os.path.dirname(__file__), self.csv_path)

        if not os.path.exists(csv_full_path):
            print(f"Warning: Pokémon CSV file not found at {csv_full_path}")
            print("Using default Pokémon data...")
            self.create_default_data()
            return

        try:
            with open(csv_full_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        pokedex_num = int(row["pokedex_number"])
                    except (KeyError, ValueError):
                        continue

                    abilities = []
                    abilities_str = row.get("abilities", "")
                    if abilities_str and abilities_str != "nan":
                        abilities = [
                            ability.strip().strip("'\"")
                            for ability in abilities_str.strip("[]").split(",")
                            if ability.strip()
                        ]

                    against_stats: Dict[str, float] = {}
                    for key, value in row.items():
                        if key.startswith("against_"):
                            try:
                                against_stats[key] = float(value)
                            except (TypeError, ValueError):
                                against_stats[key] = 1.0

                    def number_or_default(field: str, default: int = 0) -> int:
                        try:
                            return int(float(row.get(field, default)))
                        except (TypeError, ValueError):
                            return default

                    def float_or_default(field: str, default: float = 0.0) -> float:
                        try:
                            return float(row.get(field, default))
                        except (TypeError, ValueError):
                            return default

                    self.pokemon_data[pokedex_num] = {
                        "name": row.get("name", "Unknown"),
                        "pokedex_number": pokedex_num,
                        "type1": (row.get("type1") or "").strip(),
                        "type2": (row.get("type2") or "").strip() or None,
                        "hp": number_or_default("hp", 50),
                        "attack": number_or_default("attack", 50),
                        "defense": number_or_default("defense", 50),
                        "special_attack": number_or_default("sp_attack", 50),
                        "special_defense": number_or_default("sp_defense", 50),
                        "speed": number_or_default("speed", 50),
                        "abilities": abilities,
                        "height_m": float_or_default("height_m", 0.0),
                        "weight_kg": float_or_default("weight_kg", 0.0),
                        "base_total": number_or_default("base_total", 0),
                        "capture_rate": number_or_default("capture_rate", 0),
                        "classification": row.get("classfication", "Unknown"),
                        "generation": number_or_default("generation", 1),
                        "is_legendary": bool(int(row.get("is_legendary", 0))),
                        "against_stats": against_stats,
                    }

            print(f"✓ Loaded {len(self.pokemon_data)} Pokémon from {csv_full_path}")

        except Exception as exc:  # pragma: no cover - fallback path
            print(f"Error loading Pokémon CSV: {exc}")
            print("Using default Pokémon data...")
            self.create_default_data()

    def create_default_data(self) -> None:
        """Create default Pokémon data if CSV is not available."""
        self.pokemon_data = {
            1: {
                "name": "Bulbasaur",
                "pokedex_number": 1,
                "type1": "grass",
                "type2": "poison",
                "hp": 45,
                "attack": 49,
                "defense": 49,
                "special_attack": 65,
                "special_defense": 65,
                "speed": 45,
                "abilities": ["Overgrow", "Chlorophyll"],
                "height_m": 0.7,
                "weight_kg": 6.9,
                "base_total": 318,
                "capture_rate": 45,
                "classification": "Seed Pokémon",
                "generation": 1,
                "is_legendary": False,
                "against_stats": self.get_default_type_effectiveness(["grass", "poison"]),
            },
            4: {
                "name": "Charmander",
                "pokedex_number": 4,
                "type1": "fire",
                "type2": None,
                "hp": 39,
                "attack": 52,
                "defense": 43,
                "special_attack": 60,
                "special_defense": 50,
                "speed": 65,
                "abilities": ["Blaze", "Solar Power"],
                "height_m": 0.6,
                "weight_kg": 8.5,
                "base_total": 309,
                "capture_rate": 45,
                "classification": "Lizard Pokémon",
                "generation": 1,
                "is_legendary": False,
                "against_stats": self.get_default_type_effectiveness(["fire"]),
            },
            7: {
                "name": "Squirtle",
                "pokedex_number": 7,
                "type1": "water",
                "type2": None,
                "hp": 44,
                "attack": 48,
                "defense": 65,
                "special_attack": 50,
                "special_defense": 64,
                "speed": 43,
                "abilities": ["Torrent", "Rain Dish"],
                "height_m": 0.5,
                "weight_kg": 9.0,
                "base_total": 314,
                "capture_rate": 45,
                "classification": "Tiny Turtle Pokémon",
                "generation": 1,
                "is_legendary": False,
                "against_stats": self.get_default_type_effectiveness(["water"]),
            },
        }
        print("✓ Loaded default Pokémon data")

    def get_default_type_effectiveness(self, types: List[str]) -> Dict[str, float]:
        """Get default type effectiveness multipliers."""
        effectiveness = {f"against_{t}": 1.0 for t in [
            "bug", "dark", "dragon", "electric", "fairy", "fight", "fire", "flying",
            "ghost", "grass", "ground", "ice", "normal", "poison", "psychic", "rock",
            "steel", "water"
        ]}

        type_multipliers = {
            "grass": {
                "against_fire": 2.0, "against_flying": 2.0, "against_ice": 2.0,
                "against_poison": 2.0, "against_bug": 2.0, "against_water": 0.5,
                "against_electric": 0.5, "against_grass": 0.5, "against_ground": 0.5,
            },
            "poison": {
                "against_ground": 2.0, "against_psychic": 2.0, "against_grass": 0.5,
                "against_fight": 0.5, "against_poison": 0.5, "against_bug": 0.5,
                "against_fairy": 0.5,
            },
            "fire": {
                "against_water": 2.0, "against_ground": 2.0, "against_rock": 2.0,
                "against_bug": 0.5, "against_steel": 0.5, "against_fire": 0.5,
                "against_grass": 0.5, "against_ice": 0.5, "against_fairy": 0.5,
            },
            "water": {
                "against_electric": 2.0, "against_grass": 2.0, "against_steel": 0.5,
                "against_fire": 0.5, "against_water": 0.5, "against_ice": 0.5,
            },
        }

        for pokemon_type in types:
            if pokemon_type in type_multipliers:
                for stat, multiplier in type_multipliers[pokemon_type].items():
                    effectiveness[stat] *= multiplier

        return effectiveness

    def get_pokemon_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get Pokémon data by name (case-insensitive)."""
        name = name.lower().strip()
        for pokemon in self.pokemon_data.values():
            if pokemon["name"].lower() == name:
                return pokemon.copy()
        return None

    def get_pokemon_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Get Pokémon data by Pokédex number."""
        if number in self.pokemon_data:
            return self.pokemon_data[number].copy()
        return None

    def search_pokemon(self, query: str) -> List[Dict[str, Any]]:
        """Search Pokémon by partial name or number."""
        results: List[Dict[str, Any]] = []
        query_lower = query.lower()
        is_digit = query.isdigit()
        for pokemon in self.pokemon_data.values():
            if query_lower in pokemon["name"].lower():
                results.append(pokemon.copy())
            elif is_digit and int(query) == pokemon["pokedex_number"]:
                results.append(pokemon.copy())
        return results

    def get_all_pokemon_names(self) -> List[str]:
        return [pokemon["name"] for pokemon in self.pokemon_data.values()]

    def get_pokemon_list(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        pokemon_list = sorted(
            self.pokemon_data.values(), key=lambda item: item["pokedex_number"]
        )
        if limit:
            return [pokemon.copy() for pokemon in pokemon_list[:limit]]
        return [pokemon.copy() for pokemon in pokemon_list]
    
    def get_type_effectiveness(self, attack_type, defense_type):
        if not defense_type:
            return 1.0
        attack_type = attack_type.lower()
        defense_type = defense_type.lower()

        try:
            return self.type_chart.get(attack_type, {}).get(defense_type, 1.0)
        except:
            return 1.0



# Global instance for convenient imports
pokemon_db = PokemonDatabase()



"""
battle_system.py — Fully fixed for PokeProtocol RFC + GUI integration
"""

import random
from typing import Dict, List
from pokemon_data import pokemon_db


class BattleSystem:

    def __init__(self, seed: int = None):
        # Deterministic RNG for synchronized multiplayer
        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)

        # Move database
        self.moves = {
            'Tackle': {'type': 'normal', 'category': 'physical', 'power': 40, 'accuracy': 100},
            'Ember': {'type': 'fire', 'category': 'special', 'power': 40, 'accuracy': 100},
            'Water Gun': {'type': 'water', 'category': 'special', 'power': 40, 'accuracy': 100},
            'Vine Whip': {'type': 'grass', 'category': 'physical', 'power': 45, 'accuracy': 100},
            'Thunderbolt': {'type': 'electric', 'category': 'special', 'power': 90, 'accuracy': 100},
            'Flamethrower': {'type': 'fire', 'category': 'special', 'power': 90, 'accuracy': 100},
            'Hydro Pump': {'type': 'water', 'category': 'special', 'power': 110, 'accuracy': 80},
            'Solar Beam': {'type': 'grass', 'category': 'special', 'power': 120, 'accuracy': 100},
            'Earthquake': {'type': 'ground', 'category': 'physical', 'power': 100, 'accuracy': 100},
            'Ice Beam': {'type': 'ice', 'category': 'special', 'power': 90, 'accuracy': 100},
            'Psychic': {'type': 'psychic', 'category': 'special', 'power': 90, 'accuracy': 100},
            'Shadow Ball': {'type': 'ghost', 'category': 'special', 'power': 80, 'accuracy': 100},
        }

    # ----------------------------------------------------------------------
    # MOVE RETRIEVAL
    # ----------------------------------------------------------------------
    def get_moves_for(self, pkm: Dict) -> List[str]:
        """Return 4 moves based on Pokémon typing (used by GUI)."""
        type1 = pkm.get("type1", "").lower()
        type2 = pkm.get("type2", "").lower()

        type_moves = {
            'grass': ['Vine Whip', 'Solar Beam', 'Tackle'],
            'fire': ['Ember', 'Flamethrower', 'Tackle'],
            'water': ['Water Gun', 'Hydro Pump', 'Tackle'],
            'electric': ['Thunderbolt', 'Tackle'],
            'psychic': ['Psychic', 'Tackle'],
            'ghost': ['Shadow Ball', 'Tackle'],
            'ice': ['Ice Beam', 'Tackle'],
            'ground': ['Earthquake', 'Tackle']
        }

        moves = []

        if type1 in type_moves:
            moves.extend(type_moves[type1])
        if type2 in type_moves:
            for m in type_moves[type2]:
                if m not in moves:
                    moves.append(m)

        if not moves:
            moves = ['Tackle']

        return moves[:4]

    # ----------------------------------------------------------------------
    # DAMAGE CALCULATION — MATCHES POKEPROTOCOL RFC EXACTLY
    # ----------------------------------------------------------------------
    def calculate_damage(self, attacker: Dict, defender: Dict, move_name: str) -> Dict:

        move = self.moves.get(move_name, self.moves['Tackle'])

        # accuracy roll
        if random.randint(1, 100) > move["accuracy"]:
            return {
                "damage": 0,
                "hit": False,
                "message": f"{attacker['name']} used {move_name} but missed!"
            }

        # determine stats used
        if move["category"] == "physical":
            atk_stat = attacker["attack"]
            def_stat = defender["defense"]
        else:
            atk_stat = attacker["special_attack"]
            def_stat = defender["special_defense"]

            # apply boosts
            atk_stat += 20 * attacker.get("special_attack_uses", 0)
            def_stat += 20 * defender.get("special_defense_uses", 0)

        # Calculate type effectiveness properly (move_type vs each defense type)
        move_type = move['type']

        type1 = defender.get("type1", "").lower()
        type2 = defender.get("type2", "").lower() if defender.get("type2") else ""

        # Modern fix: try new API first
        if hasattr(pokemon_db, "get_type_effectiveness"):
            eff1 = pokemon_db.get_type_effectiveness(move_type, type1)
            eff2 = pokemon_db.get_type_effectiveness(move_type, type2) if type2 else 1.0
        else:
            # fallback to simple 1-type logic
            eff1 = pokemon_db.get_default_type_effectiveness(type1)
            eff2 = pokemon_db.get_default_type_effectiveness(type2) if type2 else 1.0

        type_effectiveness = eff1 * eff2

        # STAB
        stab = 1.0
        if move_type.lower() in (
            attacker.get("type1", "").lower(),
            attacker.get("type2", "").lower()
        ):
            stab = 1.5

        # random factor
        rand_factor = random.uniform(0.85, 1.0)

        # RFC formula
        base_damage = (move["power"] * atk_stat * type_effectiveness * stab) / max(1, def_stat)
        damage = max(1, int(base_damage * rand_factor))

        # effectiveness message
        if type_effectiveness == 0:
            eff_msg = " It had no effect!"
        elif type_effectiveness > 1.0:
            eff_msg = " It's super effective!"
        elif type_effectiveness < 1.0:
            eff_msg = " It's not very effective..."
        else:
            eff_msg = ""

        msg = f"{attacker['name']} used {move_name}!{eff_msg}"

        return {
            "damage": damage,
            "hit": True,
            "message": msg,
            "type_effectiveness": type_effectiveness,
            "stab": stab,
            "move_type": move_type,
        }

    # ----------------------------------------------------------------------
    def create_battle_pokemon(self, raw_stats: Dict, boosts: Dict) -> Dict:

        type1 = raw_stats.get("type1") or ""
        type2 = raw_stats.get("type2") or ""

        return {
            "name": raw_stats.get("name", ""),
            "max_hp": int(raw_stats.get("hp", 1)),
            "current_hp": int(raw_stats.get("hp", 1)),

            "attack": int(raw_stats.get("attack", 0)),
            "defense": int(raw_stats.get("defense", 0)),
            "special_attack": int(raw_stats.get("special_attack", raw_stats.get("sp_atk", 0))),
            "special_defense": int(raw_stats.get("special_defense", raw_stats.get("sp_def", 0))),

            "type1": type1,
            "type2": type2,

            "special_attack_uses": boosts.get("special_attack_uses", 0),
            "special_defense_uses": boosts.get("special_defense_uses", 0),
        }

    # ----------------------------------------------------------------------
    def apply_damage(self, pokemon: Dict, dmg: int) -> Dict:
        pokemon["current_hp"] = max(0, pokemon["current_hp"] - dmg)
        pokemon["fainted"] = pokemon["current_hp"] == 0
        return pokemon

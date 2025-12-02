import ast
import random
<<<<<<< HEAD:pokeprotocol/battle_system
from typing import Dict, Any, Optional

DEFAULT_LEVEL = 50
DEFAULT_BASE_POWER = 50  # if move doesn't specify a power
CRITICAL_CHANCE = 1 / 16  # standard-ish
RANDOM_MIN = 0.85
RANDOM_MAX = 1.0


class BattleSystem:
    def __init__(self, seed: Optional[int] = None):
        """
        seed: shared handshake integer — must be identical on both peers for deterministic results.
        """
        if seed is None:
            seed = random.randint(1, 2**31 - 1)
        self.seed = int(seed)
        # Use a Random instance so we don't pollute global random
        self.rng = random.Random(self.seed)

    # -------------------------
    # Utilities / converters
    # -------------------------
    @staticmethod
    def normalize_csv_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert CSV row values to expected python types and names used by the battle system.
        Expects row to contain keys like 'name','hp','attack','defense','sp_attack','sp_defense','type1','type2',
        and columns named 'against_fire','against_water', etc.

        Returns a dictionary with:
        - name, hp, attack, defense, sp_attack, sp_defense, speed, type1, type2
        - against: dict mapping type -> multiplier
        - abilities: list
        """
        out = {}
        out["name"] = row.get("name", "")
        # numeric fields may be strings — convert safely
        def to_int(k, default=0):
            v = row.get(k)
            try:
                return int(float(v))
            except Exception:
                return default

        out["hp"] = to_int("hp", 1)
        out["attack"] = to_int("attack", 1)
        out["defense"] = to_int("defense", 1)
        # CSV column name might be 'sp_attack' or 'sp_attack' — adapt
        out["sp_attack"] = to_int("sp_attack", to_int("sp atk", 1))
        out["sp_defense"] = to_int("sp_defense", to_int("sp def", 1))
        out["speed"] = to_int("speed", 1)
        out["type1"] = (row.get("type1") or "").lower()
        out["type2"] = (row.get("type2") or "").lower()

        # abilities often stored as "['Overgrow','Chlorophyll']" string in CSV
        raw_abilities = row.get("abilities", "")
        abilities = []
        if isinstance(raw_abilities, str) and raw_abilities.strip().startswith("["):
            try:
                abilities = ast.literal_eval(raw_abilities)
            except Exception:
                abilities = [raw_abilities]
        elif isinstance(raw_abilities, (list, tuple)):
            abilities = list(raw_abilities)
        elif raw_abilities:
            abilities = [raw_abilities]
        out["abilities"] = abilities

        # Collect all against_ columns present in row
        against = {}
        for k, v in row.items():
            if isinstance(k, str) and k.startswith("against_"):
                t = k[len("against_"):].lower()
                try:
                    against[t] = float(v)
                except Exception:
                    # fallback to 1.0
                    try:
                        against[t] = float(v.strip()) if isinstance(v, str) else 1.0
                    except Exception:
                        against[t] = 1.0
        out["against"] = against

        # current_hp and max_hp fields for battle runtime
        out["current_hp"] = out["hp"]
        out["max_hp"] = out["hp"]
        out["fainted"] = False

        return out

    # -------------------------
    # Damage calculation
    # -------------------------
    def calculate_damage(self,
                         attacker: Dict[str, Any],
                         defender: Dict[str, Any],
                         move: Dict[str, Any],
                         use_sp_attack_boost: bool = False,
                         use_sp_defense_boost: bool = False,
                         level: int = DEFAULT_LEVEL) -> Dict[str, Any]:
        """
        Calculate damage deterministically based on the provided move and stats.

        Parameters:
        - attacker, defender: normalized pokemon dicts (use normalize_csv_row before)
        - move: dict with keys: name (optional), type (required), category ('physical'|'special', optional),
                power (optional)
                Example: {'name': 'Thunderbolt', 'type': 'electric', 'category': 'special', 'power': 90}
        - use_sp_attack_boost / use_sp_defense_boost: booleans indicating use of the limited boosts

        Returns a result dict with:
        {
          'damage': int,
          'base_damage': float,
          'move_type': str,
          'category': 'physical'|'special',
          'stab': float,
          'effectiveness': float,
          'critical': bool,
          'random_factor': float,
          'attacker_stat_used': int,
          'defender_stat_used': int,
          'message': str
        }
        """

        # Validate move fields
        move_type = (move.get("type") or "").lower()
        if not move_type:
            raise ValueError("move must include a 'type' key (e.g., 'fire')")

        category = (move.get("category") or "physical").lower()
        base_power = float(move.get("power", DEFAULT_BASE_POWER))

        # Select attacker and defender stats based on category
        if category == "special":
            A_stat = int(attacker.get("sp_attack", attacker.get("sp_attack", 1)))
            D_stat = int(defender.get("sp_defense", defender.get("sp_defense", 1)))
        else:
            A_stat = int(attacker.get("attack", attacker.get("attack", 1)))
            D_stat = int(defender.get("defense", defender.get("defense", 1)))

        # Apply boosts if requested
        if use_sp_attack_boost:
            # RFC: boosts are limited resources — this function assumes caller ensures availability
            A_stat = int(A_stat * 1.5)
        if use_sp_defense_boost:
            D_stat = int(D_stat * 1.5)

        # STAB (Same Type Attack Bonus)
=======
from typing import Dict, List, Tuple
# Assuming pokemon_db is imported or defined in pokemon_data.py
# If pokemon_db is defined in pokemon_data.py, you need an import like:
# from pokemon_data import pokemon_db
from pokemon_data import pokemon_db # Assuming this import is correct


class BattleSystem:
    """Handles Pokémon battle calculations"""
    
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)
        self.seed = seed or random.randint(1, 1000000)
        random.seed(self.seed)
        
        # Move database (simplified - you should 
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
    
    def calculate_damage(self, attacker: Dict, defender: Dict, move_name: str, 
                   
                        special_attack_boost: bool = False, 
                        special_defense_boost: bool = False) -> Dict:
        """
        Calculate damage according to PokeProtocol formula:
        Damage = (BasePower × AttackerStat × TypeEffectiveness) / DefenderStat
        """
        if move_name not in self.moves:
     
            # Default move if not found
            move = {'type': 'normal', 'category': 'physical', 'power': 40, 'accuracy': 100}
        else:
            move = self.moves[move_name]
        
        # Check accuracy
        if random.randint(1, 100) > move['accuracy']:
            return {
  
                'damage': 0,
                'hit': False,
                'message': f"{attacker['name']} used {move_name}... but it missed!"
            }
        
        # Get attacker and defender stats based on move category
        if move['category'] == 'physical':
            attacker_stat = attacker['attack']
            defender_stat = defender['defense']
        else:  # special move
            attacker_stat = attacker['special_attack']
          
            defender_stat = defender['special_defense']
            
            # Apply boosts if used
            if special_attack_boost:
                attacker_stat = int(attacker_stat * 1.5)
            if special_defense_boost:
                defender_stat = int(defender_stat * 1.5)
  
       
        # Calculate type effectiveness (Type1Effectiveness * Type2Effectiveness)
        
        # 1. Get effectiveness against Type 1
        type1_effectiveness = pokemon_db.get_type_effectiveness(
            move['type'], 
            [defender['type1']] # Pass only Type 1
        )
        
        type2_effectiveness = 1.0
        if defender.get('type2'):
            # 2. Get effectiveness against Type 2 (if it exists)
            type2_effectiveness = pokemon_db.get_type_effectiveness(
                move['type'], 
                [defender['type2']] # Pass only Type 2
            )
        
        # 3. Multiply them to get the final multiplier (as per RFC)
        type_effectiveness = type1_effectiveness * type2_effectiveness
 
        
        # Apply STAB (Same Type Attack Bonus) - 1.5x if move type matches attacker's type
>>>>>>> bb72a50e486076069be496322099e8d8c3ca8bd8:pokeprotocol/battle_system.py
        stab = 1.0
        atk_t1 = (attacker.get("type1") or "").lower()
        atk_t2 = (attacker.get("type2") or "").lower()
        if move_type and (move_type == atk_t1 or move_type == atk_t2):
            stab = 1.5
<<<<<<< HEAD:pokeprotocol/battle_system

        # Type effectiveness: use defender['against'] lookup
        effectiveness = 1.0
        against_map = defender.get("against", {})
        if isinstance(against_map, dict):
            effectiveness = float(against_map.get(move_type, 1.0))
        else:
            effectiveness = 1.0

        # Critical check (deterministic with self.rng)
        crit_roll = self.rng.random()
        critical = crit_roll < CRITICAL_CHANCE
        crit_multiplier = 1.5 if critical else 1.0

        # Random factor (deterministic RNG)
        rand_factor = self.rng.uniform(RANDOM_MIN, RANDOM_MAX)

        # Use classic-ish base damage formula:
        # base = (((2 * level) / 5 + 2) * BasePower * (A_stat / max(1, D_stat)) ) / 50 + 2
        # final = base * STAB * effectiveness * crit * rand_factor
        D_stat_nonzero = max(1, D_stat)

        # compute step by step (avoid hidden float issues)
        step1 = (2 * float(level)) / 5.0 + 2.0  # deterministic
        step2 = step1 * base_power * (float(A_stat) / float(D_stat_nonzero))
        step3 = step2 / 50.0
        base_damage = step3 + 2.0

        final_multiplier = stab * effectiveness * crit_multiplier * rand_factor
        raw_damage = base_damage * final_multiplier

        # Ensure minimum damage of 1 when hit
        damage = int(max(1, int(raw_damage)))

        # Build human readable message (same on both peers)
        effect_msg = ""
        if effectiveness == 0:
            effect_msg = " It had no effect!"
        elif effectiveness > 1.0:
            effect_msg = " It was super effective!"
        elif 0 < effectiveness < 1.0:
            effect_msg = " It was not very effective..."

        crit_msg = " A critical hit!" if critical else ""
        message = f"{attacker.get('name')} used a {move_type}-type move!{effect_msg}{crit_msg}"

        return {
            "damage": damage,
            "raw_damage": raw_damage,
            "base_damage": base_damage,
            "move_type": move_type,
            "category": category,
            "stab": stab,
            "effectiveness": effectiveness,
            "critical": critical,
            "random_factor": rand_factor,
            "attacker_stat_used": A_stat,
            "defender_stat_used": D_stat_nonzero,
            "message": message
        }

    # -------------------------
    # Apply damage helper
    # -------------------------
    @staticmethod
    def apply_damage(target: Dict[str, Any], amount: int) -> Dict[str, Any]:
        """
        Subtract amount from target['current_hp'] and set fainted flag.
        Returns the updated target dict.
        """
        cur = int(target.get("current_hp", target.get("hp", 1)))
        cur = max(0, cur - int(amount))
        target["current_hp"] = cur
        target["fainted"] = (cur == 0)
        return target

    # -------------------------
    # Build CALCULATION_REPORT payload
    # -------------------------
    @staticmethod
    def build_calculation_report(attacker: Dict[str, Any], defender: Dict[str, Any], calc_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a dict containing values you can serialize and send as CALCULATION_REPORT.
        Example fields:
            attacker, move_used (type), remaining_health (attacker), damage_dealt, defender_hp_remaining, status_message
        """
=======
        
        # Random factor (0.85 to 1.0)
        random_factor = random.uniform(0.85, 1.0)
        
        # Calculate damage using the formula from RFC
        if defender_stat == 0:
            defender_stat = 1  # Prevent division by zero
        
        # Damage = (BasePower * AttackerStat * TypeEffectiveness * STAB) / DefenderStat * Random
        base_damage = (move['power'] * attacker_stat * type_effectiveness * stab) / defender_stat
      
        damage = int(base_damage * random_factor)
        
        # Minimum damage is 1 if hit
        damage = max(1, damage)
        
        # Generate message
        effectiveness_text = ""
        if type_effectiveness > 1.0:
            effectiveness_text = " It was super effective!"
        elif type_effectiveness < 1.0 and type_effectiveness > 0:
            effectiveness_text = " It was not very effective..."
        elif type_effectiveness == 0:
            effectiveness_text = " It had no effect!"
        message = f"{attacker['name']} used {move_name}!{effectiveness_text}"
        
        return {
            'damage': damage,
            'hit': True,
            'message': message,
            'type_effectiveness': type_effectiveness,
            'stab_applied': stab > 1.0,
            
            'move_type': move['type'],
            'move_category': move['category'],
            'attacker_stat_used': attacker_stat,
            'defender_stat_used': defender_stat
        }
    
    def get_available_moves(self, pokemon_name: str) -> List[str]:
        """Get moves that a Pokémon can learn (simplified)"""
        pokemon = pokemon_db.get_pokemon_by_name(pokemon_name)
        if not pokemon:
    
            return list(self.moves.keys())[:4]  # Default moves
        
        # Simplified move assignment based on type
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
        
        # Add moves for type1
        if pokemon['type1'].lower() in type_moves:
            moves.extend(type_moves[pokemon['type1'].lower()])
        
        # Add moves for type2 if exists
        if pokemon.get('type2') and pokemon['type2'].lower() in type_moves:
            for move in type_moves[pokemon['type2'].lower()]:
                if move not in moves:
   
                    moves.append(move)
        
        # Add some default moves if not enough
        if len(moves) < 2:
            moves.append('Tackle')
        
        return moves[:4]  # Limit to 4 moves
    
    def create_battle_pokemon(self, pokemon_data: Dict, stat_boosts: Dict) -> Dict:
        """Create a battle-ready Pokémon with stat boosts"""
        battle_pokemon = pokemon_data.copy()
        battle_pokemon['current_hp'] = pokemon_data['hp']
        battle_pokemon['max_hp'] = pokemon_data['hp']
        battle_pokemon['stat_boosts'] = stat_boosts.copy()
        battle_pokemon['status'] = None  # Can be 'poisoned', 'paralyzed', etc.
        battle_pokemon['available_moves'] = self.get_available_moves(pokemon_data['name'])
        return battle_pokemon
    
    def apply_damage(self, pokemon: Dict, damage: int) -> Dict:
        """Apply damage to a Pokémon and return updated state"""
        pokemon['current_hp'] = max(0, pokemon['current_hp'] - damage)
        pokemon['fainted'] = pokemon['current_hp'] == 0
        return pokemon
    
    def get_battle_summary(self, attacker: Dict, defender: Dict, 
                          damage_result: Dict) -> Dict:
 
        """Create a battle summary for CALCULATION_REPORT"""
>>>>>>> bb72a50e486076069be496322099e8d8c3ca8bd8:pokeprotocol/battle_system.py
        return {
            "message_type": "CALCULATION_REPORT",
            "attacker": attacker.get("name"),
            "move_used": calc_result.get("move_type"),
            "remaining_health": str(attacker.get("current_hp", attacker.get("hp", 0))),
            "damage_dealt": str(calc_result.get("damage")),
            "defender_hp_remaining": str(defender.get("current_hp", defender.get("hp", 0))),
            "status_message": calc_result.get("message")
        }


# Convenience factory
def create_battle_system_from_seed(seed: int) -> BattleSystem:
    return BattleSystem(seed)


# -------------------------
# Quick local test (not executed on import)
# -------------------------
if __name__ == "__main__":
    # Very small self-test: two local battle systems with same seed produce identical damage
    seed = 123456
    bs1 = create_battle_system_from_seed(seed)
    bs2 = create_battle_system_from_seed(seed)

    # Fake normalized pokemon rows (as produced by normalize_csv_row)
    bulba = {
        "name": "Bulbasaur",
        "hp": 45, "current_hp": 45,
        "attack": 49, "defense": 49,
        "sp_attack": 65, "sp_defense": 65,
        "type1": "grass", "type2": "poison",
        "against": {"fire": 0.5, "water": 2.0, "grass": 0.5}
    }
    char = {
        "name": "Charmander",
        "hp": 39, "current_hp": 39,
        "attack": 52, "defense": 43,
        "sp_attack": 60, "sp_defense": 50,
        "type1": "fire", "type2": "",
        "against": {"water": 0.5, "grass": 2.0, "fire": 0.5}
    }

    move = {"type": "fire", "category": "special", "power": 40}

    r1 = bs1.calculate_damage(attacker=char, defender=bulba, move=move)
    r2 = bs2.calculate_damage(attacker=char, defender=bulba, move=move)

    print("result1:", r1)
    print("result2:", r2)
    assert r1["damage"] == r2["damage"], "Damage mismatch — RNG not deterministic!"
    print("Self-test OK — identical damage with same seed")
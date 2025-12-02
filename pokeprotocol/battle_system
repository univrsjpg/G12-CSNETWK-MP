import ast
import random
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
        stab = 1.0
        atk_t1 = (attacker.get("type1") or "").lower()
        atk_t2 = (attacker.get("type2") or "").lower()
        if move_type and (move_type == atk_t1 or move_type == atk_t2):
            stab = 1.5

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
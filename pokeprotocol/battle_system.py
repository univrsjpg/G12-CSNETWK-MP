"""
battle_system.py - Handles Pokémon battle mechanics
"""

import random
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
        stab = 1.0
        if (move['type'].lower() == attacker['type1'].lower() or 
            (attacker['type2'] and move['type'].lower() == attacker['type2'].lower())):
            stab = 1.5
        
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
        return {
            'attacker': attacker['name'],
            'defender': defender['name'],
            'move_used': damage_result.get('move_type', 'Unknown'),
            'damage_dealt': damage_result['damage'],
            'attacker_hp_remaining': attacker['current_hp'],
            'defender_hp_remaining': defender['current_hp'],
            'status_message': damage_result['message'],
            'type_effectiveness': damage_result.get('type_effectiveness', 1.0),
            'move_category': damage_result.get('move_category', 'physical')
        }


# Global instance for easy access
battle_system = BattleSystem()
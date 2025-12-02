import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional, Any, Tuple

# --- Type Effectiveness Data (Expanded Type Chart) ---
# This dictionary defines what the ATTACKING type is effective against (DEFENDING type).
TYPE_MULTIPLIERS = {
    "normal": {
        "against_rock": 0.5, "against_steel": 0.5, "against_ghost": 0.0,
    },
    "fire": {
        "against_grass": 2.0, "against_ice": 2.0, "against_bug": 2.0, "against_steel": 2.0,
        "against_fire": 0.5, "against_water": 0.5, "against_rock": 0.5, "against_dragon": 0.5,
    },
    "water": {
        "against_fire": 2.0, "against_ground": 2.0, "against_rock": 2.0,
        "against_water": 0.5, "against_grass": 0.5, "against_dragon": 0.5,
    },
    "electric": {
        "against_water": 2.0, "against_flying": 2.0,
        "against_electric": 0.5, "against_grass": 0.5, "against_dragon": 0.5,
        "against_ground": 0.0,
    },
    "grass": {
        "against_water": 2.0, "against_ground": 2.0, "against_rock": 2.0,
        "against_fire": 0.5, "against_grass": 0.5, "against_poison": 0.5, 
        "against_flying": 0.5, "against_bug": 0.5, "against_dragon": 0.5, "against_steel": 0.5,
    },
    "ice": {
        "against_grass": 2.0, "against_ground": 2.0, "against_flying": 2.0, "against_dragon": 2.0,
        "against_fire": 0.5, "against_water": 0.5, "against_ice": 0.5, "against_steel": 0.5,
    },
    "fighting": {
        "against_normal": 2.0, "against_rock": 2.0, "against_steel": 2.0, "against_ice": 2.0, "against_dark": 2.0,
        "against_flying": 0.5, "against_poison": 0.5, "against_bug": 0.5, "against_psychic": 0.5, "against_fairy": 0.5,
        "against_ghost": 0.0,
    },
    "poison": {
        "against_grass": 2.0, "against_fairy": 2.0,
        "against_poison": 0.5, "against_ground": 0.5, "against_rock": 0.5, "against_ghost": 0.5,
        "against_steel": 0.0,
    },
    "ground": {
        "against_poison": 2.0, "against_rock": 2.0, "against_steel": 2.0, "against_fire": 2.0, "against_electric": 2.0,
        "against_grass": 0.5, "against_bug": 0.5,
        "against_flying": 0.0,
    },
    "flying": {
        "against_fighting": 2.0, "against_bug": 2.0, "against_grass": 2.0,
        "against_rock": 0.5, "against_steel": 0.5, "against_electric": 0.5,
    },
    "psychic": {
        "against_fighting": 2.0, "against_poison": 2.0,
        "against_steel": 0.5, "against_psychic": 0.5,
        "against_dark": 0.0,
    },
    "bug": {
        "against_grass": 2.0, "against_psychic": 2.0, "against_dark": 2.0,
        "against_fighting": 0.5, "against_flying": 0.5, "against_poison": 0.5, 
        "against_ghost": 0.5, "against_steel": 0.5, "against_fire": 0.5, "against_fairy": 0.5,
    },
    "rock": {
        "against_flying": 2.0, "against_bug": 2.0, "against_fire": 2.0, "against_ice": 2.0,
        "against_fighting": 0.5, "against_ground": 0.5, "against_steel": 0.5,
    },
    "ghost": {
        "against_ghost": 2.0, "against_psychic": 2.0,
        "against_dark": 0.5,
        "against_normal": 0.0, "against_fighting": 0.0,
    },
    "dragon": {
        "against_dragon": 2.0,
        "against_steel": 0.5,
        "against_fairy": 0.0,
    },
    "steel": {
        "against_rock": 2.0, "against_ice": 2.0, "against_fairy": 2.0,
        "against_steel": 0.5, "against_fire": 0.5, "against_water": 0.5, "against_electric": 0.5,
    },
    "dark": {
        "against_ghost": 2.0, "against_psychic": 2.0,
        "against_fighting": 0.5, "against_dark": 0.5, "against_fairy": 0.5,
    },
    "fairy": {
        "against_fighting": 2.0, "against_dragon": 2.0, "against_dark": 2.0,
        "against_poison": 0.5, "against_steel": 0.5, "against_fire": 0.5,
    }
}


class Pokedex:
    """Manages loading and retrieval of Pokémon data using Pandas."""
    
    # Map CSV column names to the expected Python/Protocol names
    COL_MAPPING = {
        'type1': 'type1',
        'type2': 'type2',
        'hp': 'hp',
        'attack': 'attack',
        'defense': 'defense',
        'sp_attack': 'special_attack',
        'sp_defense': 'special_defense',
        'speed': 'speed',
        'abilities': 'abilities',
        'pokedex_number': 'pokedex_number',
        # Include all 'against_' columns for safety, even if unused directly by battle_system.py
        'against_bug': 'against_bug', 'against_dark': 'against_dark',
        'against_dragon': 'against_dragon', 'against_electric': 'against_electric',
        'against_fairy': 'against_fairy', 'against_fight': 'against_fighting', # Fix mapping from fight to fighting
        'against_fire': 'against_fire', 'against_flying': 'against_flying', 
        'against_ghost': 'against_ghost', 'against_grass': 'against_grass', 
        'against_ground': 'against_ground', 'against_ice': 'against_ice', 
        'against_normal': 'against_normal', 'against_poison': 'against_poison', 
        'against_psychic': 'against_psychic', 'against_rock': 'against_rock', 
        'against_steel': 'against_steel', 'against_water': 'against_water'
    }

    def __init__(self):
        try:
            # Use 'Name' or 'name' as index based on the CSV structure
            self.pokedex = pd.read_csv('pokemon.csv')
            
            # Standardize index for easy lookup (lowercase names)
            self.pokedex['name_lower'] = self.pokedex['name'].str.lower()
            self.pokedex = self.pokedex.set_index('name_lower', drop=False)
            
            # Map column names for internal use (e.g., 'sp_attack' -> 'special_attack')
            self.pokedex = self.pokedex.rename(columns=self.COL_MAPPING)

        except FileNotFoundError:
            print("Error: 'pokemon.csv' not found. Cannot load Pokedex.")
            self.pokedex = pd.DataFrame()
        except Exception as e:
            print(f"Error loading Pokedex with Pandas: {e}")
            self.pokedex = pd.DataFrame()
            
    def _extract_pokemon_data(self, row: pd.Series) -> Dict[str, Any]:
        """Extracts and cleans essential data from a single Pandas Series (row)."""
        if row.empty:
            return {}

        # Safely convert to dictionary, handling missing values (NaN becomes None)
        data = row.replace({np.nan: None}).to_dict()
        
        # Ensure critical keys exist and are standardized for battle system
        pokemon_dict = {
            'name': data.get('name', 'Unknown'),
            'pokedex_number': int(data.get('pokedex_number', 0)),
            # Use Type_1/Type_2 if the CSV headers weren't mapped correctly, but rely on mapping
            'type1': data.get('type1', 'Normal'), 
            'type2': data.get('type2', None),
            
            # Core Stats - ensure they are integers for calculation
            'hp': int(data.get('hp', 50)),
            'attack': int(data.get('attack', 50)),
            'defense': int(data.get('defense', 50)),
            'special_attack': int(data.get('special_attack', 50)),
            'special_defense': int(data.get('special_defense', 50)),
            'speed': int(data.get('speed', 50)),
            'abilities': data.get('abilities', '[]')
            # The 'against_' keys are kept implicitly in 'data' but are not essential for core battle logic (type chart handles it)
        }
        
        # Clean up type2 if it's an empty string or 'None'
        if pokemon_dict['type2'] in ('', 'None', None):
            pokemon_dict['type2'] = None
        
        return pokemon_dict

    def get_pokemon_by_name(self, name: str) -> Optional[Dict]:
        """Retrieve Pokémon data by name."""
        if self.pokedex.empty:
            return None
            
        try:
            # Look up by the standardized lowercase index
            row = self.pokedex.loc[name.lower()]
            
            # If it returns a DataFrame (multiple matches), take the first one
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
                
            return self._extract_pokemon_data(row)
        except KeyError:
            return None

    def get_pokemon_by_number(self, number: int) -> Optional[Dict]:
        """Retrieve Pokémon data by Pokedex number."""
        if self.pokedex.empty:
            return None
        
        try:
            # Filter the DataFrame based on the 'pokedex_number' column
            match = self.pokedex[self.pokedex['pokedex_number'] == number]
            
            if not match.empty:
                return self._extract_pokemon_data(match.iloc[0])
        except Exception:
            pass # Ignore if the 'pokedex_number' column is missing/corrupted
            
        return None

    def get_pokemon_list(self, limit: int = 6) -> List[Dict]:
        """Returns a list of normalized Pokémon records for display."""
        if self.pokedex.empty:
            return []
            
        # Get the first 'limit' rows and extract data
        return [self._extract_pokemon_data(row) for _, row in self.pokedex.head(limit).iterrows()]

    # --- Type Effectiveness Calculation ---

    def get_type_effectiveness(self, attacking_type: str, defending_types: List[str]) -> float:
        """
        Calculates the damage multiplier for an attacking type against 
        a single or dual-type defender.
        """
        final_multiplier = 1.0
        attacking_type = attacking_type.lower()
        
        if attacking_type not in TYPE_MULTIPLIERS:
            return 1.0
            
        attack_multipliers = TYPE_MULTIPLIERS[attacking_type]
        
        for defender_type in defending_types:
            if not defender_type:
                continue
                
            defender_type = defender_type.lower()
            
            # The key in our lookup dictionary is formatted "against_type"
            lookup_key = f"against_{defender_type}"
            
            # Get the specific multiplier for this interaction, default to 1.0 if not found
            multiplier = attack_multipliers.get(lookup_key, 1.0)
            
            # Multiply the cumulative effectiveness
            final_multiplier *= multiplier
            
        return final_multiplier


# Global instance for easy access in other modules (e.g., battle_system.py)
pokemon_db = Pokedex()
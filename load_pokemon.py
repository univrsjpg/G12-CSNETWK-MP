import pandas as pd
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, 'pokemon.csv')


class Pokemon:

    def __init__(self, name: str, abilities, type_list, hp, attack, defense, sp_attack, sp_defense, speed,
                 against_bug, against_dark, against_dragon, against_electric, against_fairy, against_fight,
                 against_fire, against_flying, against_ghost, against_grass, against_ground, against_ice,
                 against_normal, against_poison, against_psychic, against_rock, against_steel, against_water):

        self.name = name
        self.abilities = abilities
        self.type = type_list
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.special_attack = sp_attack
        self.special_defense = sp_defense
        self.speed = speed
        self.against_bug = against_bug
        self.against_dark = against_dark
        self.against_dragon = against_dragon
        self.against_electric = against_electric
        self.against_fairy = against_fairy
        self.against_fight = against_fight
        self.against_fire = against_fire
        self.against_flying = against_flying
        self.against_ghost = against_ghost
        self.against_grass = against_grass
        self.against_ground = against_ground
        self.against_ice = against_ice
        self.against_normal = against_normal
        self.against_poison = against_poison
        self.against_psychic = against_psychic
        self.against_rock = against_rock
        self.against_steel = against_steel
        self.against_water = against_water

    def to_dict(self):
        return {
            'name': self.name,
            'abilities': self.abilities,
            'type': self.type,
            'hp': self.hp,
            'attack': self.attack,
            'defense': self.defense,
            'special_attack': self.special_attack,
            'special_defense': self.special_defense,
            'speed': self.speed,
            'against_bug': self.against_bug,
            'against_dark': self.against_dark,
            'against_dragon': self.against_dragon,
            'against_electric': self.against_electric,
            'against_fairy': self.against_fairy,
            'against_fight': self.against_fight,
            'against_fire': self.against_fire,
            'against_flying': self.against_flying,
            'against_ghost': self.against_ghost,
            'against_grass': self.against_grass,
            'against_ground': self.against_ground,
            'against_ice': self.against_ice,
            'against_normal': self.against_normal,
            'against_poison': self.against_poison,
            'against_psychic': self.against_psychic,
            'against_rock': self.against_rock,
            'against_steel': self.against_steel,
            'against_water': self.against_water
        }

class Pokedex:
    def __init__(self):
        self.pokedex = pd.read_csv(CSV_PATH)
        self.pokedex = self.pokedex.set_index('name')

    def get_pokemon(self, name: str) -> dict:
        if name not in self.pokedex.index:
            raise ValueError(f"Pokemon '{name}' not found in Pokedex.")

        data = self.pokedex.loc[name]

        pokemon_dict = {
            'name': name,
            'abilities': data['abilities'],
            'type': [data['type1'], data['type2']],
            'hp': int(data['hp']),
            'attack': int(data['attack']),
            'defense': int(data['defense']),
            'special_attack': int(data['sp_attack']),
            'special_defense': int(data['sp_defense']),
            'speed': int(data['speed']),
            'against_bug': float(data['against_bug']),
            'against_dark': float(data['against_dark']),
            'against_dragon': float(data['against_dragon']),
            'against_electric': float(data['against_electric']),
            'against_fairy': float(data['against_fairy']),
            'against_fight': float(data['against_fight']),
            'against_fire': float(data['against_fire']),
            'against_flying': float(data['against_flying']),
            'against_ghost': float(data['against_ghost']),
            'against_grass': float(data['against_grass']),
            'against_ground': float(data['against_ground']),
            'against_ice': float(data['against_ice']),
            'against_normal': float(data['against_normal']),
            'against_poison': float(data['against_poison']),
            'against_psychic': float(data['against_psychic']),
            'against_rock': float(data['against_rock']),
            'against_steel': float(data['against_steel']),
            'against_water': float(data['against_water'])
        }
        return pokemon_dict
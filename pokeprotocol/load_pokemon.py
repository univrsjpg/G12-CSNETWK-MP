import pandas as pd

class Pokemon:
    def __init__(self, name: str):
        self.name = name
        self.abilities = abilities
        self.type = type
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.special_attack = special_attack
        self.special_defense = special_defense
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
        return Pokemon(self.name, self.abilities, self.type, self.hp, self.attack, self.defense, self.special_attack, self.special_defense, self.speed, 
        self.against_bug, self.against_dark, self.against_dragon, self.against_electric, self.against_fairy, self.against_fight, self.against_fire, 
        self.against_flying, self.against_ghost, self.against_grass, self.against_ground, self.against_ice, self.against_normal, self.against_poison, 
        self.against_psychic, self.against_rock, self.against_steel, self.against_water)



class Pokedex:
    def __init__(self):
        self.pokedex = pd.read_csv('pokemon.csv')
        self.pokedex = self.pokedex.set_index('name')
        

    def get_pokemon(self, name: str):
        pokemon = {
            'name': self.pokedex.loc[name].name,
            'abilities': self.pokedex.loc[name]['abilities'],
            'type': [self.pokedex.loc[name]['type1'], self.pokedex.loc[name]['type2']],
            'hp': self.pokedex.loc[name]['hp'], 
            'attack': self.pokedex.loc[name]['attack'],
            'defense': self.pokedex.loc[name]['defense'],
            'special_attack': self.pokedex.loc[name]['sp_attack'],
            'special_defense': self.pokedex.loc[name]['sp_defense'],
            'speed': self.pokedex.loc[name]['speed'],
            'against_bug': self.pokedex.loc[name]['against_bug'],
            'against_dark': self.pokedex.loc[name]['against_dark'],
            'against_dragon': self.pokedex.loc[name]['against_dragon'],
            'against_electric': self.pokedex.loc[name]['against_electric'],
            'against_fairy': self.pokedex.loc[name]['against_fairy'],
            'against_fight': self.pokedex.loc[name]['against_fight'],
            'against_fire': self.pokedex.loc[name]['against_fire'],
            'against_flying': self.pokedex.loc[name]['against_flying'],
            'against_ghost': self.pokedex.loc[name]['against_ghost'],
            'against_grass': self.pokedex.loc[name]['against_grass'],
            'against_ground': self.pokedex.loc[name]['against_ground'],
            'against_ice': self.pokedex.loc[name]['against_ice'],
            'against_normal': self.pokedex.loc[name]['against_normal'],
            'against_poison': self.pokedex.loc[name]['against_poison'],
            'against_psychic': self.pokedex.loc[name]['against_psychic'],
            'against_rock': self.pokedex.loc[name]['against_rock'],
            'against_steel': self.pokedex.loc[name]['against_steel'],
            'against_water': self.pokedex.loc[name]['against_water']
        }
        return pokemon


def main():
    #Test the pokedex
    pokedex = Pokedex()
    print(pokedex.get_pokemon('Charizard'))
    input("Press Enter to continue...")

if __name__ == "__main__":
    main()

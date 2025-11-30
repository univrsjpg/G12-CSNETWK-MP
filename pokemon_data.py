"""
Pokémon data structures and CSV parser.
"""
import csv
from typing import Dict

class Pokemon:
    def __init__(self, row: Dict[str,str]):
        self.name = row.get("name", "")
        self.hp = int(float(row.get("hp", "1")))
        self.attack = int(float(row.get("attack", "1")))
        self.defense = int(float(row.get("defense", "1")))
        self.sp_attack = int(float(row.get("sp_attack", "1")))
        self.sp_defense = int(float(row.get("sp_defense", "1")))
        self.speed = int(float(row.get("speed", "1")))
        self.type1 = row.get("type1", "") or ""
        self.type2 = row.get("type2", "") or ""
        self.against = {}
        for k,v in row.items():
            if k.startswith("against_"):
                t = k[len("against_"):]
            try:
                self.against[t] = float(v)
            except Exception:
                self.against[t] = 1.0

def to_dict(self):
    return {"name": self.name, "hp": self.hp, "attack": self.attack, "defense": self.defense,
    "sp_attack": self.sp_attack, "sp_defense": self.sp_defense, "speed": self.speed,
    "type1": self.type1, "type2": self.type2}

class Pokedex:
    def __init__(self, csv_path: str = "pokemon.csv"):
        self.by_name = {}
        try:
            with open(csv_path, encoding="utf-8") as f:
                rdr = csv.DictReader(f, delimiter="\t")
            for r in rdr:
                p = Pokemon(r)
                if p.name:
                    self.by_name[p.name] = p
        except FileNotFoundError:
            print("[pokedex] pokemon.csv not found")

def get(self, name: str):
    return self.by_name.get(name)
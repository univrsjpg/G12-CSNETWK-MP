"""
host_runner.py - Host implementation of PokeProtocol
Run this file to start as a Host.
Usage: python host_runner.py [port]
"""

import socket
import random
import json
import sys
import time
from typing import Optional, Tuple
from base_protocol import PokeProtocolBase
from pokemon_utils import normalize_pokemon_record
from pokemon_data import pokemon_db
from chatManager import ChatManager
from battle_system import create_battle_system_from_seed, BattleSystem


class PokeProtocolHost(PokeProtocolBase):
    """Host implementation of PokeProtocol"""
    
    def __init__(self, port: int = 5000):
        super().__init__(port)
        self.seed: Optional[int] = None
        self.spectators = []
        self.battle_state = "WAITING_FOR_CONNECTION"
        self.pokedex = pokemon_db
        
    def run(self):
        self.print_banner()

        # --- START CHAT MANAGER ---
        print("Starting Chat Server (port 9999)...")
        self.chat = ChatManager()
        self.chat.start()
        print("Chat Server Online!")

        if not self.create_socket():
            return
            
        if self.bind_and_listen():
            self.main_loop()
    
    def print_banner(self):
        """Display host banner"""
        print("\n" + "="*60)
        print("POKEPROTOCOL HOST RUNNER")
        print("="*60)
        print("You are hosting a Pokémon battle.")
        print("Players will connect to you.")
        print("="*60)
    
    def bind_and_listen(self) -> bool:
        """Bind to port and start listening"""
        try:
            self.socket.bind(('0.0.0.0', self.port))
            
            # Get local IP address
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            
            print(f"✓ Host listening on:")
            print(f"  IP Address: {local_ip}")
            print(f"  Port: {self.port}")
            print(f"\nGive these details to players who want to join!")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"✗ Failed to bind to port {self.port}: {e}")
            return False
    
    def main_loop(self):
        """Main host loop"""
        while True:
            self.print_menu()
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.wait_for_player()
            elif choice == "2":
                self.accept_spectator()
            elif choice == "3":
                if self.connected:
                    self.start_battle_setup()
                else:
                    print("Player not connected yet!")
            elif choice == "4":
                self.show_status()
            elif choice == "5":
                print("Exiting host...")
                break
            elif choice == "help":
                self.show_help()
            else:
                print("Invalid option. Type 'help' for commands.")
    
    def print_menu(self):
        """Display host menu"""
        print("\n" + "-"*40)
        print("HOST MENU")
        print("-"*40)
        print("[1] Wait for player")
        print("[2] Accept spectator")
        print("[3] Start battle setup")
        print("[4] Show status")
        print("[5] Exit")
        print("Type 'help' for detailed commands")
        print("-"*40)
    
    def show_help(self):
        """Show help information"""
        print("\n" + "="*60)
        print("HOST HELP")
        print("="*60)
        print("1. Wait for player - Listens for incoming player connection")
        print("2. Accept spectator - Listens for spectator connections")
        print("3. Start battle setup - Begins battle after player connects")
        print("4. Show status - Displays current connection status")
        print("5. Exit - Close the host")
        print("\nMake sure to give your IP and port to players!")
        print("="*60)
    
    def wait_for_player(self):
        """Wait for HANDSHAKE_REQUEST from a player"""
        print("\n⏳ Waiting for player connection... (Press Enter to cancel)")
        
        # Set socket to non-blocking for cancel checking
        self.socket.settimeout(1.0)
        
        try:
            while True:
                try:
                    message, address = self.receive_message(timeout=1)
                    
                    if message and message.get('message_type') == 'HANDSHAKE_REQUEST':
                        print(f"\n✓ Received connection request from {address[0]}:{address[1]}")
                        self.peer_address = address
                        if self.send_handshake_response():
                            self.battle_state = "PLAYER_CONNECTED"
                            print("✓ Player successfully connected!")
                        return
                    
                except socket.timeout:
                    # Check for user cancellation (non-blocking input)
                    pass
        except KeyboardInterrupt:
            print("\nCancelled waiting for player")
        finally:
            self.socket.settimeout(None)
    
    def send_handshake_response(self) -> bool:
        """Send HANDSHAKE_RESPONSE with random seed"""
        self.seed = random.randint(1, 1000000)
        
        message = self.build_message(
            message_type="HANDSHAKE_RESPONSE",
            seed=self.seed
        )
        
        if self.send_message(message, self.peer_address):
            self.connected = True
            print(f"✓ Sent HANDSHAKE_RESPONSE with seed: {self.seed}")
            return True
        else:
            print("✗ Failed to send handshake response")
            return False
    
    def accept_spectator(self):
        """Accept SPECTATOR_REQUEST"""
        print("\n⏳ Waiting for spectator... (Press Enter to cancel)")
        
        self.socket.settimeout(1.0)
        
        try:
            while True:
                try:
                    message, address = self.receive_message(timeout=1)
                    
                    if message and message.get('message_type') == 'SPECTATOR_REQUEST':
                        print(f"\n✓ Received spectator request from {address[0]}:{address[1]}")
                        if address not in self.spectators:
                            self.spectators.append(address)
                            self.send_spectator_response(address)
                        return
                    
                except socket.timeout:
                    pass
        except KeyboardInterrupt:
            print("\nCancelled waiting for spectator")
        finally:
            self.socket.settimeout(None)
    
    def send_spectator_response(self, address: Tuple[str, int]):
        """Send response to spectator"""
        message = self.build_message(
            message_type="SPECTATOR_RESPONSE",
            status="ACCEPTED",
            battle_state=self.battle_state
        )
        
        if self.send_message(message, address):
            print(f"✓ Spectator accepted")
        else:
            print("✗ Failed to send spectator response") 
    
    def broadcast_to_spectators(self, message):
        for spec in self.spectators:
            self.send_message(message, spec)

            """
                self.broadcast_to_spectators(message) This will be put every turn
            """
    
    def start_battle_setup(self):
        """Start the battle setup phase"""
        print("\n" + "="*50)
        print("BATTLE SETUP PHASE")
        print("="*50)
        
        self.print_sample_pokemon()
        pokemon_name = input("Enter the name or number of the Pokémon: ").strip()
        pokemon = self.fetch_pokemon(pokemon_name)
        if not pokemon:
            print("✗ Pokémon not found in the Pokédex.")
            return
        sp_attack_usage = input("Number of times to use special attacks: ")
        sp_defense_usage = input("Number of times to use special defense: ")
        # Get stat boosts
        try:
            sp_atk = int(sp_attack_usage)
            sp_def = int(sp_defense_usage)
        except (TypeError, ValueError):
            sp_atk, sp_def = 5, 5
            print("Using default values: 5 special attack, 5 special defense")
        
        stat_boosts = {
            "special_attack_uses": sp_atk,
            "special_defense_uses": sp_def
        }
        
        # Send BATTLE_SETUP message
        message = self.build_message(
            message_type="BATTLE_SETUP",
            communication_mode="P2P",
            pokemon_name=pokemon_name,
            pokemon=pokemon,
            stat_boosts=stat_boosts
        )
        
        if self.send_message(message, self.peer_address):
            print(f"\n✓ Sent BATTLE_SETUP message")
            print(f"  Pokémon: {pokemon_name}")
            print(f"  Stat boosts: {stat_boosts}")
            
            # Wait for joiner's response
            self.wait_for_battle_setup()
        else:
            print("✗ Failed to send BATTLE_SETUP")
    
    def fetch_pokemon(self, pokemon_name: str):
        """Load and normalize Pokémon information from the Pokédex."""
        raw = None
        if pokemon_name.strip().isdigit():
            raw = self.pokedex.get_pokemon_by_number(int(pokemon_name.strip()))
        if not raw:
            raw = self.pokedex.get_pokemon_by_name(pokemon_name)
        if not raw:
            return None
        return normalize_pokemon_record(raw, raw.get("name", pokemon_name))

    def print_sample_pokemon(self, limit: int = 6):
        """Display a quick list of Pokémon options."""
        print("\nSample Pokémon choices:")
        for entry in self.pokedex.get_pokemon_list(limit):
            types = "/".join(filter(None, [entry.get("type1"), entry.get("type2")])) or "Unknown"
            print(f"  [{entry['pokedex_number']:>3}] {entry['name']} ({types})")
    
    def wait_for_battle_setup(self):
        """Wait for BATTLE_SETUP from joiner"""
        print("\n⏳ Waiting for opponent's battle setup...")
        
        message, address = self.receive_message(timeout=30)
        
        if message and message.get('message_type') == 'BATTLE_SETUP':
            print("\n" + "="*50)
            print("OPPONENT'S POKÉMON")
            print("="*50)
            print(f"Name: {message.get('pokemon_name')}")
            
            # Parse Pokémon data
            pokemon_json = message.get('pokemon', '{}')
            try:
                pokemon = json.loads(pokemon_json)
                if pokemon:
                    print(f"Type(s): {', '.join(pokemon.get('type', ['Unknown']))}")
                    print(f"HP: {pokemon.get('hp', 'Unknown')}")
                    print(f"Abilities: {', '.join(pokemon.get('abilities', ['Unknown']))}")
            except:
                print(f"Pokémon data: {pokemon_json}")
            
            # Parse stat boosts
            boosts_json = message.get('stat_boosts', '{}')
            try:
                boosts = json.loads(boosts_json)
                print(f"Stat boosts: {boosts}")
            except:
                print(f"Stat boosts: {boosts_json}")
            
            self.battle_state = "BATTLE_READY"
            print("\n✓ Battle setup complete! Ready to begin.")
            print("="*50)
            self.start_battle_loop()
        else:
            print("✗ Failed to receive opponent's setup or timeout")
    
    def start_battle_loop(self):
        """
        Entry point for host to run the full turn-based battle loop.
        Host is attacker on the first turn (Model 1).
        """
        if not self.connected or self.battle_state != "BATTLE_READY":
            print("Cannot start battle: no connected player or setup not ready.")
            return

        # Create deterministic BattleSystem from seed received earlier
        bs = create_battle_system_from_seed(self.seed)

        # Normalize / use previously fetched pokemon objects
        # self.my_pokemon and self.peer_pokemon should be normalized dicts (use normalize_csv_row)
        my_poke = self.fetch_pokemon(self.my_pokemon['name']) if isinstance(self.my_pokemon, dict) else self.my_pokemon
        enemy_poke = self.player_setup.get("pokemon") if self.player_setup else None
        # If you stored JSON strings in player_setup, parse them here:
        if isinstance(enemy_poke, str):
            try:
                enemy_poke = json.loads(enemy_poke)
            except:
                pass

        # Ensure both sides have current_hp fields
        if "current_hp" not in my_poke:
            my_poke["current_hp"] = my_poke["hp"]
        if "current_hp" not in enemy_poke:
            enemy_poke["current_hp"] = enemy_poke["hp"]

        attacker_is_host = True  # Host always starts
        print("\n=== Starting Battle Loop ===")
        while True:
            if attacker_is_host:
                attacker = my_poke
                defender = enemy_poke
                peer = self.peer_address
                role = "HOST (attacker)"
            else:
                attacker = enemy_poke
                defender = my_poke
                peer = self.peer_address
                role = "JOINER (attacker)"

            print(f"\n-- {role} turn --")
            # 1) Attacker chooses move type and whether to use special-attack boost
            if attacker_is_host:
                # Prompt host user for move type and boost usage
                move_type = input(f"Choose move TYPE for {attacker['name']} (e.g., fire, water, grass, normal): ").strip().lower()
                use_atk_boost = input("Use special-attack boost now? (y/N): ").strip().lower() == 'y'
            else:
                # This branch won't be executed by host for joiner moves; host still must send ATTACK_ANNOUNCE as attacker only.
                move_type = input(f"Choose move TYPE for {attacker['name']}: ").strip().lower()
                use_atk_boost = input("Use special-attack boost now? (y/N): ").strip().lower() == 'y'

            # Build and send ATTACK_ANNOUNCE
            attack_msg = self.build_message(
                message_type="ATTACK_ANNOUNCE",
                move_type=move_type,
                use_sp_attack_boost=str(int(bool(use_atk_boost)))
            )
            print("[HOST] Sending ATTACK_ANNOUNCE ->", attack_msg.replace("\n", " | "))
            self.send_message(attack_msg, self.peer_address)

            # 2) Wait for DEFENSE_ANNOUNCE from joiner (defender)
            print("[HOST] Waiting for DEFENSE_ANNOUNCE from defender...")
            while True:
                msg, addr = self.receive_message(timeout=10)
                if not msg:
                    print("[HOST] Timeout waiting for DEFENSE_ANNOUNCE. Retrying...")
                    # for robustness you could resend ATTACK_ANNOUNCE or abort; here we loop
                    time.sleep(0.5)
                    continue
                if msg.get("message_type") == "DEFENSE_ANNOUNCE":
                    use_def_boost = bool(int(msg.get("use_sp_defense_boost", "0")))
                    print("[HOST] Received DEFENSE_ANNOUNCE:", msg)
                    break
                else:
                    print("[HOST] Ignoring message:", msg.get("message_type"))

            # 3) Both compute damage locally using BattleSystem
            calc = bs.calculate_damage(
                attacker=attacker,
                defender=defender,
                move={"type": move_type, "category": "special" if move_type in ["fire","water","grass","electric","psychic","ice"] else "physical", "power": 50},
                use_sp_attack_boost=use_atk_boost,
                use_sp_defense_boost=use_def_boost
            )

            # Apply damage locally to defender
            defender = bs.apply_damage(defender, calc["damage"])

            # 4) Send CALCULATION_REPORT
            report = bs.build_calculation_report(attacker, defender, calc)
            # ensure message_type (build_calculation_report already includes it)
            print("[HOST] Sending CALCULATION_REPORT:", report)
            self.send_message(self.build_message(**report), self.peer_address)

            # 5) Wait for opponent's CALCULATION_REPORT and compare
            print("[HOST] Waiting for opponent CALCULATION_REPORT...")
            other_report = None
            while True:
                msg, addr = self.receive_message(timeout=10)
                if not msg:
                    print("[HOST] Timeout waiting for opponent CALCULATION_REPORT. Retrying...")
                    time.sleep(0.5)
                    continue
                if msg.get("message_type") == "CALCULATION_REPORT":
                    other_report = msg
                    print("[HOST] Received opponent CALCULATION_REPORT:", other_report)
                    break
                else:
                    print("[HOST] Ignoring message:", msg.get("message_type"))

            # Compare critical fields: damage_dealt and defender_hp_remaining
            my_damage = int(report["damage_dealt"])
            my_def_hp = int(report["defender_hp_remaining"])
            other_damage = int(other_report.get("damage_dealt", -1))
            other_def_hp = int(other_report.get("defender_hp_remaining", -1))

            if my_damage == other_damage and my_def_hp == other_def_hp:
                # Matched → send CALCULATION_CONFIRM
                confirm_msg = self.build_message(message_type="CALCULATION_CONFIRM")
                self.send_message(confirm_msg, self.peer_address)
                print("[HOST] Reports match — sent CALCULATION_CONFIRM")
            else:
                # Discrepancy → send RESOLUTION_REQUEST with our values
                res_msg = self.build_message(
                    message_type="RESOLUTION_REQUEST",
                    attacker=report["attacker"],
                    move_used=report["move_used"],
                    damage_dealt=str(report["damage_dealt"]),
                    defender_hp_remaining=str(report["defender_hp_remaining"])
                )
                self.send_message(res_msg, self.peer_address)
                print("[HOST] Sent RESOLUTION_REQUEST (discrepancy)")

                # Wait for peer response: either ACK/update or further discrepancy
                msg, addr = self.receive_message(timeout=5)
                if msg and msg.get("message_type") == "ACK":
                    print("[HOST] Peer acknowledged resolution. Proceeding.")
                else:
                    print("[HOST] Resolution failed or no ACK — terminating match.")
                    return

            # Announce faint / game over if needed
            if defender.get("fainted"):
                # Send GAME_OVER with winner = attacker
                game_over_msg = self.build_message(
                    message_type="GAME_OVER",
                    winner=attacker.get("name"),
                    loser=defender.get("name")
                )
                self.send_message(game_over_msg, self.peer_address)
                print(f"[HOST] GAME_OVER sent. Winner: {attacker.get('name')}")
                self.battle_state = "GAME_OVER"
                return

            # Swap roles and continue
            attacker_is_host = not attacker_is_host
            print("[HOST] Turn complete — swapping roles.")

    def show_status(self):
        """Display current status"""
        print("\n" + "="*50)
        print("HOST STATUS")
        print("="*50)
        print(f"State: {self.battle_state}")
        print(f"Listening Port: {self.port}")
        print(f"Player Connected: {self.connected}")
        
        if self.connected:
            print(f"Player Address: {self.peer_address[0]}:{self.peer_address[1]}")
            print(f"Battle Seed: {self.seed}")
        else:
            print("Player: Not connected")
        
        print(f"Spectators: {len(self.spectators)}")
        for i, spec in enumerate(self.spectators, 1):
            print(f"  {i}. {spec[0]}:{spec[1]}")
        print("="*50)


def main():
    """Main function for host runner"""
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}. Using default port 5000.")
    
    host = PokeProtocolHost(port)
    
    try:
        host.run()
    except KeyboardInterrupt:
        print("\n\nHost interrupted by user.")
    finally:
        host.close()


if __name__ == "__main__":
    main()
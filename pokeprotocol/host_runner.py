"""
host_runner.py - Host implementation of PokeProtocol
Run this file to start as a Host.
Usage: python host_runner.py [port]
"""

import socket
import random
import json
import sys
from typing import Optional, Tuple
from base_protocol import PokeProtocolBase
from load_pokemon import Pokedex
from pokemon_utils import normalize_pokemon_record


class PokeProtocolHost(PokeProtocolBase):
    """Host implementation of PokeProtocol"""
    
    def __init__(self, port: int = 5000):
        super().__init__(port)
        self.seed: Optional[int] = None
        self.spectators = []
        self.battle_state = "WAITING_FOR_CONNECTION"
        self.pokedex = Pokedex()
        
    def run(self):
        """Main host runner"""
        self.print_banner()
        
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
                
                # Check if user pressed Enter to cancel
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    print("\nCancelled waiting for player")
                    return
                    
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
                
                # Check for user cancellation
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    print("\nCancelled waiting for spectator")
                    return
                    
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
    
    def start_battle_setup(self):
        """Start the battle setup phase"""
        print("\n" + "="*50)
        print("BATTLE SETUP PHASE")
        print("="*50)
        
        pokemon_name = input("Enter the name of the pokemon: ").strip()
        pokemon = self.fetch_pokemon(pokemon_name)
        if not pokemon:
            print("✗ Pokémon not found in the Pokédex.")
            return

        # Get stat boosts
        try:
            sp_atk = int(pokemon.get("special_attack", 3))
            sp_def = int(pokemon.get("special_defense", 2))
        except (TypeError, ValueError):
            sp_atk, sp_def = 3, 2
            print("Using default values: 3 special attack, 2 special defense")
        
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
        try:
            raw = self.pokedex.get_pokemon(pokemon_name)
        except KeyError:
            return None
        if not raw:
            return None
        return normalize_pokemon_record(raw, pokemon_name)
    
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
        else:
            print("✗ Failed to receive opponent's setup or timeout")
    
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
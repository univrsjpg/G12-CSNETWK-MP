"""
joiner_runner.py - Joiner implementation of PokeProtocol
Run this file to start as a Joiner.
Usage: python joiner_runner.py [host_ip] [port]
"""

import socket
import json
import sys
import time
import threading
from typing import Optional, Tuple, Dict, Any
from base_protocol import PokeProtocolBase
from pokemon_utils import normalize_pokemon_record
from pokemon_data import pokemon_db
import socket
CHAT_PORT = 9999
from battle_system import BattleSystem, battle_system
from chatManager import ChatManager


class PokeProtocolJoiner(PokeProtocolBase):
    """Joiner implementation of PokeProtocol"""
    
    def __init__(self, host_ip: str, host_port: int = 5000):
        super().__init__(host_port)
        self.host_address = (host_ip, host_port)
        self.seed: Optional[int] = None
        self.battle_state = "DISCONNECTED"
        self.pokedex = pokemon_db
        self.host_pokemon: Optional[Dict[str, Any]] = None 
        self.joiner_pokemon: Optional[Dict[str, Any]] = None 
        self.battle_engine: Optional[BattleSystem] = None 
        self.is_host_turn = True
        self.local_turn_report: Optional[Dict] = None # Added for comparison
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.chat_socket.bind(("0.0.0.0", 0))



    def start_chat_listener(self):
        def listen():
            while self.chat_running:
                try:
                    data, addr = self.chat_socket.recvfrom(4096)
                    print(f"\n💬 {data.decode()}")
                except:
                    pass

        self.chat_running = True
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()



    def run(self):
        """Main joiner runner"""
        self.print_banner()
        
        if not self.create_socket():
            return
        
        self.main_loop()
    
    def print_banner(self):
        """Display joiner banner"""
        print("\n" + "="*60)
        print("POKEPROTOCOL JOINER RUNNER")
        print("="*60)
        print(f"Connecting to: {self.host_address[0]}:{self.host_address[1]}")
        print("="*60)
    
    def main_loop(self):
        """Main joiner loop"""
        while True:
            self.print_menu()
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.connect_as_player()
            elif choice == "2":
                self.connect_as_spectator()
            elif choice == "3":
                if self.connected:
                    self.start_battle_setup()
                else:
                    print("Not connected to host!")
            elif choice == "4":
                self.show_status()
            elif choice == "5":
                print("Exiting joiner...")
                break
            elif choice == "6":
                # Only offer turn action if the state allows for it
                if self.battle_state == "WAITING_FOR_MOVE" and not self.is_host_turn:
                     self.start_turn()
                else:
                    print("✗ Not your turn or battle not ready.")
            elif choice == "7":
                self.send_chat_message()
            elif choice == "help":
                self.show_help()
            else:
                print("Invalid option. Type 'help' for commands.")
    
    def send_chat_message(self):
        if not self.chat_running:
            print("✗ Chat is not active. Connect as player or spectator first.")
            return

        text = input("Enter chat message: ").strip()
        if not text:
            print("✗ Empty message.")
            return

        msg = f"[Spectator] {text}" if self.battle_state == "SPECTATING" else f"[Player] {text}"
        try:
            self.chat_socket.sendto(msg.encode(), (self.host_address[0], CHAT_PORT))
            print("✓ Message sent!")
        except Exception as e:
            print(f"✗ Chat send error: {e}")



    def print_menu(self):
        """Display joiner menu"""
        print("\n" + "-"*40)
        print("JOINER MENU")
        print("-"*40)
        print("[1] Connect as player")
        print("[2] Connect as spectator")
        print("[3] Send battle setup")
        print("[4] Show status")
        if self.battle_state == "WAITING_FOR_MOVE":
            action = 'JOINER ATTACK' if not self.is_host_turn else 'WAITING FOR HOST COMMIT'
            print(f"[6] {action}")
        print("[5] Exit")
        print("Type 'help' for detailed commands")
        print("-"*40)
    
    def show_help(self):
        """Show help information"""
        print("\n" + "="*60)
        print("JOINER HELP")
        print("="*60)
        print("1. Connect as player - Connect to host as a player")
        print("2. Connect as spectator - Watch battle without playing")
        print("3. Send battle setup - Choose Pokémon after connecting")
        print("4. Show status - Display connection status")
        print("5. Exit - Close the joiner")
        print("\nYou need the host's IP address and port to connect!")
        print("="*60)
    
    def connect_as_player(self, max_retries: int = 5):
        """Send HANDSHAKE_REQUEST to host """
        print(f"\n🔗 Connecting to host...")
        
        message = self.build_message(message_type="HANDSHAKE_REQUEST")
        
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}/{max_retries}...")
            
            if self.send_message(message, self.host_address):
                print("✓ Handshake request sent")
                
                # Wait for response 
                print("⏳ Waiting for host response...")
                response, address = self.receive_message(timeout=3)
                
                if response and response.get('message_type') == 'HANDSHAKE_RESPONSE':
                    self.handle_handshake_response(response, address)
                    return True
                else:
                    print("No response from host, retrying...")
            else:
                print("Failed to send request, retrying...")
            
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
        
        print(f"\n✗ Failed to connect after {max_retries} attempts")
        return False
    
    def handle_handshake_response(self, response: dict, address: Tuple[str, int]):
        """Handle successful handshake response"""
        try:
            self.seed = int(response.get('seed', 0))
            self.battle_engine = BattleSystem(self.seed)
            self.peer_address = address
            self.connected = True
            self.battle_state = "CONNECTED"
            self.connect_chat(name="Player")
             
            
            print("\n" + "="*50)
            print("✅ CONNECTION SUCCESSFUL!")
            print("="*50)
            print(f"Connected to: {address[0]}:{address[1]}")
            print(f"Battle Seed: {self.seed}")
            print("="*50)
            
        except ValueError:
            print("✗ Invalid seed received from host")
    
    def connect_as_spectator(self):
        """Send SPECTATOR_REQUEST to host """
        print(f"\n👁️  Joining as spectator...")
        
        message = self.build_message(message_type="SPECTATOR_REQUEST")
        
        if self.send_message(message, self.host_address):
            print("✓ Spectator request sent")
            
            # Wait for response
            print("⏳ Waiting for host acceptance...")
            response, address = self.receive_message(timeout=5)
            
            if response and response.get('message_type') == 'SPECTATOR_RESPONSE':
                print("\n✅ ACCEPTED AS SPECTATOR!")
                print(f"Status: {response.get('status', 'Unknown')}")
                print(f"Battle State: {response.get('battle_state', 'Unknown')}")
                self.battle_state = "SPECTATING" 
                self.start_chat_listener()

            else:
                print("✗ No response from host or request denied")
        else:
            print("✗ Failed to send spectator request")
    
    def connect_chat(self, name="Unknown"):
        # Placeholder for chat connectivity
        msg = f"message_type: CHAT_MESSAGE\nsender: {name}\ntext: joined the lobby"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg.encode(), (self.host_address[0], CHAT_PORT))


    def start_battle_setup(self):
        """Start the battle setup phase """
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
        self.joiner_pokemon = self.battle_engine.create_battle_pokemon(pokemon, stat_boosts)
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
            
            # Wait for host's response
            self.wait_for_host_setup()
        else:
            print("✗ Failed to send BATTLE_SETUP")
    
    def wait_for_host_setup(self):
        """Wait for BATTLE_SETUP from host"""
        print("\n⏳ Waiting for host's battle setup...")
        
        message, address = self.receive_message(timeout=30)
        
        if message and message.get('message_type') == 'BATTLE_SETUP':
            print("\n" + "="*50)
            print("HOST'S POKÉMON")
            print("="*50)
            print(f"Name: {message.get('pokemon_name')}")
            
            # Parse Pokémon data
            pokemon_json = message.get('pokemon', '{}')
            boosts_json = message.get('stat_boosts', '{}')
            try:
                raw_pokemon = json.loads(pokemon_json)
                raw_boosts = json.loads(boosts_json)
                self.host_pokemon = self.battle_engine.create_battle_pokemon(raw_pokemon, raw_boosts)
            except:
                print("✗ Error parsing host's Pokémon data.")
                return
            
            # Parse stat boosts
            boosts_json = message.get('stat_boosts', '{}')
            try:
                boosts = json.loads(boosts_json)
                print(f"Stat boosts: {boosts}")

            except:
                print(f"Stat boosts: {boosts_json}")
            
            self.battle_state = "WAITING_FOR_MOVE" 
            print("\n✅ Battle setup complete! Ready to begin.")
            print("="*50)
            # Host goes first, so joiner enters the waiting loop
            self.wait_for_battle_messages()
        else:
            print("✗ Failed to receive host's setup or timeout. Cannot proceed to turn.")
    
    def wait_for_battle_messages(self):
        """
        Main loop for turn-based state.
        FIX: Use a small timeout to poll for turn switching (since Host doesn't send a turn switch message).
        """
        print("\n⏳ Entering battle loop. Waiting for Host's first move...")
        
        # FIX: Set timeout for non-blocking read to allow periodic turn check
        self.socket.settimeout(0.5) 
        
        while self.battle_state not in ["ERROR", "GAME_OVER", "DISCONNECTED"]:
            try:
                message, address = self.receive_message(timeout=0.5) # Use the short timeout
                
                if message:
                    message_type = message.get('message_type')
                    seq_num = message.get('sequence_number')
                    
                    if message_type == 'ACK':
                        print(f"-> Received ACK for {message.get('ack_number')}")
                        continue
                    
                    # ACK is sent for all sequenced messages *before* handling the message type
                    if seq_num:
                        self.send_ack(seq_num)
                        
                    # NEW LOGIC: Host sends CALCULATION_REPORT as ATTACK_COMMIT when defending
                    if self.battle_state == "WAITING_FOR_MOVE" and self.is_host_turn and message_type == 'CALCULATION_REPORT':
                        # Joiner calculates and compares
                        move_name = message.get('move_used')
                        local_report = self.calculate_opponent_attack(move_name, self.host_pokemon, self.joiner_pokemon)
                        
                        self.battle_state = "WAITING_FOR_CONFIRM"
                        self.compare_reports_and_respond(message, local_report)
                        
                        continue 
                        
                    # Handle Confirmation/Resolution when attacking (Joiner's turn)
                    elif self.battle_state == "WAITING_FOR_CONFIRM":
                        if message_type == 'CALCULATION_CONFIRM': 
                            print("✓ Received CALCULATION_CONFIRM.")
                            self.end_turn()
                            
                        elif message_type == 'RESOLUTION_REQUEST':
                            self.handle_resolution_request(message)
                        
                    elif message_type == 'GAME_OVER':
                        print(f"\n🛑 GAME OVER! {message.get('winner')} won.") 
                        self.battle_state = "GAME_OVER"
                        return
                
                # After message processing (or timeout): Check if it's the Joiner's turn.
                if self.battle_state == "WAITING_FOR_MOVE" and not self.is_host_turn:
                    print("--> Detected turn switch. Initiating attack.")
                    self.start_turn() # This breaks out of the passive loop to start the action flow
                    # IMPORTANT: start_turn calls wait_for_battle_messages again upon completion, restarting the loop.

            except socket.timeout:
                # Timeout is normal now; check turn state again
                if self.battle_state == "WAITING_FOR_MOVE" and not self.is_host_turn:
                     print("--> Timeout check: Initiating attack.")
                     self.start_turn()
                continue
                
            except Exception as e:
                print(f"Error in battle loop: {e}")
                break
        
        # Reset timeout behavior after loop ends
        self.socket.settimeout(None)

    def calculate_opponent_attack(self, move_name: str, attacker: Dict, defender: Dict) -> Dict:
        """Helper to calculate and apply damage for the reactive peer (Joiner defending)."""
        sp_atk_boost = attacker['stat_boosts']['special_attack_uses'] > 0
        sp_def_boost = defender['stat_boosts']['special_defense_uses'] > 0
        
        damage_result = self.battle_engine.calculate_damage(
            attacker, defender, move_name, 
            special_attack_boost=sp_atk_boost, special_defense_boost=sp_def_boost
        )
        self.battle_engine.apply_damage(defender, damage_result['damage'])
        report = self.battle_engine.get_battle_summary(attacker, defender, damage_result)
        
        print("\n--- JOINER'S LOCAL CALCULATION (Defending) ---")
        print(f"Damage Dealt: {report['damage_dealt']}")
        print(f"Your HP: {report['defender_hp_remaining']}")
        print("----------------------------------------------")
        return report


    def compare_reports_and_respond(self, opponent_report_msg: Dict, local_report: Dict):
        """NEW Step 2: Compare and send CONFIRM or RESOLUTION_REQUEST."""
        opponent_hp = opponent_report_msg.get('defender_hp_remaining')
        local_hp = str(local_report['defender_hp_remaining'])
        
        if opponent_hp == local_hp:
            print("✅ Calculations match! Sending CONFIRM.") 
            self.send_calculation_confirm()
            self.end_turn()
        else:
            print(f"⚠️ Calculation discrepancy! Local HP: {local_hp}, Opponent HP: {opponent_hp}")
            self.resolve_discrepancy(local_report) 


    def start_turn(self):
        """NEW Step 1: ATTACK_COMMIT (Joiner's action: Calculate damage and send report immediately)"""
        # Ensure we only proceed if it is indeed the Joiner's turn
        if self.battle_state != "WAITING_FOR_MOVE" or self.is_host_turn:
            # If start_turn was called incorrectly, exit gracefully and return to passive wait
            return
            
        attacker = self.joiner_pokemon
        defender = self.host_pokemon
        
        # 1. Joiner chooses move
        print("\n" + "="*50)
        print("YOUR TURN: CHOOSE MOVE")
        print("="*50)
        moves = attacker['available_moves']
        for i, move in enumerate(moves):
            print(f"[{i+1}] {move}")
            
        move_choice = input(f"Select move (1-{len(moves)}): ").strip()
        try:
            move_index = int(move_choice) - 1
            if 0 <= move_index < len(moves):
                move_name = moves[move_index]
            else:
                raise ValueError
        except ValueError:
            print("Invalid choice. Using first move.")
            move_name = moves[0]

        # 2. Joiner calculates damage and applies it immediately
        sp_atk_boost = attacker['stat_boosts']['special_attack_uses'] > 0
        sp_def_boost = defender['stat_boosts']['special_defense_uses'] > 0
        
        damage_result = self.battle_engine.calculate_damage(
            attacker, defender, move_name, 
            special_attack_boost=sp_atk_boost, special_defense_boost=sp_def_boost
        )
        self.battle_engine.apply_damage(defender, damage_result['damage'])
        report = self.battle_engine.get_battle_summary(attacker, defender, damage_result)
        
        print("\n--- JOINER'S ATTACK & CALCULATION ---")
        print(f"Damage Dealt: {report['damage_dealt']}")
        print(f"Opponent HP: {report['defender_hp_remaining']}")
        print(f"Message: {report['status_message']}")
        print("-------------------------------------")
        
        # 3. Send ATTACK_COMMIT (using CALCULATION_REPORT message structure) 
        seq_num = self.generate_sequence_number()
        message = self.build_message(
            message_type="CALCULATION_REPORT",
            sequence_number=seq_num,
            attacker=report['attacker'],
            move_used=move_name,
            remaining_health=report['attacker_hp_remaining'],
            damage_dealt=report['damage_dealt'],
            defender_hp_remaining=report['defender_hp_remaining'],
            status_message=report['status_message']
        )
        
        if self.send_message(message, self.peer_address):
            print(f"✓ Sent ATTACK_COMMIT (CALCULATION_REPORT) (Seq: {seq_num})")
            self.battle_state = "WAITING_FOR_CONFIRM"
            self.local_turn_report = report # Store for reconciliation
            self.wait_for_report_and_confirm()
        else:
            print("✗ Failed to send ATTACK_COMMIT.")
            self.battle_state = "ERROR"


    def wait_for_report_and_confirm(self):
        """Modified: Joiner attacked, now waits ONLY for CONFIRM/RESOLUTION"""
        max_retries = 3
        timeout = 5 # 5 seconds
        
        for attempt in range(max_retries):
            print(f"\n⏳ Waiting for Host's CALCULATION_CONFIRM or RESOLUTION_REQUEST (Attempt {attempt + 1}/{max_retries})...")
            
            response_msg, _ = self.receive_message(timeout=timeout)
            
            if response_msg:
                message_type = response_msg.get('message_type')
                seq_num = response_msg.get('sequence_number')
                
                if message_type == 'CALCULATION_CONFIRM': 
                    self.send_ack(seq_num)
                    print("✓ Received CALCULATION_CONFIRM.")
                    self.end_turn()
                    return # Exit successfully
                    
                elif message_type == 'RESOLUTION_REQUEST':
                    self.handle_resolution_request(response_msg)
                    if self.battle_state == "WAITING_FOR_MOVE":
                        return # Exit successfully after resolution
                    elif self.battle_state == "TERMINATED":
                        return # Exit on error
                
                print(f"Warning: Received unexpected message type: {message_type}. Waiting for expected response.")
            
        print("✗ Timeout or invalid message. Maximum retries reached. Batstle status set to ERROR.")
        self.battle_state = "ERROR"

    def send_calculation_confirm(self):
        """Step 4: Send CALCULATION_CONFIRM """
        seq_num = self.generate_sequence_number()
        message = self.build_message(
            message_type="CALCULATION_CONFIRM",
            sequence_number=seq_num
        )
        self.send_message(message, self.peer_address)
        print(f"✓ Sent CALCULATION_CONFIRM (Seq: {seq_num})")

    def resolve_discrepancy(self, local_report: Dict):
        """Send RESOLUTION_REQUEST with Joiner's calculated values"""
        print("Sending RESOLUTION_REQUEST with local values.")
        
        seq_num = self.generate_sequence_number()
        resolution_msg = self.build_message(
            message_type="RESOLUTION_REQUEST",
            sequence_number=seq_num,
            attacker=local_report['attacker'],
            move_used=local_report['move_used'],
            damage_dealt=local_report['damage_dealt'],
            defender_hp_remaining=local_report['defender_hp_remaining']
        )
        
        if self.send_message(resolution_msg, self.peer_address):
            print("⏳ Waiting for opponent's ACK/agreement on RESOLUTION_REQUEST.")
            ack_msg, _ = self.receive_message(timeout=5)
            
            if ack_msg and ack_msg.get('message_type') == 'ACK' and ack_msg.get('ack_number') == str(seq_num):
                print("✅ Opponent agreed to resolution. Battle state updated.")
                self.end_turn()
            else:
                print("❌ Opponent did not agree or timeout. Battle SHOUD terminate.")
                self.battle_state = "TERMINATED"
        else:
            print("✗ Failed to send RESOLUTION_REQUEST.")

    def handle_resolution_request(self, request: Dict):
        """Handle incoming RESOLUTION_REQUEST from Host """
        request_hp = request.get('defender_hp_remaining')
        local_hp = str(self.local_turn_report['defender_hp_remaining'])

        if request_hp == local_hp:
             print("✅ Host's RESOLUTION_REQUEST matches Joiner's calculation. Acknowledging and updating state.")
             self.end_turn() 
        else:
             print("❌ Fundamental calculation error detected. Joiner still disagrees. Terminating.") 
             self.battle_state = "TERMINATED"
             return


    def end_turn(self):
        """Prepare for the next turn"""
        
        # 1. Check for win condition
        if self.host_pokemon['current_hp'] <= 0:
            self.send_game_over(winner=self.joiner_pokemon['name'], loser=self.host_pokemon['name']) 
            return
        
        # 2. If no win, switch turn
        print("\n--- TURN ENDED ---")
        self.is_host_turn = not self.is_host_turn # Reverse turn order 
        self.battle_state = "WAITING_FOR_MOVE"
        print(f"It is now the {'Host' if self.is_host_turn else 'Joiner'}'s turn.")
        self.wait_for_battle_messages() 

    def send_game_over(self, winner: str, loser: str):
        """
        Send GAME_OVER message and wait for opponent's ACK.
        This function is now responsible for ensuring delivery (with retries).
        """
        seq_num = self.generate_sequence_number()
        message = self.build_message(
            message_type="GAME_OVER",
            sequence_number=seq_num,
            winner=winner,
            loser=loser
        )
        
        max_retries = 3
        timeout = 5
        
        for attempt in range(max_retries):
            if self.send_message(message, self.peer_address):
                print(f"\n🎉 Sent GAME_OVER! {winner} wins. (Attempt {attempt + 1}/{max_retries})")
                
                # Wait for ACK
                ack_msg, _ = self.receive_message(timeout=timeout)
                
                if ack_msg and ack_msg.get('message_type') == 'ACK' and ack_msg.get('ack_number') == str(seq_num):
                    print("✓ Received ACK for GAME_OVER. Final state confirmed.")
                    self.battle_state = "GAME_OVER"
                    return # Exit successfully
                
                print("Warning: No ACK received for GAME_OVER. Retrying...")
            else:
                print("✗ Failed to send GAME_OVER message. Retrying...")
        
        print("❌ Failed to confirm GAME_OVER state after maximum retries. Battle terminated.")
        self.battle_state = "TERMINATED"

    def send_ack(self, ack_number: str):
        """Send a basic ACK message"""
        ack_message = self.build_message(message_type="ACK", ack_number=ack_number) 
        self.send_message(ack_message, self.peer_address)


    def fetch_pokemon(self, pokemon_name: str):
        """Load and normalize Pokémon information from the Pokédex."""
        raw = None
        # We must use the methods provided in the Pokedex class (pokemon_db)
        raw = self.pokedex.get_pokemon_by_name(pokemon_name)
        if not raw:
            # Try to search by number if the name didn't work
            try:
                if pokemon_name.strip().isdigit():
                    raw = self.pokedex.get_pokemon_by_number(int(pokemon_name.strip()))
            except ValueError:
                pass # Not a valid number
        
        return raw

    def print_sample_pokemon(self, limit: int = 10):
        """Display quick choices to help the player."""
        pokemon_list = self.pokedex.get_pokemon_list(limit)
        
        for entry in pokemon_list:
            # Assuming the normalized dictionary from Pokedex returns 'type1' and 'type2'
            type1 = entry.get('type1', '???')
            type2 = entry.get('type2')
            types = "/".join(filter(None, [type1, type2])) or "Unknown"
            
            # Note: We need 'pokedex_number' in the normalized dict for the display format
            pokedex_num = entry.get('pokedex_number', '???')
            
            print(f"  [{pokedex_num:>3}] {entry.get('name', '???')} ({types})")
        print("...")
    
    def show_status(self):
        """Display current status"""
        print("\n" + "="*50)
        print("JOINER STATUS")
        print("="*50)
        print(f"State: {self.battle_state}")
        print(f"Target Host: {self.host_address[0]}:{self.host_address[1]}")
        print(f"Connected: {self.connected}")
        
        if self.connected:
            print(f"Host Address: {self.peer_address[0]}:{self.peer_address[1]}")
            print(f"Battle Seed: {self.seed}")
        else:
            print("Host: Not connected")
        print("="*50)


def main():
    """Main function for joiner runner"""
    # Get host IP and port from command line arguments or prompt
    host_ip = "127.0.0.1"
    port = 5000
    
    if len(sys.argv) > 1:
        host_ip = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port: {sys.argv[2]}. Using default port 5000.")
    
    # If no arguments provided, prompt for host
    if len(sys.argv) <= 1:
        print("\nEnter host details:")
        host_ip = input(f"Host IP [{host_ip}]: ").strip() or host_ip
        port_str = input(f"Port [{port}]: ").strip()
        if port_str:
            try:
                port = int(port_str)
            except ValueError:
                print(f"Invalid port. Using {port}.")
    
    joiner = PokeProtocolJoiner(host_ip, port)
    
    try:
        joiner.run()
    except KeyboardInterrupt:
        print("\n\nJoiner interrupted by user.")
    finally:
        joiner.close()


if __name__ == "__main__":
    main()
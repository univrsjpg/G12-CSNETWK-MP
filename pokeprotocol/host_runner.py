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
from typing import Optional, Tuple, Dict, Any
from base_protocol import PokeProtocolBase
from pokemon_utils import normalize_pokemon_record
from pokemon_data import pokemon_db
from chatManager import ChatManager
from battle_system import BattleSystem, battle_system


class PokeProtocolHost(PokeProtocolBase):
    """Host implementation of PokeProtocol"""
    
    def __init__(self, port: int = 5000):
        super().__init__(port)
        self.seed: Optional[int] = None
        self.spectators = []
        self.battle_state = "WAITING_FOR_CONNECTION"
        self.pokedex = pokemon_db
        self.host_pokemon: Optional[Dict[str, Any]] = None 
        self.joiner_pokemon: Optional[Dict[str, Any]] = None 
        self.battle_engine: Optional[BattleSystem] = None 
        self.is_host_turn = True
        self.opponent_calc_report: Optional[Dict[str, str]] = None
        
    def run(self):
        self.print_banner()

        # --- START CHAT MANAGER ---
        print("Starting Chat Server (port 9999)...")
        # Assuming ChatManager is defined elsewhere and works correctly
        # self.chat = ChatManager()
        # self.chat.start()
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
            elif choice == "6":
                # Check for passive turn handler before starting own turn
                if self.battle_state == "WAITING_FOR_MOVE":
                    # FIX: Option 6 only triggers the Host's attack, 
                    # as passive listening is now automatic (called in end_turn).
                    if self.is_host_turn:
                        self.start_turn()
                    else:
                        # If it's not the Host's turn, and they manually select 6, 
                        # they should be reminded that the system is already listening.
                        print("✗ Not your turn. System is passively waiting for opponent's move.")
                else:
                    print("✗ Battle setup not complete. Use option [3] first.")
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
        if self.battle_state == "WAITING_FOR_MOVE":
            # Menu option 6 now reflects the new simplified flow
            action = 'HOST ATTACK' if self.is_host_turn else 'WAITING FOR OPPONENT COMMIT (Listening...)'
            print(f"[6] {action}")
        print("[5] Exit")
        print("Type 'help' for detailed commands")
        print("-"*40)
    
    
    def start_turn(self):
        """NEW Step 1: ATTACK_COMMIT (Host's action: Calculate damage and send report immediately)"""
        # Critical precondition check
        if not self.joiner_pokemon or not self.host_pokemon:
            print("✗ ERROR: Battle Pokémon data is incomplete. Ensure setup phase finished successfully.")
            return

        if self.battle_state != "WAITING_FOR_MOVE" or not self.is_host_turn:
            print("✗ Not your turn or battle not ready.")
            return

        attacker = self.host_pokemon
        defender = self.joiner_pokemon
        
        # 1. Host chooses move
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

        # 2. Host calculates damage and applies it immediately
        sp_atk_boost = attacker['stat_boosts']['special_attack_uses'] > 0
        sp_def_boost = defender['stat_boosts']['special_defense_uses'] > 0
        
        damage_result = self.battle_engine.calculate_damage(
            attacker, defender, move_name, 
            special_attack_boost=sp_atk_boost, special_defense_boost=sp_def_boost
        )
        self.battle_engine.apply_damage(defender, damage_result['damage'])
        report = self.battle_engine.get_battle_summary(attacker, defender, damage_result)
        
        print("\n--- HOST'S ATTACK & CALCULATION ---")
        print(f"Damage Dealt: {report['damage_dealt']}")
        print(f"Opponent HP: {report['defender_hp_remaining']}")
        print(f"Message: {report['status_message']}")
        print("-----------------------------------")
        
        # 3. Send ATTACK_COMMIT (using CALCULATION_REPORT message structure)
        seq_num = self.generate_sequence_number()
        message = self.build_message(
            message_type="CALCULATION_REPORT", # Reuse CALCULATION_REPORT message type
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
            self.battle_state = "WAITING_FOR_CONFIRM" # New state
            self.wait_for_report_and_confirm(report)
        else:
            print("✗ Failed to send ATTACK_COMMIT.")
            self.battle_state = "ERROR"
    
    def wait_for_opponent_commit(self):
        """
        NEW Step 1 (Reactive): Wait for Joiner's ATTACK_COMMIT (CALCULATION_REPORT) (with retries/polling)
        This is the blocking listener loop for the passive turn.
        """
        max_retries = 60 # Set high to wait ~30 seconds for opponent's move (60 * 0.5s)
        timeout = 0.5    # Small timeout for polling
        
        print("\n⏳ Waiting for Joiner's attack commitment (Auto-Listening)...")
        
        # FIX: We now enter a continuous loop to wait for the packet
        while self.battle_state == "WAITING_FOR_MOVE" and not self.is_host_turn:
            
            message, address = self.receive_message(timeout=timeout)
            
            if message:
                message_type = message.get('message_type')
                seq_num = message.get('sequence_number')

                if message_type == 'ACK':
                    print(f"-> Received ACK for {message.get('ack_number')}")
                    continue
                
                # Critical message received: CALCULATION_REPORT (the Commit)
                if message_type == 'CALCULATION_REPORT':
                    self.send_ack(seq_num)
                    print(f"✓ Received opponent's ATTACK_COMMIT (Seq: {seq_num}).")
                    
                    # Host independently calculates the damage for comparison
                    move_name = message.get('move_used')
                    local_report = self.calculate_opponent_attack(move_name, self.joiner_pokemon, self.host_pokemon)
                    
                    self.battle_state = "WAITING_FOR_CONFIRM"
                    self.compare_reports_and_respond(message, local_report)
                    
                    # If the turn concluded successfully, the state will be reset to WAITING_FOR_MOVE by end_turn.
                    if self.battle_state in ["WAITING_FOR_MOVE", "GAME_OVER", "TERMINATED"]: 
                        return
                
                elif message_type == 'GAME_OVER':
                    # --- CRITICAL FIX: Send ACK immediately upon receiving GAME_OVER ---
                    if seq_num:
                        self.send_ack(seq_num)
                    # ------------------------------------------------------------------
                    
                    print(f"\n🛑 GAME OVER! {message.get('winner')} won.")
                    self.battle_state = "GAME_OVER"
                    return
                
                else:
                    print(f"Warning: Received unexpected message type: {message_type}. Waiting for expected response.")
            
            # If timeout, the loop continues (polling).
        
        # If the loop breaks due to state change (e.g., user selected option 5)
        print("... Host stopped listening for opponent's move.")


    def calculate_opponent_attack(self, move_name: str, attacker: Dict, defender: Dict) -> Dict:
        """Helper to calculate and apply damage for the reactive peer."""
        sp_atk_boost = attacker['stat_boosts']['special_attack_uses'] > 0
        sp_def_boost = defender['stat_boosts']['special_defense_uses'] > 0
        
        damage_result = self.battle_engine.calculate_damage(
            attacker, defender, move_name, 
            special_attack_boost=sp_atk_boost, special_defense_boost=sp_def_boost
        )
        self.battle_engine.apply_damage(defender, damage_result['damage'])
        report = self.battle_engine.get_battle_summary(attacker, defender, damage_result)
        
        print("\n--- HOST'S LOCAL CALCULATION (Defending) ---")
        print(f"Damage Dealt: {report['damage_dealt']}")
        print(f"Your HP: {report['defender_hp_remaining']}")
        print("--------------------------------------------")
        return report


    def compare_reports_and_respond(self, opponent_report_msg: Dict, local_report: Dict):
        """NEW Step 2: Compare and send CONFIRM or RESOLUTION_REQUEST."""
        # This method is used when the Host is defending.
        opponent_hp = opponent_report_msg.get('defender_hp_remaining')
        local_hp = str(local_report['defender_hp_remaining'])
        
        if opponent_hp == local_hp:
            print("✅ Calculations match! Sending CONFIRM.")
            self.send_calculation_confirm()
            self.end_turn()
        else:
            print(f"⚠️ Calculation discrepancy! Local HP: {local_hp}, Opponent HP: {opponent_hp}")
            self.resolve_discrepancy(local_report)

    def wait_for_report_and_confirm(self, local_report: Dict):
        """Modified: Host attacked, now waits ONLY for CONFIRM/RESOLUTION (with retries)"""
        max_retries = 3
        timeout = 5 # 5 seconds
        
        for attempt in range(max_retries):
            print(f"\n⏳ Waiting for opponent's CALCULATION_CONFIRM or RESOLUTION_REQUEST (Attempt {attempt + 1}/{max_retries})...")
            
            response_msg, _ = self.receive_message(timeout=timeout)
            
            if response_msg:
                message_type = response_msg.get('message_type')
                seq_num = response_msg.get('sequence_number')
                
                if message_type == 'CALCULATION_CONFIRM':
                    self.send_ack(seq_num)
                    print("✓ Received CALCULATION_CONFIRM. Turn complete.")
                    self.end_turn()
                    return # Exit successfully
                    
                elif message_type == 'RESOLUTION_REQUEST':
                    self.handle_resolution_request(response_msg, local_report)
                    # The resolution handler will call end_turn if successful
                    if self.battle_state == "WAITING_FOR_MOVE":
                        return # Exit successfully after resolution
                    elif self.battle_state == "TERMINATED":
                        return # Exit on error
                
                # If we received a message but it wasn't the expected type, log and continue loop
                print(f"Warning: Received unexpected message type: {message_type}. Waiting for expected response.")
                # If we receive something unexpected, we continue the loop, potentially waiting on the next receive_message call.

            # If the loop finishes without return, it timed out or received unexpected messages.
            
        print("✗ Timeout or invalid message. Maximum retries reached. Battle status set to ERROR.")
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
        """Send RESOLUTION_REQUEST with Host's calculated values """
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
            # Wait for opponent's ACK to confirm agreement
            print("⏳ Waiting for opponent's ACK/agreement on RESOLUTION_REQUEST.")
            # The next message received will be the ACK if they agree.
            ack_msg, _ = self.receive_message(timeout=5)
            
            if ack_msg and ack_msg.get('message_type') == 'ACK' and ack_msg.get('ack_number') == str(seq_num):
                print("✅ Opponent agreed to resolution. Battle state updated.")
                self.end_turn()
            else:
                print("❌ Opponent did not agree or timeout. Battle SHOUD terminate.")
                self.battle_state = "TERMINATED"
        else:
            print("✗ Failed to send RESOLUTION_REQUEST.")

    def handle_resolution_request(self, request: Dict, local_report: Dict):
        """Handle incoming RESOLUTION_REQUEST from Joiner """
        request_hp = request.get('defender_hp_remaining')
        local_hp = str(local_report['defender_hp_remaining'])
        
        if request_hp == local_hp:
            print("⚠️ Received RESOLUTION_REQUEST but calculations match. Ignoring.")
            self.end_turn()
            return
        
        # Check if Host agrees with the Joiner's reported values
        if request_hp != local_hp:
             # If it still disagrees, this indicates a fundamental error, and the battle SHOULD terminate. 
             print("❌ Fundamental calculation error detected. Host disagrees with Joiner's RESOLUTION_REQUEST. Terminating.")
             self.battle_state = "TERMINATED"
             return

    def end_turn(self):
        """Prepare for the next turn"""
        
        # 1. Check for win condition
        if self.joiner_pokemon['current_hp'] <= 0:
            # If win condition met, send GAME_OVER and return.
            self.send_game_over(winner=self.host_pokemon['name'], loser=self.joiner_pokemon['name']) 
            return

        # 2. If no win, switch turn
        print("\n--- TURN ENDED ---")
        self.is_host_turn = not self.is_host_turn  # Reverse turn order 
        self.battle_state = "WAITING_FOR_MOVE"
        print(f"It is now the {'Host' if self.is_host_turn else 'Joiner'}'s turn.")
        
        # --- FIX: Automatically enter passive listening mode if turn switches to Joiner ---
        if not self.is_host_turn:
            self.wait_for_opponent_commit()
        # ---------------------------------------------------------------------------------

    def send_game_over(self, winner: str, loser: str):
        """
        Send GAME_OVER message and wait for opponent's ACK.
        This function is now responsible for ensuring delivery.
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
        self.battle_state = "TERMINATED" # Set to terminated if final state cannot be confirmed

    def send_ack(self, ack_number: str):
        """Send a basic ACK message"""
        ack_message = self.build_message(message_type="ACK", ack_number=ack_number)
        self.send_message(ack_message, self.peer_address)

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
        self.battle_engine = BattleSystem(self.seed)
        
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
        self.host_pokemon = self.battle_engine.create_battle_pokemon(pokemon, stat_boosts)
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
        # We must use the methods provided in the Pokedex class (pokemon_db)
        # Assuming pokemon_db is an instance of the Pokedex class
        raw = self.pokedex.get_pokemon_by_name(pokemon_name)
        if not raw:
            # Try to search by number if the name didn't work
            try:
                if pokemon_name.strip().isdigit():
                    raw = self.pokedex.get_pokemon_by_number(int(pokemon_name.strip()))
            except ValueError:
                pass # Not a valid number
        
        return raw

    def print_sample_pokemon(self, limit: int = 6):
        """Display a quick list of Pokémon options."""
        print("\nSample Pokémon choices:")
        pokemon_list = self.pokedex.get_pokemon_list(limit)
        
        for entry in pokemon_list:
            # Assuming the normalized dictionary from Pokedex returns 'type1' and 'type2'
            type1 = entry.get('type1', '???')
            type2 = entry.get('type2')
            types = "/".join(filter(None, [type1, type2])) or "Unknown"
            
            # Note: We need 'pokedex_number' in the normalized dict for the display format
            pokedex_num = entry.get('pokedex_number', '???')
            
            print(f"  [{pokedex_num:>3}] {entry.get('name', '???')} ({types})")
    
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
            boosts_json = message.get('stat_boosts', '{}')
            
            try:
                raw_pokemon = json.loads(pokemon_json)
                raw_boosts = json.loads(boosts_json)
                
                # --- CRITICAL CHECK ADDED ---
                if 'type1' not in raw_pokemon:
                    print("✗ Error: Opponent's Pokémon data is missing essential 'type1' field. Setup aborted.")
                    return
                # ----------------------------

                self.joiner_pokemon = self.battle_engine.create_battle_pokemon(raw_pokemon, raw_boosts)
            except Exception as e:
                print(f"✗ Error parsing opponent's Pokémon data: {e}")
                return
            
            # Parse stat boosts
            boosts_json = message.get('stat_boosts', '{}')
            try:
                boosts = json.loads(boosts_json)
                print(f"Stat boosts: {boosts}")
            except:
                print(f"Stat boosts: {boosts_json}")
            
            # --- FIX: Set state and return *after* successful parsing ---
            self.battle_state = "WAITING_FOR_MOVE" 
            print("\n✓ Battle setup complete! Ready to begin.")
            print("="*50)
            return
            # -----------------------------------------------------------
        else:
            print("✗ Failed to receive opponent's setup or timeout. Cannot proceed to turn.")
            return
    
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
        
        # Display Pokémon health if battle is active
        if self.battle_state in ["WAITING_FOR_MOVE", "WAITING_FOR_CONFIRM", "GAME_OVER"] and self.host_pokemon and self.joiner_pokemon:
            host_hp = f"{self.host_pokemon['current_hp']}/{self.host_pokemon['max_hp']}"
            joiner_hp = f"{self.joiner_pokemon['current_hp']}/{self.joiner_pokemon['max_hp']}"
            print("\n--- POKÉMON HEALTH ---")
            print(f"Your Pokémon ({self.host_pokemon['name']}): HP {host_hp}")
            print(f"Opponent ({self.joiner_pokemon['name']}): HP {joiner_hp}")
            print("----------------------")

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
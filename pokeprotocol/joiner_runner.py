"""
joiner_runner.py - Joiner implementation of PokeProtocol
Run this file to start as a Joiner.
Usage: python joiner_runner.py [host_ip] [port]
"""

import socket
import json
import sys
import time
from typing import Optional, Tuple, Dict, Any
from base_protocol import PokeProtocolBase
from pokemon_utils import normalize_pokemon_record
from pokemon_data import pokemon_db
import socket
CHAT_PORT = 9999
from battle_system import BattleSystem, battle_system


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
        self.local_turn_report: Optional[Dict] = None

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
            elif choice == "help":
                self.show_help()
            else:
                print("Invalid option. Type 'help' for commands.")
    
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
            # self.connect_chat(name="Player") 
            
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
<<<<<<< HEAD
            self.run_defender_loop()

=======
            # Host goes first, so joiner enters the waiting loop
            self.wait_for_battle_messages()
>>>>>>> bb72a50e486076069be496322099e8d8c3ca8bd8
        else:
            print("✗ Failed to receive host's setup or timeout. Cannot proceed to turn.")
    
    def wait_for_battle_messages(self):
        """Main loop for turn-based state"""
        print("\n⏳ Entering battle loop. Waiting for Host's first move...")
        
        while self.battle_state not in ["ERROR", "GAME_OVER", "DISCONNECTED"]:
            try:
                message, address = self.receive_message(timeout=None)
                
                if message:
                    message_type = message.get('message_type')
                    seq_num = message.get('sequence_number')
                    
                    if message_type == 'ACK':
                        print(f"-> Received ACK for {message.get('ack_number')}")
                        continue
                    
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
                            
                            # --- CRITICAL FIX: Send ACK after receiving confirmation ---
                            self.send_ack(seq_num)
                            # --------------------------------------------------------
                            
                            print("✓ Received CALCULATION_CONFIRM.")
                            self.end_turn()
                            
                        elif message_type == 'RESOLUTION_REQUEST':
                            self.handle_resolution_request(message)
                        
                    elif self.battle_state == "WAITING_FOR_MOVE" and not self.is_host_turn:
                        # This is the Joiner's turn to attack
                        self.start_turn()
                        
                    elif message_type == 'GAME_OVER':
                        print(f"\n🛑 GAME OVER! {message.get('winner')} won.") 
                        self.battle_state = "GAME_OVER"
                        return

            except Exception as e:
                print(f"Error in battle loop: {e}")
                break

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
        if self.battle_state != "WAITING_FOR_MOVE" or self.is_host_turn:
            self.wait_for_battle_messages()
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
        print("\n⏳ Waiting for Host's CALCULATION_CONFIRM or RESOLUTION_REQUEST...")
        
        response_msg, _ = self.receive_message(timeout=5)
        
        if response_msg and response_msg.get('message_type') == 'CALCULATION_CONFIRM':
            
            # The ACK fix is applied inside wait_for_battle_messages loop flow when the
            # message is received there. If received here, we need the ACK.
            # However, since this method is blocking, the flow is cleaner if handled
            # inside the main message loop. 
            
            # But since this method is blocking and expecting a CONFIRM, 
            # we apply the ACK here to ensure the reliability layer is satisfied.
            self.send_ack(response_msg.get('sequence_number'))
            
            print("✓ Received CALCULATION_CONFIRM.")
            self.end_turn()
            
        elif response_msg and response_msg.get('message_type') == 'RESOLUTION_REQUEST':
             self.handle_resolution_request(response_msg)
        else:
            print("✗ Timeout or invalid message.")
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
        
        if self.host_pokemon['current_hp'] <= 0:
            self.send_game_over(winner=self.joiner_pokemon['name'], loser=self.host_pokemon['name']) 
            return
        
        print("\n--- TURN ENDED ---")
        self.is_host_turn = not self.is_host_turn # Reverse turn order 
        self.battle_state = "WAITING_FOR_MOVE"
        print(f"It is now the {'Host' if self.is_host_turn else 'Joiner'}'s turn.")
        self.wait_for_battle_messages() 

    def send_game_over(self, winner: str, loser: str):
        """Send GAME_OVER message """
        seq_num = self.generate_sequence_number()
        message = self.build_message(
            message_type="GAME_OVER",
            sequence_number=seq_num,
            winner=winner,
            loser=loser
        )
        if self.send_message(message, self.peer_address):
            print(f"\n🎉 Sent GAME_OVER! {winner} wins.")
            self.battle_state = "GAME_OVER"

    def send_ack(self, ack_number: str):
        """Send a basic ACK message"""
        ack_message = self.build_message(message_type="ACK", ack_number=ack_number) 
        self.send_message(ack_message, self.peer_address)


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
        """Display quick choices to help the player."""
        print("\nSample Pokémon choices:")
        # We need a method in Pokedex to get a list for display.
        pokemon_list = self.pokedex.get_pokemon_list(limit)
        
        for entry in pokemon_list:
            # Assuming the normalized dictionary from Pokedex returns 'type1' and 'type2'
            type1 = entry.get('type1', '???')
            type2 = entry.get('type2')
            types = "/".join(filter(None, [type1, type2])) or "Unknown"
            
            # Note: We need 'pokedex_number' in the normalized dict for the display format
            pokedex_num = entry.get('pokedex_number', '???')
            
            print(f"  [{pokedex_num:>3}] {entry.get('name', '???')} ({types})")
    
    def run_defender_loop(self):
        """
        Joiner runs a loop that listens for ATTACK_ANNOUNCE (host attacks first),
        replies DEFENSE_ANNOUNCE, computes and reports, and confirms.
        """
        if not self.connected or self.battle_state != "BATTLE_READY":
            print("Cannot run turn loop: not connected or setup not ready.")
            return

        bs = create_battle_system_from_seed(self.seed)

        # Ensure normalized pokemon dicts exist: self.my_pokemon and host_pokemon
        my_poke = self.fetch_pokemon(self.my_pokemon['name']) if isinstance(self.my_pokemon, dict) else self.my_pokemon
        host_poke = None
        # The host's setup likely stored in self.peer_setup (or you parsed it earlier)
        if self.peer_setup and isinstance(self.peer_setup.get("pokemon"), dict):
            host_poke = self.peer_setup.get("pokemon")
        if host_poke is None:
            print("[JOINER] Host pokemon not found locally; waiting for host setup...")
            # attempt a blocking receive for BATTLE_SETUP
            msg, addr = self.receive_message(timeout=30)
            if msg and msg.get("message_type") == "BATTLE_SETUP":
                try:
                    host_poke = json.loads(msg.get("pokemon")) if isinstance(msg.get("pokemon"), str) else msg.get("pokemon")
                except:
                    host_poke = msg.get("pokemon")
        if "current_hp" not in my_poke:
            my_poke["current_hp"] = my_poke["hp"]
        if "current_hp" not in host_poke:
            host_poke["current_hp"] = host_poke["hp"]

        attacker_is_host = True  # host starts as attacker
        print("\n=== Joiner Turn Loop (defender first) ===")
        while True:
            if attacker_is_host:
                # 1) Wait for ATTACK_ANNOUNCE
                print("[JOINER] Waiting for ATTACK_ANNOUNCE from host...")
                while True:
                    msg, addr = self.receive_message(timeout=10)
                    if not msg:
                        print("[JOINER] Timeout waiting for ATTACK_ANNOUNCE; keep listening...")
                        continue
                    if msg.get("message_type") == "ATTACK_ANNOUNCE":
                        move_type = msg.get("move_type")
                        attacker_boost_flag = bool(int(msg.get("use_sp_attack_boost", "0")))
                        print("[JOINER] Received ATTACK_ANNOUNCE:", msg)
                        break
                    else:
                        print("[JOINER] Ignoring message:", msg.get("message_type"))

                # 2) DEFENSE_ANNOUNCE — decide whether to use defense boost
                use_def_boost = False
                choice = input(f"Host used move type {move_type}. Do you want to use special-defense boost? (y/N): ").strip().lower()
                use_def_boost = (choice == 'y')
                defense_msg = self.build_message(
                    message_type="DEFENSE_ANNOUNCE",
                    use_sp_defense_boost=str(int(use_def_boost))
                )
                self.send_message(defense_msg, self.peer_address)
                print("[JOINER] Sent DEFENSE_ANNOUNCE:", defense_msg.replace("\n"," | "))

                # 3) Compute damage locally (joiner calculates as defender)
                calc = bs.calculate_damage(
                    attacker=host_poke,
                    defender=my_poke,
                    move={"type": move_type, "category": "special" if move_type in ["fire","water","grass","electric","psychic","ice"] else "physical", "power": 50},
                    use_sp_attack_boost=attacker_boost_flag,
                    use_sp_defense_boost=use_def_boost
                )
                my_poke = bs.apply_damage(my_poke, calc["damage"])

                # Send CALCULATION_REPORT
                report = bs.build_calculation_report(host_poke, my_poke, calc)
                print("[JOINER] Sending CALCULATION_REPORT:", report)
                self.send_message(self.build_message(**report), self.peer_address)

                # 4) Wait for host's CALCULATION_REPORT and compare
                print("[JOINER] Waiting for host's CALCULATION_REPORT...")
                other_report = None
                while True:
                    msg, addr = self.receive_message(timeout=10)
                    if not msg:
                        print("[JOINER] Timeout waiting for host report; keep listening...")
                        continue
                    if msg.get("message_type") == "CALCULATION_REPORT":
                        other_report = msg
                        print("[JOINER] Received host CALCULATION_REPORT:", other_report)
                        break
                    else:
                        print("[JOINER] Ignoring message:", msg.get("message_type"))

                # Compare
                my_damage = int(report["damage_dealt"])
                my_def_hp = int(report["defender_hp_remaining"])
                other_damage = int(other_report.get("damage_dealt", -1))
                other_def_hp = int(other_report.get("defender_hp_remaining", -1))

                if my_damage == other_damage and my_def_hp == other_def_hp:
                    # Reports match → wait for CALCULATION_CONFIRM from host
                    print("[JOINER] Reports match, waiting for CALCULATION_CONFIRM...")
                    while True:
                        msg, addr = self.receive_message(timeout=10)
                        if not msg:
                            print("[JOINER] Waiting for CALCULATION_CONFIRM...")
                            continue
                        if msg.get("message_type") == "CALCULATION_CONFIRM":
                            print("[JOINER] Received CALCULATION_CONFIRM — turn resolved.")
                            break
                        else:
                            print("[JOINER] Ignoring message:", msg.get("message_type"))
                else:
                    # Discrepancy → wait for host RESOLUTION_REQUEST or send own
                    print("[JOINER] Discrepancy detected. Sending RESOLUTION_REQUEST with our values.")
                    res_msg = self.build_message(
                        message_type="RESOLUTION_REQUEST",
                        attacker=report["attacker"],
                        move_used=report["move_used"],
                        damage_dealt=str(report["damage_dealt"]),
                        defender_hp_remaining=str(report["defender_hp_remaining"])
                    )
                    self.send_message(res_msg, self.peer_address)
                    # Wait for host ACK or resolution - simple approach: wait for ACK
                    msg, addr = self.receive_message(timeout=5)
                    if msg and msg.get("message_type") == "ACK":
                        print("[JOINER] Received ACK for resolution. Proceeding.")
                    else:
                        print("[JOINER] No ACK; terminating match.")
                        return

                # Check faint
                if my_poke.get("fainted"):
                    # opponent (host) won
                    go = self.build_message(message_type="GAME_OVER", winner=host_poke.get("name"), loser=my_poke.get("name"))
                    self.send_message(go, self.peer_address)
                    print("[JOINER] You fainted. Sent GAME_OVER to host.")
                    self.battle_state = "GAME_OVER"
                    return

                # Swap roles for next loop
                attacker_is_host = not attacker_is_host

            else:
                # (This block would run if joiner had to act as attacker; not used in host-first model)
                attacker_is_host = not attacker_is_host
    
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
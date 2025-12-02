"""
launcher.py - Launcher menu to choose Host or Joiner
Run this file to get a menu to choose which to run.
"""

import os
import sys
import subprocess
import load_pokemon
from load_pokemon import Pokedex, Pokemon

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print application banner"""
    clear_screen()
    print("\n" + "="*60)
    print("        POKEPROTOCOL LAUNCHER")
    print("="*60)
    print("   Peer-to-Peer Pokémon Battle Protocol")
    print("="*60)


def print_menu():
    """Print main menu"""
    print("\n" + "="*60)
    print("MAIN MENU")
    print("="*60)
    print("[1] Run as HOST (Create a battle)")
    print("    - Players connect to you")
    print("    - You control the battle")
    print()
    print("[2] Run as JOINER (Join a battle)")
    print("    - Connect to someone else's battle")
    print("    - You need their IP address")
    print()
    print("[3] Quick Local Test")
    print("    - Run both host and joiner locally")
    print("    - For testing only")
    print()
    print("[4] View Protocol Documentation")
    print("[5] Exit")
    print("="*60)


def run_host():
    """Run the host application"""
    print("\nStarting Host...")
    print("="*60)
    
    port = input("Enter port to listen on [5000]: ").strip() or "5000"
    
    # Run host_runner.py with port argument
    subprocess.run([sys.executable, "host_runner.py", port])
    
    input("\nPress Enter to return to menu...")


def run_joiner():
    """Run the joiner application"""
    print("\nStarting Joiner...")
    print("="*60)
    print("You need the host's IP address and port.")
    print()
    
    host_ip = input("Enter host IP address: ").strip()
    if not host_ip:
        print("Host IP is required!")
        input("Press Enter to continue...")
        return
    
    port = input(f"Enter host port [5000]: ").strip() or "5000"
    
    # Run joiner_runner.py with arguments
    subprocess.run([sys.executable, "joiner_runner.py", host_ip, port])
    
    input("\nPress Enter to return to menu...")


def run_local_test():
    """Run a local test with both host and joiner"""
    print("\n" + "="*60)
    print("QUICK LOCAL TEST")
    print("="*60)
    print("This will open two terminals:")
    print("1. One for Host (listening on port 5000)")
    print("2. One for Joiner (connecting to localhost)")
    print()
    print("Note: This requires a terminal that supports")
    print("      multiple tabs/windows.")
    print("="*60)
    
    confirm = input("\nStart local test? (y/n): ").strip().lower()
    
    if confirm == 'y':
        print("\nStarting local test...")
        
        import threading
        import time
        
        def run_in_thread(script, *args):
            """Run a script in a thread"""
            cmd = [sys.executable, script] + list(args)
            subprocess.run(cmd)
        
        # Start host in background thread
        host_thread = threading.Thread(target=run_in_thread, args=("host_runner.py", "5000"))
        host_thread.start()
        
        # Give host time to start
        time.sleep(2)
        
        # Start joiner
        joiner_thread = threading.Thread(target=run_in_thread, args=("joiner_runner.py", "127.0.0.1", "5000"))
        joiner_thread.start()
        
        # Wait for threads
        host_thread.join()
        joiner_thread.join()
    
    input("\nPress Enter to return to menu...")


def show_documentation():
    """Show protocol documentation"""
    clear_screen()
    print("\n" + "="*60)
    print("POKEPROTOCOL DOCUMENTATION")
    print("="*60)
    print("\nPROTOCOL OVERVIEW:")
    print("- Uses UDP for low-latency communication")
    print("- Peer-to-Peer architecture")
    print("- Turn-based Pokémon battles")
    print("- Includes text chat with stickers")
    print("- Supports spectators")
    print()
    print("\nGETTING STARTED:")
    print("1. One player runs as HOST")
    print("2. Host shares their IP address and port")
    print("3. Other players run as JOINER with that info")
    print("4. Connect and choose Pokémon")
    print("5. Battle begins!")
    print()
    print("\nMESSAGE TYPES:")
    print("- HANDSHAKE_REQUEST/SPONSE: Initial connection")
    print("- BATTLE_SETUP: Exchange Pokémon data")
    print("- ATTACK_ANNOUNCE: Declare moves")
    print("- CHAT_MESSAGE: Text or stickers")
    print("- GAME_OVER: End battle")
    print()
    print("="*60)
    input("\nPress Enter to return to menu...")

def main():
    """Main launcher function"""
    while True:
        print_banner()
        print_menu()
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            run_host()
        elif choice == "2":
            run_joiner()
        elif choice == "3":
            run_local_test()
        elif choice == "4":
            show_documentation()
        elif choice == "5":
            print("\nThank you for using PokeProtocol!")
            print("Goodbye!\n")
            break
        else:
            print("\nInvalid choice. Please enter 1-5.")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()
MSG_TYPE = {
    # Reliability Layer (Step 7)
    "ACK": "ACK",
    "DISCREPANCY_REPORT": "DISCREPANCY_REPORT",
    "CALC_CONFIRM": "CALC_CONFIRM",

    # Connection & Handshake (Step 2)
    "HANDSHAKE_REQUEST": "HANDSHAKE_REQUEST",
    "HANDSHAKE_RESPONSE": "HANDSHAKE_RESPONSE",
    "SPECTATOR_REQUEST": "SPECTATOR_REQUEST",  # Already in your messages.py

    # Battle Setup (Step 3)
    "BATTLE_SETUP": "BATTLE_SETUP",

    # Turn System (Step 4)
    "ATTACK_ANNOUNCE": "ATTACK_ANNOUNCE",
    "DEFENSE_ANNOUNCE": "DEFENSE_ANNOUNCE",
    "CALCULATION_REPORT": "CALCULATION_REPORT",

    # Chat & Game End (Steps 8 & 9)
    "CHAT": "CHAT",
    "GAME_OVER": "GAME_OVER",
}

# --- Other shared constants (Optional but useful) ---
POKEMON_PORT = 12345
TIMEOUT = 3.0
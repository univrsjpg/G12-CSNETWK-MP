class MessageProtocol:
    @staticmethod
    def format_reliable_message(
            message_type: str,
            seq_num: int,
            ack_num: int,
            **kwargs
    ) -> str:

        # 1. Add reliability headers first
        lines = [
            f"seq_num: {seq_num}",
            f"ack_num: {ack_num}",
            f"message_type: {message_type}"
        ]

        # 2. Add payload data
        for key, value in kwargs.items():
            lines.append(f"{key}: {value}")

        return "\n".join(lines)

    @staticmethod
    def parse_message(message: str) -> dict:
        # NOTE: This parsing logic should be updated to handle types (int/str) 
        # for seq_num, ack_num, and other numeric data like HP or damage.
        result = {}
        for line in message.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        return result

    @staticmethod
    def create_handshake_request(seq_num: int, ack_num: int) -> str:
        return MessageProtocol.format_reliable_message("HANDSHAKE_REQUEST", seq_num, ack_num)

    @staticmethod
    def create_handshake_response(seq_num: int, ack_num: int, seed: int) -> str:
        return MessageProtocol.format_reliable_message("HANDSHAKE_RESPONSE", seq_num, ack_num, seed=seed)

    @staticmethod
    def create_ack(seq_num: int, ack_num: int) -> str:
        """Explicit ACK message (Step 7)"""
        return MessageProtocol.format_reliable_message("ACK", seq_num, ack_num)

    @staticmethod
    def create_battle_setup(seq_num: int, ack_num: int, pokemon_data: dict) -> str:
        """Exchange Pokémon data (Step 3)"""
        # Note: Dictionaries must be serialized (e.g., using json.dumps) before being passed
        # as a string value here, otherwise this simple formatting fails.
        return MessageProtocol.format_reliable_message("BATTLE_SETUP", seq_num, ack_num, **pokemon_data)

    @staticmethod
    def create_attack_announce(seq_num: int, ack_num: int, move_name: str) -> str:
        """Turn system: Attacker's move choice (Step 4)"""
        return MessageProtocol.format_reliable_message("ATTACK_ANNOUNCE", seq_num, ack_num, move=move_name)

    @staticmethod
    def create_calculation_report(seq_num: int, ack_num: int, damage_value: int) -> str:
        """Damage calculation results (Step 4)"""
        return MessageProtocol.format_reliable_message("CALCULATION_REPORT", seq_num, ack_num, damage=damage_value)

    @staticmethod
    def create_chat(seq, ack, text="", sticker_b64=None):
        msg = {
            "seq_num": str(seq),
            "ack_num": str(ack),
            "message_type": "CHAT_MESSAGE",
            "text": text,
        }

        # If sending a sticker, include it
        if sticker_b64:
            msg["sticker"] = sticker_b64

        return MessageProtocol.format_message(msg)


    @staticmethod
    def create_game_over(seq_num: int, ack_num: int, winner_name: str) -> str:
        """Game termination (Step 9)"""
        return MessageProtocol.format_reliable_message("GAME_OVER", seq_num, ack_num, winner=winner_name)
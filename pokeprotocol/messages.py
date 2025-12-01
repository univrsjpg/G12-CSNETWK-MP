class MessageProtocol:
    @staticmethod
    def format_message(message_type: str, **kwargs) -> str:
        lines = [f"message_type: {message_type}"]
        for key, value in kwargs.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    @staticmethod
    def parse_message(message: str) -> dict:
        result = {}
        for line in message.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        return result
    
    @staticmethod
    def create_handshake_request() -> str:
        return MessageProtocol.format_message("HANDSHAKE_REQUEST")
    
    @staticmethod
    def create_handshake_response(seed: int) -> str:
        return MessageProtocol.format_message("HANDSHAKE_RESPONSE", seed=seed)
    
    @staticmethod
    def create_spectator_request() -> str:
        return MessageProtocol.format_message("SPECTATOR_REQUEST")

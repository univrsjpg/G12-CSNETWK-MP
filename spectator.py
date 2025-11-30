import socket
from messages import MessageProtocol


class SpectatorPeer:
    def __init__(self, host_ip: str, host_port: int = 5000):
        self.host_address = (host_ip, host_port)
        self.socket = None
        self.connected = False
        self.seed = None

    def connect(self, timeout: float = 5.0) -> bool:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)

        try:
            request = MessageProtocol.create_spectator_request()
            self.socket.sendto(request.encode('utf-8'), self.host_address)
            print(f"[SPECTATOR] Sent SPECTATOR_REQUEST → {self.host_address}")

            data, address = self.socket.recvfrom(1024)
            parsed = MessageProtocol.parse_message(data.decode('utf-8'))

            if parsed.get("message_type") != "HANDSHAKE_RESPONSE":
                print("[SPECTATOR] Unexpected message type")
                return False

            self.seed = int(parsed["seed"])
            self.connected = True

            print(f"[SPECTATOR] Connected. Seed = {self.seed}")
            return True

        except socket.timeout:
            print("[SPECTATOR] Timeout waiting for host")
            return False

    def close(self):
        if self.socket:
            self.socket.close()
            print("[SPECTATOR] Socket closed")

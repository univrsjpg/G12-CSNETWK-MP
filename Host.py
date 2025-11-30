import socket
import random
from messages import MessageProtocol


class Host:
    def __init__(self, port: int = 5000):
        self.port = port
        self.addr = 'localhost'
        self.socket = None
        self.opponent = set()
        self.spectators = set()
        self.seed = None

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.addr, self.port))
        print(f"[HOST] Listening on port {self.port}")

        self.seed = random.randint(1, 999999)
        print(f"[HOST] Seed generated: {self.seed}")

    def handle_request(self, timeout: float = None):
        if timeout:
            self.socket.settimeout(timeout)

        try:
            data, address = self.socket.recvfrom(1024)
            message = data.decode('utf-8')
            parsed = MessageProtocol.parse_message(message)

            msg_type = parsed.get("message_type")
            if not msg_type:
                print("Error")
                return None

            print(f"[HOST] Received {msg_type} from {address}")

            if msg_type == "HANDSHAKE_REQUEST":
                self._handle_handshake(address)
                return ("JOINER", address, parsed)

            elif msg_type == "SPECTATOR_REQUEST":
                self._handle_spectator(address)
                return ("SPECTATOR", address, parsed)

            else:
                print(f"[HOST] Unknown message type: {msg_type}")
                return None

        except socket.timeout:
            return None

    def _handle_handshake(self, address):
        response = MessageProtocol.create_handshake_response(self.seed)
        self.socket.sendto(response.encode('utf-8'), address)
        self.opponent.add(address)
        print(f"[HOST] Handshake response sent → {address}")

    def _handle_spectator(self, address):
        response = MessageProtocol.create_handshake_response(self.seed)
        self.socket.sendto(response.encode('utf-8'), address)
        self.spectators.add(address)
        print(f"[HOST] Spectator connected → {address}")

    def close(self):
        if self.socket:
            self.socket.close()
            print("[HOST] Socket closed")


def main():
    host = Host(5000)
    host.start()

    print("Waiting for Opponent or Spectator...")
    while True:
        result = host.handle_request()
    


if __name__ == "__main__":
    main()

import socket
import threading
import queue
from messages import MessageProtocol


"""
    This will handle chats / spectators
"""

# Global
MESSAGE_QUEUE = queue.Queue()
CLIENTS = set()
SPECTATORS = set()

BUFFER = 2048
PORT = 9999

class ChatManager:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("localhost", PORT))

    def start(self):
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def receive_loop(self):
        while True:
            try:
                data, addr = self.socket.recvfrom(BUFFER)
                MESSAGE_QUEUE.put((data.decode(), addr))
            except:
                continue

    def broadcast_loop(self):
        while True:
            while not MESSAGE_QUEUE.empty():
                message, addr = MESSAGE_QUEUE.get()

                parsed = MessageProtocol.parse_message(message)
                msg_type = parsed.get("message_type")

                # Register new peers
                if addr not in CLIENTS and addr not in SPECTATORS:
                    if msg_type == "SPECTATOR_REQUEST":
                        SPECTATORS.add(addr)
                        print(f"[HOST] Spectator joined: {addr}")
                    else:
                        CLIENTS.add(addr)
                        print(f"[HOST] Player joined: {addr}")

                # Send message to all peers + spectators
                for peer in CLIENTS | SPECTATORS:
                    self.socket.sendto(message.encode(), peer)

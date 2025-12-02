import socket
import threading
from typing import Tuple, Dict, Set

BUFFER = 2048


class ChatManager:
    """
    Chat server for Host side only.
    Players and spectators DO NOT run this class.

    Joiners/Spectators connect using a simple UDP socket and send messages to HOST.
    Host then broadcasts to all connected peers.
    """

    def __init__(self, host_ip: str, host_port: int = 9999):
        self.host_ip = host_ip
        self.host_port = host_port

        # UDP socket for chat communication
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host_ip, host_port))

        # Track connected users
        self.players: Set[Tuple[str, int]] = set()
        self.spectators: Set[Tuple[str, int]] = set()

        self.running = False
        print(f"[CHAT SERVER] Bound to {host_ip}:{host_port}")

    # -------------------------------------------------------------
    # PUBLIC: Start chat server
    # -------------------------------------------------------------
    def start(self):
        self.running = True

        threading.Thread(target=self._receive_loop, daemon=True).start()
        print("[CHAT SERVER] Listening for messages...")

    # -------------------------------------------------------------
    # RECEIVE RAW MESSAGES FROM CLIENTS
    # -------------------------------------------------------------
    def _receive_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER)
                message = data.decode()

                msg_type, payload = self._parse_message(message)

                # Register new client type
                if msg_type == "REGISTER_PLAYER":
                    self.players.add(addr)
                    print(f"[CHAT] Player joined: {addr}")
                    self._broadcast_system(f"Player {addr} joined the chat.")
                    continue

                elif msg_type == "REGISTER_SPECTATOR":
                    self.spectators.add(addr)
                    print(f"[CHAT] Spectator joined: {addr}")
                    self._broadcast_system(f"Spectator {addr} joined the chat.")
                    continue

                # Normal chat message
                elif msg_type == "CHAT":
                    formatted = f"{payload.get('sender')}: {payload.get('text')}"
                    print(f"[CHAT] {formatted}")
                    self._broadcast_raw(formatted)
                    continue

                # Sticker
                elif msg_type == "STICKER":
                    formatted = f"{payload.get('sender')} sent sticker [{payload.get('id')}]"
                    print(f"[CHAT] {formatted}")
                    self._broadcast_raw(formatted)
                    continue

            except Exception as e:
                print("[CHAT ERROR]", e)

    # -------------------------------------------------------------
    # SEND MESSAGES
    # -------------------------------------------------------------
    def _broadcast_raw(self, text: str):
        """Broadcast raw text string to all clients."""
        packet = text.encode()
        for p in self.players | self.spectators:
            self.socket.sendto(packet, p)

    def _broadcast_system(self, text: str):
        """Send a system-style message."""
        packet = f"SYSTEM: {text}".encode()
        for p in self.players | self.spectators:
            self.socket.sendto(packet, p)

    # -------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------
    @staticmethod
    def _parse_message(raw: str):
        """
        Supported formats:
            CHAT;sender=name;text=hello
            STICKER;sender=name;id=004
            REGISTER_PLAYER
            REGISTER_SPECTATOR
        """
        raw = raw.strip()

        # Simple registration messages
        if raw == "REGISTER_PLAYER":
            return "REGISTER_PLAYER", {}
        if raw == "REGISTER_SPECTATOR":
            return "REGISTER_SPECTATOR", {}

        # Key-value parsing
        try:
            parts = raw.split(";")
            msg_type = parts[0]
            payload = {}

            for part in parts[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    payload[k] = v

            return msg_type, payload
        except:
            return "UNKNOWN", {}

    # -------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------
    def stop(self):
        self.running = False
        self.socket.close()
        print("[CHAT SERVER] Stopped.")

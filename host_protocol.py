# host_protocol.py
import socket
from typing import Tuple, Optional, Any
from messages import MessageProtocol
from base_protocol import PokeProtocolBase


class HostProtocol(PokeProtocolBase):
    """
    Concrete implementation of PokeProtocolBase for the host side.
    Handles handshake and UDP message formatting.
    """

    def __init__(self, port: int):
        super().__init__(port)
        self.socket: Optional[socket.socket] = None

    # -----------------------------------------------------------
    # Required abstract method (not used by HostWorker)
    # -----------------------------------------------------------
    def run(self):
        """
        Dummy implementation because HostWorker controls the loop.
        Required only because PokeProtocolBase marks it abstract.
        """
        pass

    # -----------------------------------------------------------
    # SOCKET CREATION
    # -----------------------------------------------------------
    def create_socket(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            self.socket.settimeout(0.5)
            return True
        except Exception as e:
            print("HostProtocol.create_socket() ERROR:", e)
            self.socket = None
            return False

    # -----------------------------------------------------------
    # SEND MESSAGE (RFC SAFE)
    # -----------------------------------------------------------
    def send_message(self, message: Any, address: Tuple[str, int]) -> bool:
        if not self.socket:
            print("HostProtocol.send_message ERROR: socket is None")
            return False

        try:
            # ↓ do NOT use huge sndbuf (macOS breaks)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65507)

            # dict → RFC
            if isinstance(message, dict):
                message = MessageProtocol.format_message(message)

            # bytes → decode
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="ignore")

            # ensure string
            if not isinstance(message, str):
                message = str(message)

            payload = message.encode("utf-8")
            self.socket.sendto(payload, address)
            return True

        except Exception as e:
            print("HostProtocol SEND ERROR:", e)
            return False

    # -----------------------------------------------------------
    # RECEIVE MESSAGE
    # -----------------------------------------------------------
    def receive_message(self, timeout=0.5):
        if not self.socket:
            return None, None

        try:
            self.socket.settimeout(timeout)
            raw, addr = self.socket.recvfrom(65535)
            return raw, addr

        except socket.timeout:
            return None, None
        except BlockingIOError:
            return None, None
        except Exception:
            return None, None

    # -----------------------------------------------------------
    # CLOSE SOCKET
    # -----------------------------------------------------------
    def close(self):
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.socket = None

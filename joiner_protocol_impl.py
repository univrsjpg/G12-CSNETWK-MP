# joiner_protocol_impl.py
import socket
from typing import Optional, Tuple, Any
from messages import MessageProtocol


class JoinerProtocolImpl:
    """
    Minimal UDP protocol wrapper for Joiner.
    - create_socket(): creates a UDP socket (non-blocking but using timeouts)
    - send_message(message, address): accepts str/dict and sends bytes
    - receive_message(timeout): returns (raw_bytes_or_str, addr) or (None, None)
    - close(): closes socket
    """

    def __init__(self, host_ip: str, host_port: int = 5000):
        self.host_address: Tuple[str, int] = (host_ip, host_port)
        self.peer_address: Optional[Tuple[str, int]] = None
        self.socket: Optional[socket.socket] = None

    def create_socket(self) -> bool:
        try:
            # Bind local ephemeral port so we can receive replies
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            # bind to all interfaces on ephemeral port
            self.socket.bind(('', 0))
            return True
        except Exception:
            self.socket = None
            return False

    def send_message(self, message, address):
        if not self.socket:
            return False
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)

            if isinstance(message, dict):
                message = MessageProtocol.format_message(message)

            if isinstance(message, bytes):
                message = message.decode()

            data = message.encode("utf-8")

            self.socket.sendto(data, address)
            return True

        except Exception as e:
            print("SEND ERROR:", e)
            return False


    def receive_message(self, timeout: float = 0.5):
        """
        Wait up to timeout seconds for a datagram. Returns (raw_bytes, addr)
        or (None, None) on timeout / no data.
        """
        if not self.socket:
            return None, None
        try:
            self.socket.settimeout(timeout)
            raw, addr = self.socket.recvfrom(65535)
            if self.peer_address is None:
                self.peer_address = addr
            return raw, addr
        except socket.timeout:
            return None, None
        except BlockingIOError:
            return None, None
        except Exception:
            return None, None

    def close(self):
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.socket = None

# host_runner.py
from PyQt5.QtCore import QObject, pyqtSignal
import socket
import random
from typing import Optional, Tuple, Dict, Any

from messages import MessageProtocol


class HostWorker(QObject):
    status_update = pyqtSignal(str)
    handshake_complete = pyqtSignal(int)
    message_ready = pyqtSignal(dict)

    def __init__(self, port: int = 5000, message_signal=None):
        super().__init__()
        self.port = port
        self.message_signal = message_signal

        self.socket: Optional[socket.socket] = None

        # state
        self.host_ip: Optional[str] = None
        self.seed: Optional[int] = None
        self.peer_address: Optional[Tuple[str, int]] = None
        self.connected = False
        self.battle_state = "WAITING_FOR_CONNECTION"

        self.gui_message_signal = message_signal

    def _forward_to_gui(self, msg):
        if self.gui_message_signal:
            self.gui_message_signal.emit(msg)

    def setup_host(self):
        """
        Start host listener loop. Blocking; intended to be run from a separate thread.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # allow reuse on dev machines
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.settimeout(1.0)
        except Exception as e:
            self.status_update.emit(f"✗ Failed to create/bind host socket: {e}")
            return

        self.status_update.emit(f"Hosting on port {self.port}. Waiting for a player…")

        while True:
            try:
                try:
                    raw, addr = self.socket.recvfrom(65535)
                except socket.timeout:
                    continue
                except BlockingIOError:
                    continue

                if raw is None:
                    continue

                # decode/parse
                parsed = None
                try:
                    if isinstance(raw, bytes):
                        raw = raw.decode('utf-8', errors='ignore')
                    parsed = MessageProtocol.parse_message(raw) if isinstance(raw, str) else raw
                except Exception as e:
                    self.status_update.emit(f"Malformed incoming message: {e}")
                    continue

                if not parsed:
                    continue

                msg_type = parsed.get("message_type", "").upper().strip()

                if msg_type == "HANDSHAKE_REQUEST":
                    # respond
                    self._handle_handshake_request(addr)
                    continue

                # attach from address and forward to GUI
                parsed["_from_address"] = list(addr)
                # track peer if not set
                if not self.peer_address:
                    self.peer_address = addr
                self.message_ready.emit(parsed)

            except Exception as e:
                self.status_update.emit(f"Host error: {e}")
                break

        # cleanup
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.status_update.emit("Host socket closed.")

    def setup_network(self, ip: Optional[str], port: int):
        """
        Backwards compatible entrypoint; simply starts the host loop.
        """
        self.port = port
        self.setup_host()

    def _handle_handshake_request(self, address: Tuple[str, int]):
        self.peer_address = address
        self.seed = random.randint(1, 999999)

        try:
            # build response via MessageProtocol if available
            try:
                msg = MessageProtocol.create_handshake_response(0, 0, seed=self.seed)
            except Exception:
                # fallback to simple formatted string if helper not available
                msg = f"message_type: HANDSHAKE_RESPONSE\nseed: {self.seed}\n"
            # send
            self.socket.sendto(msg.encode('utf-8') if isinstance(msg, str) else msg, address)

            # inform GUI
            meta = {"message_type": "HANDSHAKE_RESPONSE", "seed": self.seed, "_from_address": list(address)}
            self.message_ready.emit(meta)
            try:
                self.handshake_complete.emit(self.seed)
            except Exception:
                pass

            self.connected = True
            self.battle_state = "PLAYER_CONNECTED"
            self.status_update.emit("Player connected and synced.")
        except Exception as e:
            self.status_update.emit(f"✗ Failed sending handshake response: {e}")

    def send_message(self, message: str, address: Tuple[str, int]) -> bool:
        if not self.socket:
            return False
        try:
            if isinstance(message, dict):
                message = MessageProtocol.format_message(message) if hasattr(MessageProtocol, "format_message") else str(message)
            if isinstance(message, str):
                payload = message.encode('utf-8')
            else:
                payload = message
            self.socket.sendto(payload, address)
            return True
        except Exception:
            return False

    def receive_message(self, timeout=1.0):
        if not self.socket:
            return None, None
        try:
            self.socket.settimeout(timeout)
            raw, addr = self.socket.recvfrom(65535)
            return raw, addr
        except socket.timeout:
            return None, None
        except Exception:
            return None, None

    def close_socket(self):
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.socket = None
        self.status_update.emit("Host socket closed.")

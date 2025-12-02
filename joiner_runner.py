# joiner_runner.py
import time
import threading
from typing import Optional, Tuple, Any
from PyQt5.QtCore import QObject, pyqtSignal

from messages import MessageProtocol
from joiner_protocol_impl import JoinerProtocolImpl


class PokeProtocolJoiner(QObject):
    status_update = pyqtSignal(str)
    handshake_complete = pyqtSignal(int)
    message_ready = pyqtSignal(dict)

    def __init__(self, port: int = 5000, message_signal=None):
        super().__init__()
        self.port = port
        self.gui_message_signal = message_signal
        self.protocol: Optional[JoinerProtocolImpl] = None

        self.host_address: Optional[Tuple[str, int]] = None
        self.peer_address: Optional[Tuple[str, int]] = None
        self.connected = False
        self.seed = None
        self.battle_state = "DISCONNECTED"

        # Forward worker messages → GUI
        self.message_ready.connect(self._forward_to_gui)

        # internal listener thread flag
        self._listener_running = False

    def _forward_to_gui(self, msg):
        if self.gui_message_signal:
            self.gui_message_signal.emit(msg)

    def setup_network(self, ip: str, port: int):
        """
        Called from GUI thread via QThread.started. This sets up the joiner socket,
        performs handshake, and if successful launches listener thread.
        """
        self.host_address = (ip, port)
        self.port = port
        self.protocol = JoinerProtocolImpl(ip, port)

        if not self.protocol.create_socket():
            self.status_update.emit("✗ Failed to create socket (joiner).")
            return

        try:
            ok = self._connect_as_player()
            if ok:
                self.status_update.emit("✓ Connected to host!")

                # store peer address if protocol set it
                if self.protocol and getattr(self.protocol, "peer_address", None):
                    self.peer_address = self.protocol.peer_address

                # start listener loop
                self._listener_running = True
                t = threading.Thread(target=self._listen_loop, daemon=True)
                t.start()
            else:
                self.status_update.emit("✗ Handshake failed / timed out.")
        except Exception as e:
            self.status_update.emit(f"✗ Network error during handshake: {e}")

    def _parse_incoming(self, raw):
        """
        Normalize incoming payload into a dict. Accepts dict / str / bytes.
        Returns dict or None on parse failure.
        """
        try:
            if raw is None:
                return None
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, bytes):
                raw = raw.decode(errors="ignore")
            if isinstance(raw, str):
                # parse_message should return dict
                return MessageProtocol.parse_message(raw)
        except Exception:
            return None
        return None

    def _connect_as_player(self, max_retries: int = 6) -> bool:
        # Build handshake using MessageProtocol
        try:
            handshake_msg = MessageProtocol.create_handshake_request(0, 0)
        except Exception:
            # fallback if method signature different
            handshake_msg = "message_type: HANDSHAKE_REQUEST\n"

        for attempt in range(max_retries):
            self.status_update.emit(f"Attempting handshake ({attempt+1}/{max_retries})...")

            sent = self.protocol.send_message(handshake_msg, self.host_address)
            if sent:
                self.status_update.emit("Handshake request sent.")
                # wait for response
                raw_response, address = self.protocol.receive_message(timeout=2.0)
                response = self._parse_incoming(raw_response)

                if response and response.get("message_type", "").upper() == "HANDSHAKE_RESPONSE":
                    # store seed
                    try:
                        seed_val = int(response.get("seed", 0))
                    except Exception:
                        seed_val = 0

                    self.seed = seed_val
                    self.connected = True
                    self.battle_state = "CONNECTED"

                    # ensure peer address tracked
                    self.protocol.peer_address = address
                    self.peer_address = address

                    # attach metadata for GUI and emit
                    response["_from_address"] = list(address)
                    self.message_ready.emit(response)

                    # emit handshake_complete with seed
                    try:
                        self.handshake_complete.emit(self.seed)
                    except Exception:
                        pass

                    self.status_update.emit(f"Connected! Seed: {self.seed}")
                    return True

                self.status_update.emit("No valid handshake response, retrying...")

            else:
                self.status_update.emit("Failed to send handshake request.")

            time.sleep(1)

        return False

    def _listen_loop(self):
        while self._listener_running:
            try:
                raw_msg, addr = self.protocol.receive_message(timeout=0.25)
                if raw_msg is None:
                    continue

                parsed = self._parse_incoming(raw_msg)
                if not parsed:
                    # could log malformed payload
                    self.status_update.emit("Received malformed message (ignored).")
                    continue

                parsed["_from_address"] = list(addr)
                # update peer_address if not set
                if not self.peer_address:
                    self.peer_address = addr
                self.message_ready.emit(parsed)
            except Exception as exc:
                try:
                    self.status_update.emit(f"Listener error: {exc}")
                except Exception:
                    pass
                continue

    def send_message(self, message: str, address: Tuple[str, int]) -> bool:
        if not self.protocol:
            return False
        try:
            return self.protocol.send_message(message, address)
        except Exception:
            return False

    def receive_message(self, timeout: Optional[float] = None):
        if not self.protocol:
            return None, None
        return self.protocol.receive_message(timeout)

    def close(self):
        self._listener_running = False
        if self.protocol:
            try:
                self.protocol.close()
            except Exception:
                pass
        self.status_update.emit("Joiner socket closed.")

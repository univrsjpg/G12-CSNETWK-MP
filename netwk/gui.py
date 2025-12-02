# gui.py
import sys
import os
import base64
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtWidgets import QFileDialog, QProgressBar

from host_runner import HostWorker
from joiner_runner import PokeProtocolJoiner
from messages import MessageProtocol
from load_pokemon import Pokedex
from battle_system import BattleSystem
from constants import POKEMON_PORT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS = {
    "bg_main": "assets/bg_main.jpg",
    "bg_connect": "assets/bg_connect.jpg",
    "bg_choose": "assets/bg_choose.png",
    "battle_scene": "assets/battle_scene.jpg",
    "pokeball": "assets/pokeball.png",
    "logo": "assets/logo.png",
    "pixel_font": os.path.join(SCRIPT_DIR, "assets", "pixel_font.ttf")
}


def load_pixel_font(path):
    try:
        font_id = QtGui.QFontDatabase.addApplicationFont(path)
        if font_id >= 0:
            families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
    except Exception:
        pass
    return None


class ImageBackgroundWidget(QtWidgets.QWidget):
    def __init__(self, image_path=None, parent=None):
        super().__init__(parent)
        self.pix = QtGui.QPixmap(image_path) if image_path else None
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        if self.pix and not self.pix.isNull():
            scaled = self.pix.scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QtGui.QColor("#1f1f1f"))


class MainWindow(QtWidgets.QMainWindow):
    message_signal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PokeProtocol")
        self.resize(1000, 720)

        pixel_family = load_pixel_font(ASSETS["pixel_font"]) or "Monospace"
        self.pixel_font = QtGui.QFont(pixel_family, 36)
        self.pixel_font_small = QtGui.QFont(pixel_family, 12)

        # Data
        self.pokemon_stats_db = Pokedex()
        self.local_pokemon_name = None
        self.local_pokemon_data = None
        self.opponent_pokemon_name = None
        self.opponent_pokemon_data = None
        self.battle_engine = None
        self.local_battle_pokemon = None
        self.opponent_battle_pokemon = None

        self.sequence_number = 0
        
        # Game
        self.is_my_turn = False
        self.turn_lock = False      # prevents double-turn bugs

        # Network
        self.runner_thread = None
        self.network_runner = None
        self.local_locked_in = False

        # UI stack
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)

        self.message_signal.connect(self.process_battle_message)

        # Screens
        self.screens = {}
        self.screens['main'] = self.create_main_menu()
        self.screens['connect'] = self.create_connect_screen()
        self.screens['choose'] = self.create_choose_pokemon()
        self.screens['battle'] = self.create_battle_screen()
        self.screens['spectate'] = self.create_spectator_screen()

        for screen in ['main', 'connect', 'choose', 'battle', 'spectate']:
            self.stack.addWidget(self.screens[screen])

        self.stack.setCurrentWidget(self.screens['main'])
        self.statusBar().showMessage("Main Menu")

    # ---------- Network helpers ----------
    def next_sequence(self):
        self.sequence_number += 1
        return self.sequence_number

    def get_peer_address(self):
        """Return peer address tuple from network runner if available."""
        if not self.network_runner:
            return None
        addr = getattr(self.network_runner, "peer_address", None)
        if addr:
            return addr
        # joiner stores host_address for target if not connected yet
        addr = getattr(self.network_runner, "host_address", None)
        return addr

    def attach_worker_signals(self, worker):
        """Connect worker signals to GUI handlers (works for HostWorker and Joiner)."""
        try:
            worker.status_update.connect(self.update_status_bar)
        except Exception:
            pass
        try:
            worker.handshake_complete.connect(self.handle_handshake_success)
        except Exception:
            pass
        try:
            worker.message_ready.connect(lambda m: self.message_signal.emit(m))
        except Exception:
            pass

    def start_network_session(self, is_host: bool, ip: str = None, port: int = POKEMON_PORT, role: str = "player"):
        """Create and start HostWorker or PokeProtocolJoiner and wire signals."""
        # create worker
        WorkerClass = HostWorker if is_host else PokeProtocolJoiner
        self.network_runner = WorkerClass(port=port, message_signal=self.message_signal)
        # create thread
        self.runner_thread = QtCore.QThread()
        # move worker
        self.network_runner.moveToThread(self.runner_thread)
        # attach signals
        self.attach_worker_signals(self.network_runner)

        if is_host:
            # Host has a blocking loop method
            self.runner_thread.started.connect(self.network_runner.setup_host)
        else:
            # Joiner needs ip and port
            self.runner_thread.started.connect(lambda: self.network_runner.setup_network(ip, port))

        # start
        self.runner_thread.start()

        # immediate UI
        if role.lower() == "spectator":
            self.switch_to('spectate')
        else:
            self.switch_to('choose')

    # ---------- Message processing ----------
    def append_to_chat_log(self, text: str):
        try:
            if hasattr(self.screens['battle'], 'chat_log'):
                self.screens['battle'].chat_log.append(text)
        except Exception:
            pass
        try:
            if hasattr(self.screens['spectate'], 'chat_log'):
                self.screens['spectate'].chat_log.append(text)
        except Exception:
            pass
        
    def enable_attack_buttons(self, enabled: bool):
        for btn in self.attack_buttons:
            btn.setEnabled(enabled)
            
    def _handle_action_press(self, action):
        if not self.is_my_turn or self.turn_lock:
            self.append_to_chat_log("[WARN] Not your turn!\n")
            return

        self.turn_lock = True
        self.enable_attack_buttons(False)

        seq = self.next_sequence()
        msg = MessageProtocol.create_attack_announce(seq, 0, action)

        peer = self.get_peer_address()
        if peer and self.network_runner:
            ok = self.network_runner.send_message(msg, peer)
            if ok:
                self.append_to_chat_log(f"[OUT] ATTACK_ANNOUNCE: {action} (seq {seq})\n")
            else:
                self.append_to_chat_log("[ERR] Failed sending attack.\n")


    def initialize_battle_engine(self):
        # Create engine if missing
        if not self.battle_engine:
            self.battle_engine = BattleSystem()

        # ---- Build Local Pokémon ----
        if self.local_pokemon_data:
            try:
                raw = (
                    self.local_pokemon_data.to_dict()
                    if hasattr(self.local_pokemon_data, "to_dict")
                    else self.local_pokemon_data
                )
            except Exception:
                raw = self.local_pokemon_data

            self.local_battle_pokemon = self.battle_engine.create_battle_pokemon(raw, {})

        # ---- Build Opponent Pokémon ----
        if self.opponent_pokemon_data:
            try:
                raw_op = (
                    self.opponent_pokemon_data.to_dict()
                    if hasattr(self.opponent_pokemon_data, "to_dict")
                    else self.opponent_pokemon_data
                )
            except Exception:
                raw_op = self.opponent_pokemon_data

            self.opponent_battle_pokemon = self.battle_engine.create_battle_pokemon(raw_op, {})

        # Update UI
        self.update_battle_stats_ui()
        
        actions = ["Attack", "Defend", "Sp. Attack"]

        def make_action_handler(action_name):
            return lambda _, a=action_name: self._announce_attack(a)

        for i, btn in enumerate(self.attack_buttons):
            try:
                btn.clicked.disconnect()
            except Exception:
                pass

            if i < 3:
                btn.setText(actions[i])
                btn.setEnabled(True)
                btn.clicked.connect(make_action_handler(actions[i]))
            else:
                btn.setText("")
                btn.setEnabled(False)

        self.is_my_turn = True
        self.turn_lock = False
        self.enable_attack_buttons(True)

        self.append_to_chat_log("[INIT] Battle engine initialized.\n")
        self.append_to_chat_log("[TURN] Your turn!\n")

    # =======================================================
    #  FIXED GLOBAL ATTACK ANNOUNCE FUNCTION
    #  (MUST BE OUTSIDE initialize_battle_engine!)
    # =======================================================
    def _announce_attack(self, action_name):
        if not self.is_my_turn or self.turn_lock:
            self.append_to_chat_log("[WARN] Not your turn!\n")
            return

        self.turn_lock = True
        self.enable_attack_buttons(False)

        seq = self.next_sequence()
        msg = MessageProtocol.create_attack_announce(seq, 0, action_name)

        peer = self.get_peer_address()
        if peer and self.network_runner:
            ok = self.network_runner.send_message(msg, peer)
            if ok:
                self.append_to_chat_log(f"[OUT] ATTACK_ANNOUNCE ({action_name}, seq {seq})\n")
            else:
                self.append_to_chat_log("[ERR] Failed to send attack\n")
        else:
            self.append_to_chat_log("[ERR] No peer address — cannot send\n")

    def process_battle_message(self, message: dict):
        # -------- Parse message --------
        parsed = message
        if isinstance(message, str):
            parsed = MessageProtocol.parse_message(message)

        msg_type = parsed.get('message_type') or parsed.get('type') or parsed.get('message')
        seq = parsed.get('seq_num') or parsed.get('sequence_number')

        if isinstance(msg_type, bytes):
            msg_type = msg_type.decode()
        if msg_type:
            msg_type = msg_type.strip().upper()

        self.append_to_chat_log(f"[IN] {msg_type} (seq {seq}) -> {parsed}")

        # =====================================================================
        #                           HANDSHAKE RESPONSE
        # =====================================================================
        if msg_type == "HANDSHAKE_RESPONSE":
            try:
                seed_val = int(parsed.get('seed', 0))
            except Exception:
                seed_val = 0

            self.append_to_chat_log(f"[SYSTEM] Handshake OK — Seed = {seed_val}")
            self.battle_engine = BattleSystem(seed=seed_val)

            # Save peer address if provided
            if "_from_address" in parsed and self.network_runner:
                try:
                    self.network_runner.peer_address = tuple(parsed["_from_address"])
                    self.append_to_chat_log(f"[DEBUG] Peer address set -> {self.network_runner.peer_address}")
                except Exception:
                    pass

            return

        # =====================================================================
        #                              BATTLE SETUP
        # =====================================================================
        if msg_type == "BATTLE_SETUP":
            opponent = {
                'name': parsed.get('pokemon_name') or "",
                'hp': int(parsed.get('hp') or parsed.get('max_hp') or 0),
                'attack': int(parsed.get('attack') or 0),
                'defense': int(parsed.get('defense') or 0),
                'special_attack': int(parsed.get('special_attack') or 0),
                'special_defense': int(parsed.get('special_defense') or 0),
                'type1': parsed.get('type1') or "",
                'type2': parsed.get('type2') or ""
            }

            self.opponent_pokemon_name = opponent['name']
            self.opponent_pokemon_data = opponent

            self.append_to_chat_log(f"[LOCK-IN] Opponent selected **{self.opponent_pokemon_name}**")

            if self.local_locked_in:
                self.initialize_battle_engine()
                self.switch_to("battle")
                self.append_to_chat_log("[SYSTEM] Both players ready. Battle begins!")
            else:
                self.append_to_chat_log("[SYSTEM] Opponent ready. Please lock in.")

            return

        # =====================================================================
        #                           ATTACK ANNOUNCE
        # =====================================================================
        if msg_type == "ATTACK_ANNOUNCE":
            move = parsed.get('move') or parsed.get('move_name') or ""

            self.append_to_chat_log(f"[TURN] Opponent used **{move}**!")

            # Opponent attacks you ⇒ calculate damage to *your* Pokémon
            if self.battle_engine and self.opponent_battle_pokemon and self.local_battle_pokemon:
                dmg_result = self.battle_engine.calculate_damage(
                    attacker=self.opponent_battle_pokemon,
                    defender=self.local_battle_pokemon,
                    move_name=move
                )

                reported = int(dmg_result['damage'])
                seq = self.next_sequence()
                msg = MessageProtocol.create_calculation_report(seq, 0, reported)

                peer = self.get_peer_address()
                if peer and self.network_runner:
                    try:
                        ok = self.network_runner.send_message(msg, peer)
                        if ok:
                            self.append_to_chat_log(
                                f"[OUT] Sent CALCULATION_REPORT ({reported} damage)."
                            )
                    except Exception:
                        self.append_to_chat_log("[ERR] Failed sending CALCULATION_REPORT")

            return

        # =====================================================================
        #                        CALCULATION_REPORT RECEIVED
        # =====================================================================
        if msg_type == "CALCULATION_REPORT":

            # ------------------------------
            # Parse reported damage
            # ------------------------------
            try:
                reported_damage = int(parsed.get('damage') or parsed.get('damage_dealt') or 0)
            except Exception:
                reported_damage = 0

            self.append_to_chat_log(f"[INFO] Opponent confirmed {reported_damage} damage.\n")

            # ------------------------------
            # Apply to OPPONENT (because YOU attacked)
            # ------------------------------
            if self.battle_engine and self.opponent_battle_pokemon:

                self.opponent_battle_pokemon = self.battle_engine.apply_damage(
                    self.opponent_battle_pokemon,
                    reported_damage
                )

                self.update_battle_stats_ui()

                hp  = self.opponent_battle_pokemon['current_hp']
                max = self.opponent_battle_pokemon['max_hp']

                self.append_to_chat_log(f"[DAMAGE] Opponent HP: {hp}/{max}\n")

                # ======================================================
                #                  GAME OVER CHECK 
                # ======================================================
                if hp <= 0:
                    winner = self.local_battle_pokemon['name']

                    seq = self.next_sequence()
                    msg = MessageProtocol.create_game_over(seq, 0, winner)

                    peer = self.get_peer_address()
                    if peer and self.network_runner:
                        self.network_runner.send_message(msg, peer)

                    self.append_to_chat_log(f"[GAME OVER] You win! ({winner})\n")
                    QtWidgets.QMessageBox.information(self, "Victory!", f"You win!\n({winner})")

                    self.switch_to("main")
                    return  # <-- IMPORTANT

                # ======================================================
                # Next turn: Opponent's turn
                # ======================================================
                self.is_my_turn = False
                self.turn_lock = False
                self.append_to_chat_log("[TURN] Opponent's turn!\n")

            return


       # =====================================================================
        #                             CHAT + STICKERS
        # =====================================================================
        if msg_type in ("CHAT", "CHAT_MESSAGE"):
            sender = parsed.get("sender_name") or parsed.get("from") or "Peer"
            text = parsed.get("text") or ""

            # unified sticker extraction
            sticker_b64 = (
                parsed.get("sticker") or
                parsed.get("sticker_data") or
                parsed.get("sticker_png") or
                parsed.get("sticker_image") or
                parsed.get("sticker_base64")
            )

            # ---- text ----
            if text:
                self.append_to_chat_log(f"{sender}: {text}\n")

            # ---- sticker ----
            if sticker_b64:
                try:
                    decoded = base64.b64decode(sticker_b64)
                    pix = QtGui.QPixmap()
                    pix.loadFromData(decoded)

                    if pix.isNull():
                        raise ValueError("Sticker decode returned NULL pixmap")

                    popup = QtWidgets.QLabel()
                    popup.setPixmap(
                        pix.scaled(200, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    )
                    popup.setWindowFlags(QtCore.Qt.Tool)
                    popup.setWindowTitle(f"Sticker from {sender}")
                    popup.show()

                    # prevent garbage collection
                    if not hasattr(self, "_sticker_windows"):
                        self._sticker_windows = []
                    self._sticker_windows.append(popup)

                    self.append_to_chat_log(f"[STICKER] Sticker received from {sender}\n")

                except Exception as e:
                    self.append_to_chat_log(f"[ERR] Failed to decode sticker: {e}\n")

            return

        # =====================================================================
        #                             GAME OVER
        # =====================================================================
        if msg_type == "GAME_OVER":
            winner = parsed.get('winner') or parsed.get('winner_name') or "Unknown"
            self.append_to_chat_log(f"[GAME OVER] Winner: **{winner}**")
            QtWidgets.QMessageBox.information(self, "Game Over", f"Winner: {winner}")
            self.switch_to("main")
            return

        # =====================================================================
        #                             DEFAULT
        # =====================================================================
        self.append_to_chat_log(f"[WARN] Unhandled message type: {msg_type}")


    # ---------- UI builders ----------
    def create_logo_widget(self, width=200, height=100, font_size=None):
        logo_label = QtWidgets.QLabel()
        logo_pix = QtGui.QPixmap(ASSETS.get("logo"))
        if not logo_pix.isNull():
            scaled_pix = logo_pix.scaled(width, height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pix)
        else:
            logo_label.setText("LOGO FAILED")
            if font_size:
                logo_label.setFont(QtGui.QFont(self.pixel_font.family(), font_size))
        logo_label.setAlignment(QtCore.Qt.AlignHCenter)
        return logo_label

    def create_main_menu(self):
        widget = ImageBackgroundWidget(ASSETS.get("bg_main"))
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        logo_widget = self.create_logo_widget(width=600, height=300)
        layout.addWidget(logo_widget, alignment=QtCore.Qt.AlignHCenter)
        layout.addSpacing(6)

        btn_pokeball = QtWidgets.QPushButton()
        btn_pokeball.setFixedSize(220, 150)
        icon_pix = QtGui.QPixmap(ASSETS.get("pokeball"))
        if not icon_pix.isNull():
            pokeball_icon = QtGui.QIcon(icon_pix)
            btn_pokeball.setIcon(pokeball_icon)
            btn_pokeball.setIconSize(QtCore.QSize(220, 150))
        btn_pokeball.setStyleSheet("border: none; background: transparent;")
        btn_pokeball.clicked.connect(lambda: self.switch_to('connect'))

        pokeball_layout = QtWidgets.QHBoxLayout()
        pokeball_layout.addStretch()
        pokeball_layout.addWidget(btn_pokeball)
        pokeball_layout.addStretch()
        layout.addLayout(pokeball_layout)

        btn_spectate = QtWidgets.QPushButton("Spectate a Battle")
        btn_spectate.setFixedHeight(36)
        btn_spectate.clicked.connect(lambda: self.switch_to('connect'))
        layout.addWidget(btn_spectate, alignment=QtCore.Qt.AlignHCenter)

        layout.addStretch(1)
        return widget

    def handle_host_click(self):
        port_text = self.host_port_input.text().strip() if hasattr(self, 'host_port_input') else ''
        try:
            host_port = int(port_text)
        except ValueError:
            host_port = POKEMON_PORT
        role = self.role_selector.currentText().split()[0].lower()
        self.start_network_session(is_host=True, port=host_port, role=role)

    def handle_joiner_click(self):
        host_ip = self.joiner_ip_input.text().strip() if hasattr(self, 'joiner_ip_input') else ''
        port_text = self.joiner_port_input.text().strip() if hasattr(self, 'joiner_port_input') else ''
        try:
            host_port = int(port_text)
        except ValueError:
            host_port = POKEMON_PORT
        if not host_ip:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter the Host IP Address.")
            return
        role = self.role_selector.currentText().split()[0].lower()
        self.start_network_session(is_host=False, ip=host_ip, port=host_port, role=role)

    def create_connect_screen(self):
        widget = ImageBackgroundWidget(ASSETS.get("bg_connect"))
        outer = QtWidgets.QVBoxLayout(widget)
        outer.setContentsMargins(20, 12, 20, 12)
        outer.setSpacing(8)

        logo_widget = self.create_logo_widget(width=600, height=300)
        outer.addWidget(logo_widget, alignment=QtCore.Qt.AlignHCenter)

        self.role_selector = QtWidgets.QComboBox()
        self.role_selector.addItems(["Host Player", "Join Player", "Spectator"])
        self.role_selector.currentTextChanged.connect(self._on_role_changed)
        outer.addWidget(self.role_selector, alignment=QtCore.Qt.AlignHCenter)

        form_area = QtWidgets.QWidget()
        form_layout = QtWidgets.QHBoxLayout(form_area)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(18)
        form_layout.addStretch()

        left_box = QtWidgets.QGroupBox("Create / Host")
        left_layout = QtWidgets.QFormLayout()
        left_box.setLayout(left_layout)
        left_box.setFixedWidth(360)

        self.host_nickname_input = QtWidgets.QLineEdit()
        self.host_nickname_input.setPlaceholderText("Your Nickname")
        self.host_ip_input = QtWidgets.QLineEdit()
        self.host_ip_input.setPlaceholderText("Host IP Address (optional)")
        self.host_port_input = QtWidgets.QLineEdit()
        self.host_port_input.setPlaceholderText("Host Port")

        btn_create = QtWidgets.QPushButton("Start Hosting")
        btn_create.clicked.connect(self.handle_host_click)

        left_layout.addRow("Nickname", self.host_nickname_input)
        left_layout.addRow("Host IP Address", self.host_ip_input)
        left_layout.addRow("Host Port (Default: 5000)", self.host_port_input)
        left_layout.addRow("", btn_create)

        right_box = QtWidgets.QGroupBox("Join a Game")
        right_layout = QtWidgets.QFormLayout()
        right_box.setLayout(right_layout)
        right_box.setFixedWidth(360)

        self.joiner_nickname_input = QtWidgets.QLineEdit()
        self.joiner_nickname_input.setPlaceholderText("Your Nickname")
        self.joiner_ip_input = QtWidgets.QLineEdit()
        self.joiner_ip_input.setPlaceholderText("Host IP Address")
        self.joiner_port_input = QtWidgets.QLineEdit()
        self.joiner_port_input.setPlaceholderText("Host Port")

        btn_join = QtWidgets.QPushButton("Join Game")
        btn_join.clicked.connect(self.handle_joiner_click)

        right_layout.addRow("Nickname", self.joiner_nickname_input)
        right_layout.addRow("Host IP Address", self.joiner_ip_input)
        right_layout.addRow("Host Port (Default: 5000)", self.joiner_port_input)
        right_layout.addRow("", btn_join)

        form_layout.addWidget(left_box)
        form_layout.addWidget(right_box)
        form_layout.addStretch()
        outer.addWidget(form_area)
        outer.addStretch()
        self._on_role_changed(self.role_selector.currentText())
        return widget

    def _on_role_changed(self, text):
        is_spectator = text.lower().startswith("spect")
        if hasattr(self, 'joiner_ip_input'):
            self.joiner_ip_input.setEnabled(True)
            self.joiner_port_input.setEnabled(True)
        if hasattr(self, 'host_ip_input'):
            self.host_ip_input.setEnabled(not is_spectator)
            self.host_port_input.setEnabled(not is_spectator)

    def create_choose_pokemon(self):
        container = ImageBackgroundWidget(ASSETS.get("bg_choose"))
        outer_layout = QtWidgets.QVBoxLayout(container)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(10)

        logo_widget = self.create_logo_widget(width=600, height=200)
        outer_layout.addWidget(logo_widget, alignment=QtCore.Qt.AlignHCenter)
        outer_layout.addSpacing(10)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(20)
        row.setContentsMargins(0, 0, 0, 0)
        row.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        outer_layout.addLayout(row)

        panel_style = """
            QFrame { background-color: rgba(255,255,255,0.85); border-radius: 8px; color: black; }
            QLabel { color: black; }
        """

        left_panel = QtWidgets.QFrame()
        left_panel.setStyleSheet(panel_style)
        left_panel.setFixedSize(260, 260)
        left_layout = QtWidgets.QVBoxLayout(left_panel)

        title = QtWidgets.QLabel("Pokémon List")
        title.setFont(QtGui.QFont(self.pixel_font.family(), 14))
        left_layout.addWidget(title)

        poke_list = QtWidgets.QListWidget()
        try:
            items = list(self.pokemon_stats_db.pokedex.index.tolist())
            poke_list.addItems(items)
        except Exception:
            poke_list.addItem("Error loading Pokédex")
        poke_list.setFixedHeight(200)
        left_layout.addWidget(poke_list)

        center_panel = QtWidgets.QFrame()
        center_panel.setStyleSheet(panel_style)
        center_panel.setFixedSize(300, 260)
        center_layout = QtWidgets.QVBoxLayout(center_panel)
        sprite_label = QtWidgets.QLabel()
        sprite_label.setAlignment(QtCore.Qt.AlignCenter)
        sprite_label.setFixedSize(180, 180)
        center_layout.addWidget(sprite_label)

        right_panel = QtWidgets.QFrame()
        right_panel.setStyleSheet(panel_style)
        right_panel.setFixedSize(260, 260)
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        stat_title = QtWidgets.QLabel("Pokémon Stats")
        stat_title.setFont(QtGui.QFont(self.pixel_font.family(), 14))
        right_layout.addWidget(stat_title)

        stat_name = QtWidgets.QLabel("—")
        stat_name.setFont(QtGui.QFont(self.pixel_font.family(), 14))
        right_layout.addWidget(stat_name)

        stats_form = QtWidgets.QFormLayout()
        stats_labels = {
            "type1": QtWidgets.QLabel(""),
            "type2": QtWidgets.QLabel(""),
            "hp": QtWidgets.QLabel(""),
            "attack": QtWidgets.QLabel(""),
            "defense": QtWidgets.QLabel(""),
            "sp_atk": QtWidgets.QLabel(""),
            "sp_def": QtWidgets.QLabel("")
        }
        for lbl in stats_labels.values():
            lbl.setFont(self.pixel_font_small)
        stats_form.addRow("TYPE 1:", stats_labels["type1"])
        stats_form.addRow("TYPE 2:", stats_labels["type2"])
        stats_form.addRow("HP:", stats_labels["hp"])
        stats_form.addRow("ATK:", stats_labels["attack"])
        stats_form.addRow("DEF:", stats_labels["defense"])
        stats_form.addRow("SP.ATK:", stats_labels["sp_atk"])
        stats_form.addRow("SP.DEF:", stats_labels["sp_def"])
        right_layout.addLayout(stats_form)

        boost_layout = QtWidgets.QHBoxLayout()
        sa_label = QtWidgets.QLabel("Sp.Atk Boost")
        sa_label.setFont(self.pixel_font_small)
        sa_spin = QtWidgets.QSpinBox()
        sa_spin.setRange(0, 10)
        sd_label = QtWidgets.QLabel("Sp.Def Boost")
        sd_label.setFont(self.pixel_font_small)
        sd_spin = QtWidgets.QSpinBox()
        sd_spin.setRange(0, 10)
        boost_layout.addWidget(sa_label)
        boost_layout.addWidget(sa_spin)
        boost_layout.addWidget(sd_label)
        boost_layout.addWidget(sd_spin)
        right_layout.addLayout(boost_layout)

        btn_lock = QtWidgets.QPushButton("Lock In")
        btn_lock.setFixedHeight(34)
        btn_lock.setStyleSheet("""
            QPushButton { background-color: black; color: white; border: 2px solid #222; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #333; }
        """)
        right_layout.addWidget(btn_lock)

        row.addWidget(left_panel)
        row.addWidget(center_panel)
        row.addWidget(right_panel)

        def on_select(item):
            name = item.text()
            stat_name.setText(name)
            base_sprite_folder = os.path.join(SCRIPT_DIR, "assets", "sprites")
            potential_files = [f"{name.lower()}.png", f"{name.capitalize()}.png", f"{name}.png"]
            pix = QtGui.QPixmap()
            for filename in potential_files:
                current_path = os.path.join(base_sprite_folder, filename)
                if os.path.exists(current_path):
                    if pix.load(current_path):
                        break
            if pix.isNull():
                try_path = os.path.join(SCRIPT_DIR, "assets", f"{name.lower()}.png")
                if os.path.exists(try_path):
                    pix.load(try_path)
            if pix.isNull():
                sprite_label.clear()
                sprite_label.setText(name + "\n(SPRITE MISSING)")
            else:
                sprite_label.setText("")
                sprite_label.setPixmap(pix.scaled(180, 180, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

            stats = self.pokemon_stats_db.get_pokemon(name)
            if not stats:
                for k in ["type1", "type2", "hp", "attack", "defense", "sp_atk", "sp_def"]:
                    stats_labels[k].setText("")
                self.local_pokemon_name = None
                self.local_pokemon_data = None
                return
            self.local_pokemon_name = name
            self.local_pokemon_data = stats
            raw_t1 = (stats.get("type1") or (stats.get("type", [""])[0] if isinstance(stats.get("type"), list) else stats.get("type", "") or ""))
            stats_labels["type1"].setText("" if raw_t1 is None else str(raw_t1))
            raw_t2 = (stats.get("type2") or (stats.get("type", ["", ""])[1] if isinstance(stats.get("type"), list) else ""))
            stats_labels["type2"].setText("" if raw_t2 is None else str(raw_t2))
            stats_labels["hp"].setText(str(stats.get("hp", "")))
            stats_labels["attack"].setText(str(stats.get("attack", "")))
            stats_labels["defense"].setText(str(stats.get("defense", "")))
            stats_labels["sp_atk"].setText(str(stats.get("sp_atk", stats.get("special_attack", ""))))
            stats_labels["sp_def"].setText(str(stats.get("sp_def", stats.get("special_defense", ""))))

        poke_list.itemClicked.connect(on_select)

        def lock_in():
            if not self.local_pokemon_name or not self.local_pokemon_data:
                QtWidgets.QMessageBox.warning(self, "Lock In", "Please select a Pokémon first.")
                return

            self.local_locked_in = True
            stats = self.local_pokemon_data
            types = stats.get("type", [])
            type1 = types[0] if len(types) > 0 else ""
            type2 = types[1] if len(types) > 1 else ""

            payload = {
                "pokemon_name": self.local_pokemon_name,
                "hp": str(stats.get("hp", 0)),
                "attack": str(stats.get("attack", 0)),
                "defense": str(stats.get("defense", 0)),
                "special_attack": str(stats.get("sp_atk", stats.get("special_attack", 0))),
                "special_defense": str(stats.get("sp_def", stats.get("special_defense", 0))),
                "type1": type1,
                "type2": type2
            }

            boosts = {
                "special_attack_uses": sa_spin.value(),
                "special_defense_uses": sd_spin.value()
            }

            if not self.battle_engine:
                self.battle_engine = BattleSystem()

            self.local_battle_pokemon = self.battle_engine.create_battle_pokemon(stats, boosts)

            peer = self.get_peer_address()
            seq = self.next_sequence()
            try:
                msg = MessageProtocol.create_battle_setup(seq, 0, payload)
            except Exception:
                # fallback raw message
                msg = f"message_type: BATTLE_SETUP\npokemon_name: {self.local_pokemon_name}\n"

            if peer and self.network_runner:
                try:
                    ok = self.network_runner.send_message(msg, peer)
                    if ok:
                        self.append_to_chat_log(f"[OUT] BATTLE_SETUP sent for {self.local_pokemon_name}")
                    else:
                        self.append_to_chat_log("[ERR] Failed to send BATTLE_SETUP.")
                except Exception as e:
                    self.append_to_chat_log(f"[ERR] Exception sending BATTLE_SETUP: {e}")
            else:
                self.append_to_chat_log("[WARN] No peer address — local test mode")

            if self.opponent_pokemon_data:
                self.opponent_battle_pokemon = self.battle_engine.create_battle_pokemon(self.opponent_pokemon_data, {})
                self.update_battle_stats_ui()
                self.switch_to("battle")
            else:
                self.append_to_chat_log("Locked in. Waiting for opponent...")

        btn_lock.clicked.connect(lock_in)

        return container

    def create_battle_screen(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        chat_panel = QtWidgets.QFrame()
        chat_panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        chat_panel.setFixedWidth(320)
        chat_layout = QtWidgets.QVBoxLayout(chat_panel)
        header = QtWidgets.QLabel("Opponent / Connection")
        header.setFont(self.pixel_font_small)
        chat_layout.addWidget(header)

        self.seq_label = QtWidgets.QLabel(f"Seq: {self.sequence_number}")
        chat_layout.addWidget(self.seq_label, alignment=QtCore.Qt.AlignLeft)

        self.chat_log = QtWidgets.QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setPlaceholderText("Chat log")
        chat_layout.addWidget(self.chat_log)

        chat_entry = QtWidgets.QLineEdit()
        chat_entry.setPlaceholderText("Enter your message")
        chat_layout.addWidget(chat_entry)

        btn_sticker = QtWidgets.QPushButton("Send Sticker")
        btn_sticker.clicked.connect(lambda: self._send_sticker_gui(self.chat_log))
        chat_layout.addWidget(btn_sticker)

        def send_chat():
            text = chat_entry.text().strip()
            if not text:
                return
            seq = self.next_sequence()
            try:
                msg = MessageProtocol.create_chat(seq, 0, text, None)
            except Exception:
                msg = f"message_type: CHAT_MESSAGE\nmessage_text: {text}\n"
            peer = self.get_peer_address()
            if peer and self.network_runner:
                ok = False
                try:
                    ok = self.network_runner.send_message(msg, peer)
                except Exception:
                    ok = False
                if ok:
                    self.append_to_chat_log(f"You: {text} (seq {seq})")
                else:
                    self.append_to_chat_log(f"[ERR] Failed to send chat (seq {seq})")
            else:
                self.append_to_chat_log("[ERR] No peer address - cannot send chat")
            chat_entry.clear()

        chat_entry.returnPressed.connect(send_chat)

        center_panel = ImageBackgroundWidget(ASSETS.get("battle_scene"))
        center_layout = QtWidgets.QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)

        stats_frame = QtWidgets.QFrame()
        stats_layout = QtWidgets.QHBoxLayout(stats_frame)

        self.local_stats_group = QtWidgets.QGroupBox("You")
        local_stats_layout = QtWidgets.QVBoxLayout(self.local_stats_group)
        self.local_name_label = QtWidgets.QLabel("—")
        self.local_hp_bar = QProgressBar()
        self.local_hp_bar.setTextVisible(True)
        self.local_atk_label = QtWidgets.QLabel("ATK: -")
        self.local_def_label = QtWidgets.QLabel("DEF: -")
        local_stats_layout.addWidget(self.local_name_label)
        local_stats_layout.addWidget(self.local_hp_bar)
        local_stats_layout.addWidget(self.local_atk_label)
        local_stats_layout.addWidget(self.local_def_label)

        self.opponent_stats_group = QtWidgets.QGroupBox("Opponent")
        opp_stats_layout = QtWidgets.QVBoxLayout(self.opponent_stats_group)
        self.opponent_name_label = QtWidgets.QLabel("—")
        self.opponent_hp_bar = QProgressBar()
        self.opponent_hp_bar.setTextVisible(True)
        self.opponent_atk_label = QtWidgets.QLabel("ATK: -")
        self.opponent_def_label = QtWidgets.QLabel("DEF: -")
        opp_stats_layout.addWidget(self.opponent_name_label)
        opp_stats_layout.addWidget(self.opponent_hp_bar)
        opp_stats_layout.addWidget(self.opponent_atk_label)
        opp_stats_layout.addWidget(self.opponent_def_label)

        stats_layout.addWidget(self.local_stats_group)
        stats_layout.addWidget(self.opponent_stats_group)
        center_layout.addWidget(stats_frame)

        action_panel = QtWidgets.QFrame()
        action_panel.setFixedWidth(220)
        action_layout = QtWidgets.QVBoxLayout(action_panel)
        action_layout.setContentsMargins(8, 8, 8, 8)
        action_layout.addStretch()

        # Replace attack buttons with 3 fixed actions
        self.attack_buttons = []

        actions = ["Attack", "Defend", "Sp. Attack"]

        for action in actions:
            b = QtWidgets.QPushButton(action)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _, a=action: self._handle_action_press(a))
            action_layout.addWidget(b)
            self.attack_buttons.append(b)

        def announce_attack_factory(move_name):
            def f():
                seq = self.next_sequence()
                msg = MessageProtocol.create_attack_announce(seq, 0, move_name)
                peer = self.get_peer_address()
                if peer and self.network_runner:
                    ok = False
                    try:
                        ok = self.network_runner.send_message(msg, peer)
                    except Exception:
                        ok = False
                    if ok:
                        self.append_to_chat_log(f"[OUT] ATTACK_ANNOUNCE: {move_name} (seq {seq})")
                    else:
                        self.append_to_chat_log("[ERR] Failed to send ATTACK_ANNOUNCE")
                else:
                    self.append_to_chat_log("[ERR] No peer address - cannot announce attack")
            return f

        if self.attack_buttons:
            self.attack_buttons[0].setText("Tackle")
            self.attack_buttons[0].clicked.connect(announce_attack_factory("Tackle"))

        action_layout.addStretch()
        layout.addWidget(chat_panel)
        layout.addWidget(center_panel, stretch=1)
        layout.addWidget(action_panel)

        self.screens['battle'] = widget
        self.screens['battle'].chat_log = self.chat_log
        return widget

    def update_battle_stats_ui(self):
        try:
            if self.local_battle_pokemon:
                name = self.local_battle_pokemon.get('name', 'You')
                cur = self.local_battle_pokemon.get('current_hp', 0)
                maxhp = self.local_battle_pokemon.get('max_hp', 1)
                atk = self.local_battle_pokemon.get('attack', 0)
                df = self.local_battle_pokemon.get('defense', 0)
                self.local_name_label.setText(name)
                self.local_hp_bar.setMaximum(maxhp)
                self.local_hp_bar.setValue(cur)
                self.local_hp_bar.setFormat(f"{cur}/{maxhp}")
                self.local_atk_label.setText(f"ATK: {atk}")
                self.local_def_label.setText(f"DEF: {df}")
            if self.opponent_battle_pokemon:
                name = self.opponent_battle_pokemon.get('name', 'Opponent')
                cur = self.opponent_battle_pokemon.get('current_hp', 0)
                maxhp = self.opponent_battle_pokemon.get('max_hp', 1)
                atk = self.opponent_battle_pokemon.get('attack', 0)
                df = self.opponent_battle_pokemon.get('defense', 0)
                self.opponent_name_label.setText(name)
                self.opponent_hp_bar.setMaximum(maxhp)
                self.opponent_hp_bar.setValue(cur)
                self.opponent_hp_bar.setFormat(f"{cur}/{maxhp}")
                self.opponent_atk_label.setText(f"ATK: {atk}")
                self.opponent_def_label.setText(f"DEF: {df}")
        except Exception:
            pass

    def _send_sticker_gui(self, chat_log_widget):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choose Sticker", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return

        pix = QtGui.QPixmap(file_path)
        if pix.isNull():
            chat_log_widget.append("[ERR] Sticker image failed to load.\n")
            return

        # resize + encode as PNG bytes
        pix_resized = pix.scaled(256, 256, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pix_resized.save(buffer, "PNG")

        raw = bytes(buffer.data())
        sticker_b64 = base64.b64encode(raw).decode()

        seq = self.next_sequence()

        # ⭐ IMPORTANT: always use "sticker" as key
        msg = {
            "message_type": "CHAT",
            "seq_num": str(seq),
            "ack_num": "0",
            "text": "",
            "sticker": sticker_b64
        }

        peer = self.get_peer_address()
        ok = self.network_runner.send_message(msg, peer)

        if ok:
            chat_log_widget.append(f"[OUT] Sticker sent (seq {seq})\n")
        else:
            chat_log_widget.append("[ERR] Sticker failed to send\n")


    def create_spectator_screen(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        header = QtWidgets.QLabel("Spectating Battle")
        header.setFont(self.pixel_font_small)
        layout.addWidget(header)
        self.spectate_chat_log = QtWidgets.QTextEdit()
        self.spectate_chat_log.setReadOnly(True)
        layout.addWidget(self.spectate_chat_log)
        chat_entry = QtWidgets.QLineEdit()
        chat_entry.setPlaceholderText("Send a chat (spectators allowed)")
        layout.addWidget(chat_entry)
        btn_sticker = QtWidgets.QPushButton("Send Sticker")
        btn_sticker.clicked.connect(lambda: self._send_sticker_gui(self.spectate_chat_log))
        layout.addWidget(btn_sticker, alignment=QtCore.Qt.AlignLeft)

        def send_spec_chat():
            text = chat_entry.text().strip()
            if not text:
                return
            seq = self.next_sequence()
            msg = MessageProtocol.create_chat(seq, 0, text, None)
            peer = self.get_peer_address()
            if peer and self.network_runner:
                try:
                    ok = self.network_runner.send_message(msg, peer)
                    if ok:
                        self.spectate_chat_log.append(f"You: {text} (seq {seq})")
                    else:
                        self.spectate_chat_log.append("[ERR] Failed to send spectator chat")
                except Exception:
                    self.spectate_chat_log.append("[ERR] Exception sending spectator chat")
            else:
                self.spectate_chat_log.append("[ERR] No peer address - cannot send chat")
            chat_entry.clear()

        chat_entry.returnPressed.connect(send_spec_chat)
        self.screens['spectate'] = widget
        self.screens['spectate'].chat_log = self.spectate_chat_log
        return widget

    # Utility
    def switch_to(self, name):
        if name in self.screens:
            self.stack.setCurrentWidget(self.screens[name])
            self.statusBar().showMessage(name.capitalize().replace('_', ' ') + " Screen")
            if name == 'battle':
                self.update_battle_stats_ui()

    def update_status_bar(self, text):
        try:
            self.statusBar().showMessage(str(text))
            self.append_to_chat_log(f"[STATUS] {text}")
        except Exception:
            pass

    def handle_handshake_success(self, payload):
        try:
            seed = payload if isinstance(payload, int) else (payload.get('seed') if isinstance(payload, dict) else None)
            self.update_status_bar(f"Handshake complete (seed {seed})")
            self.append_to_chat_log(f"Handshake complete (seed {seed})")
            if isinstance(payload, dict) and "_from_address" in payload:
                try:
                    self.network_runner.peer_address = tuple(payload["_from_address"])
                    self.append_to_chat_log(f"[DEBUG] Peer address updated to {self.network_runner.peer_address}")
                except Exception:
                    pass
            try:
                seed_val = int(seed) if seed else None
                self.battle_engine = BattleSystem(seed=seed_val)
            except Exception:
                self.battle_engine = BattleSystem()
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif event.key() == QtCore.Qt.Key_1:
            self.switch_to('main')
        elif event.key() == QtCore.Qt.Key_2:
            self.switch_to('connect')
        elif event.key() == QtCore.Qt.Key_3:
            self.switch_to('choose')
        elif event.key() == QtCore.Qt.Key_4:
            self.switch_to('battle')
        elif event.key() == QtCore.Qt.Key_5:
            self.switch_to('spectate')
        else:
            super().keyPressEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

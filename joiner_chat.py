import socket
import threading
from messages import MessageProtocol

class PeerChat:
    def __init__(self, name):
        self.name = name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("localhost", 0))  # random port assigned
        
        threading.Thread(target=self.listen_loop, daemon=True).start()

    def listen_loop(self):
        while True:
            try:
                data, _ = self.socket.recvfrom(2048)
                print(data.decode())
            except:
                continue

    def send_chat(self, text):
        msg = MessageProtocol.format_message(
            "CHAT_MESSAGE",
            sender_name=self.name,
            content_type="TEXT",
            message_text=text,
            sequence_number=1
        )
        self.socket.sendto(msg.encode(), ("localhost", 9999))

"""
base_protocol.py - Shared base class for PokeProtocol
"""

import socket
import json
from typing import Optional, Tuple, Dict
from abc import ABC, abstractmethod


class PokeProtocolBase(ABC):
    """Base class for PokeProtocol with common functionality"""
    
    def __init__(self, port: int = 5000):
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.sequence_number = 0
        self.peer_address: Optional[Tuple[str, int]] = None
        
    def create_socket(self) -> bool:
        """Create and configure UDP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return True
        except Exception as e:
            print(f"Failed to create socket: {e}")
            return False
    
    def parse_message(self, data: bytes) -> Dict[str, str]:
        """Parse key:value message format"""
        message = {}
        try:
            text = data.decode('utf-8').strip()
            lines = text.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    message[key.strip()] = value.strip()
        except Exception as e:
            print(f"Failed to parse message: {e}")
        return message
    
    def build_message(self, message_type: str, **kwargs) -> str:
        """Build message in key:value format"""
        lines = [f"message_type: {message_type}"]
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, dict):
                    value = json.dumps(value)
                lines.append(f"{key}: {value}")
        return '\n'.join(lines)
    
    def send_message(self, message: str, address: Tuple[str, int]) -> bool:
        """Send message to specific address"""
        try:
            self.socket.sendto(message.encode('utf-8'), address)
            return True
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
    
    def receive_message(self, timeout: Optional[float] = None) -> Tuple[Optional[Dict[str, str]], Optional[Tuple[str, int]]]:
        """Receive and parse a message"""
        if timeout:
            self.socket.settimeout(timeout)
        
        try:
            data, address = self.socket.recvfrom(1024)
            message = self.parse_message(data)
            return message, address
        except socket.timeout:
            return None, None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None, None
    
    def generate_sequence_number(self) -> int:
        """Generate a new sequence number"""
        self.sequence_number += 1
        return self.sequence_number
    
    def close(self):
        """Close the socket"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Socket closed")
    
    @abstractmethod
    def run(self):
        """Main runner method to be implemented by subclasses"""
        pass
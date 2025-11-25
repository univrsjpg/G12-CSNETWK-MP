
from socket import *

serverName = "127.0.0.1"
serverPort = 6767
clientName = "Client of Group 12"

# TCP Socket
clientSocket = socket(AF_INET, SOCK_STREAM)
print("[INFO] Client socket created successfully.")

# Connecting to server
clientSocket.connect((serverName,serverPort))
print(f"[INFO] {clientName} connected to server at {serverName}:{serverPort}")

reply_to_server = input("Address: ")

# Send to server
message = f"{clientName}: {reply_to_server}"
print(f"[INFO] Sending message {message} to server.")
clientSocket.send(message.encode())
    
# Server's reply
reply = clientSocket.recv(1024).decode()
print(f"{reply} from server")

clientSocket.close()
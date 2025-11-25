from socket import *
import random
import csv
import pandas as pd
import string 


HOST = "127.0.0.1"
PORT = 6767

server_name = "Pokemon Battle"
pokemon_pd = pd.read_csv('pokemon.csv') #accesses the pokemon.csv
#print(pokemon_pd.info())

# Create TCP Socket
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind((HOST,PORT))
serverSocket.listen(1)



GameOver = True

while GameOver:
    connectionSocket, address = serverSocket.accept()
    
    print(f"Welcome to Pokemon Battle\nEnter {address} to start") # printed to server side

    data = connectionSocket.recv(1024).decode() #will receive data from client side
    print(f"Message from client: {data}")

    reply = f"\n {pokemon_pd.head()} examples"
    connectionSocket.send(reply.encode()) # to client side

    connectionSocket.close() #closes connection to the client
    GameOver = False #Closes connection to the server



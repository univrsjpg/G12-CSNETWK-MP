# This is a trial
# This is based on https://www.youtube.com/watch?v=3qlhbez-RPI&t=828s 

from socket import *
import random
import csv
import pandas as pd
import string 
import socket,threading,queue

messages = queue.Queue()
clients = []

server_name = "Pokemon Battle"
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pokemon_pd = pd.read_csv('pokemon.csv') #accesses the pokemon.csv and ignore this
server.bind(("192.168.1.3",9999))

def receive():
    while True:
        try:
            message,addr = server.recvfrom(1024)
            messages.put((message,addr))
        except:
            pass

def broadcast():
    while True:
        while not messages.empty():
            message, addr = messages.get()
            print(message.decode())
            if addr not in clients:
                clients.append(addr)
            for client in clients:
                try:
                    if message.decode().startswith("SIGNUP_TAG:"):
                        name = message.decode()[message.decode().index(":")+1:]
                        server.sendto(f"{name} joined!".encode(), client)
                    else:
                        server.sendto(message, client)
                except: 
                    clients.remove(client)
t1 = threading.Thread(target=receive)
t2 = threading.Thread(target=broadcast)

t1.start()
t2.start()




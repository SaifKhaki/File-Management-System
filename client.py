import socket

ClientMultiSocket = socket.socket()
host = input("Specify server's IP address: ")
port = 2051
username = input("Input your username: ")
print('Waiting for connection response')
try:
    ClientMultiSocket.connect((host, port))
except socket.error as e:
    print(str(e))

res = ClientMultiSocket.recv(1024)
print(res.decode('utf-8'))
while True:
    Input = input('>>>> ')
    ClientMultiSocket.send(str.encode(Input))
    if Input == "4":
        break
    res = ClientMultiSocket.recv(1024)
    print(res.decode('utf-8'))

ClientMultiSocket.close()
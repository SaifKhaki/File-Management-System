import socket
import os
from _thread import *
import sys
import json
import math
import time
import threading

ServerSideSocket = socket.socket()
host = socket.gethostname()
print("The server's IP addres is (add this to the client's input): ", socket.gethostbyname(host))
port = 2051
ThreadCount = 0
try:
    ServerSideSocket.bind((host, port))
except socket.error as e:
    print(str(e))
print('Socket is listening..')
ServerSideSocket.listen(5)

#ititializing system
ram = {}
EXTRA_STRING_SIZE = 49
pageSize = 10
pageTotal = 1000
loop = 1
clientId = -1
heirarchy = json.load(open('/home/saifbinkhaki/Desktop/OS lab 12/ram.json'))
ram['root'] = heirarchy['root']
ram['data'] = heirarchy['data']
currentLocation = []
data = heirarchy['data']
nullIndex = [i for i in range(len(data)) if data[i] == ""]
rwl = {}


class rwlock:
    def __init__(self):
        self.rwlock = 0
        self.writers_waiting = 0
        self.monitor = threading.Lock()
        self.readers_ok = threading.Condition(self.monitor)
        self.writers_ok = threading.Condition(self.monitor)
    
    def rlock(self):
        self.monitor.acquire()
        while self.rwlock < 0 or self.writers_waiting:
            self.readers_ok.wait()
        self.rwlock += 1
        self.monitor.release()

    def wlock(self):
        self.monitor.acquire()
        while self.rwlock != 0:
            self.writers_waiting += 1
            self.writers_ok.wait()
            self.writers_waiting -= 1
        self.rwlock = -1
        self.monitor.release()

    def release(self):
        self.monitor.acquire()
        if self.rwlock < 0:
            self.rwlock = 0
        else:
            self.rwlock -= 1
        wake_writers = self.writers_waiting and self.rwlock == 0
        wake_readers = self.writers_waiting == 0
        self.monitor.release()
        if wake_writers:
            self.writers_ok.acquire()
            self.writers_ok.notify()
            self.writers_ok.release()
        elif wake_readers:
            self.readers_ok.acquire()
            self.readers_ok.notifyAll()
            self.readers_ok.release()

for key, value in ram['root'].items():
    if type(value) is dict:
        pass
    else:
        rwl[key] = rwlock()
    
def fre_write(file, newstring, start, connection, id):
    page_index = math.floor(start/pageSize)
    offset = start%pageSize
    if offset!=0:
        oldstring = ram['data'][currentLocation[id][file][page_index]]
        newstring = oldstring[:offset] + newstring + oldstring[offset:]
        ram['data'][currentLocation[id][file][page_index]] = ""
        nullIndex.append(currentLocation[id][file][page_index])
        currentLocation[id][file].remove(currentLocation[id][file][page_index])
        
    if(len(data) + (math.ceil(len(newstring)/pageSize)) <= pageTotal):
        for i in range(0,len(newstring),pageSize):
            currentLocation[id][file][page_index:page_index] = [len(data)]
            start = len(currentLocation[id][file])
            if i+pageSize < len(newstring):
                data.append(newstring[i:i+pageSize])
            else:
                data.append(newstring[i:len(newstring)])
            page_index = page_index + 1
        return ""
    else:
        if(len(nullIndex) < (math.ceil(len(newstring)/pageSize))):
            for i in range(0,len(newstring),pageSize):
                for j in nullIndex:
                    data[j]=i
                    currentLocation[id][file][start:start] = [data.index(j)]
            return ""
        else:
            return "Running out of memory"      
#write a file
def fwrite(file, start, connection, id):
    connection.send(str.encode("Write your new string: "))
    newstring = connection.recv(2048).decode('utf-8')
    return_str = ""
    if(start == -1):
        length_file = 0
        for i in currentLocation[id][file]:
            length_file = length_file + len(data[i])
        return_str += fre_write(file, newstring, length_file, connection, id)
    else:        
        return_str += fre_write(file, newstring, start, connection, id)
    return return_str
def fread(filePages, start, connection):
    send_str = ""
    send_str += "\n\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ MS WORD \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\n"
    send_str += ram['data'][filePages[math.floor(start/pageSize)]][start:]
    for i in range(math.floor(start/pageSize)+1, len(filePages)):
        send_str += ram['data'][filePages[i]]
    send_str += "\n\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\n"
    return send_str    
#read a file
#start is the index where you want to start reading, but our program reads the complete page in which the start index resides.
def fopen(file, start, connection, id):
    filePages = currentLocation[id][file]    
    writeAccess = 1
    send_str = ""
    while(writeAccess):
        rwl[file].acquire_read()
        send_str += fread(filePages, start, connection)
        rwl[file].release()
        connection.send(str.encode(send_str + "Do you want to write this file? Press 1 to start writing, 0 to close the file: "))
        send_str = ""
        writeAccess = int(connection.recv(2048).decode('utf-8'))
        if writeAccess==0:
            break
        elif writeAccess==1:
            rwl[file].acquire_write()
            connection.send(str.encode("Start index from where you want to write (to write on end, enter -1): "))
            start_write = int(connection.recv(2048).decode('utf-8'))
            send_str += fwrite(file, start_write, connection, id)
            rwl[file].release()
    return send_str
#make directory
def mkdir(name, id):
    if(name in currentLocation[id].keys()):
        return "Folder already exists."
    currentLocation[id][name] = {}
    return ""
#navigate through file system
def cd(folder, id):
    global currentLocation
    if folder=="..":
        currentLocation[id] = ram['root']
        return ""
    currentLocation[id] = currentLocation[id][folder]
    return ""
def fdel(file, connection, id):
    connection.send(str.encode("Confirm do you want to delete? Press 1 to confirm, 0 to abort."))    
    confirmation = connection.recv(2048).decode('utf-8')
    return_str = ""
    if(confirmation):
        filePages = currentLocation[id][file]
        del currentLocation[id][file]
        rwl[file].acquire_write()
        for i in filePages:
            data[i] = ""
            nullIndex.append(i)
        rwl[file].release()
        return_str += "Deleted succesfully."
    return return_str
def fmove(file, connection, id):
    fromLocation = currentLocation[id]
    cd("..", id)
    return_str = ""
    destination = "2"
    while(destination):
        connection.send(str.encode("Go to the directory you want the "+ file + " to move, and press 1. To abort moving files, press 0.\n" + see_heirarchy(connection, id)))
        destination = connection.recv(2048).decode('utf-8')
        if destination == "0":
            destination = 0
            return_str += "Moving folder aborted. The folder is at its original location."
        elif destination == "1":
            currentLocation[id].update({file:fromLocation[file]})
            rwl[file].acquire_write()
            del fromLocation[file]
            rwl[file].release()
            destination = 0
            return_str += "File moved successfully."
        else:
            cd(destination, id)
    return return_str
#create a file
def create(file, content, connection, id):
    if(file in currentLocation[id].keys()):
        return "File already exists."

    rwl[file] = rwlock()
    print(rwl)
    if(len(data) + (math.ceil(len(content)/pageSize)) <= pageTotal):
        currentLocation[id][file] = []
        rwl[file].acquire_write()
        for i in range(0,len(content),pageSize):
            currentLocation[id][file].append(len(data))
            if i+pageSize < len(content):
                data.append(content[i:i+pageSize])
            else:
                data.append(content[i:len(content)])
        rwl[file].release()
        return ""
    elif(len(nullIndex) > (math.ceil(len(content)/pageSize))):
        currentLocation[id][file] = []
        rwl[file].acquire_write()
        for i in range(0,len(content),pageSize):
            data[nullIndex[0]]=content[i:i+pageSize]
            currentLocation[id][file].append(nullIndex[0])
            del nullIndex[0]
        rwl[file].release()            
        return ""
    else:
        return "___________________________________\n Alert: Running out of memory\n___________________________________"
def see_heirarchy(connection, id):
    return_str = "\n\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ File Explorer \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\n"
    for key in currentLocation[id].keys():
        return_str += key + "\n"
    return_str += "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\n"
    return return_str
def multi_threaded_client(connection, id):
    send_str = ""
    while True:
        connection.send(str.encode(send_str + see_heirarchy(connection, id) + "Select operation: \n1. Make a directory \n2. Make a file\n3. Move through files using 'cd command'\n4. To quit\n5. Read any file\n6. Delete any file\n7. Move a file or folder.\n8. See memory map.\n"))
        option = connection.recv(2048).decode('utf-8')
        send_str = ""
        if option == "1":
            connection.send(str.encode("Write the directory name: "))
            dirName = connection.recv(2048).decode('utf-8')
            send_str += mkdir(dirName, id)
        elif option == "2":
            connection.send(str.encode("Write the file name with required extension: "))
            file = connection.recv(2048).decode('utf-8')
            connection.send(str.encode("Write the content of the file: "))
            fileContent = connection.recv(2048).decode('utf-8')
            send_str += create(file, fileContent, connection, id)
        elif option == "3":
            connection.send(str.encode("Write folder name to move to that folder or .. to move to the root directory: "))
            folderName = connection.recv(2048).decode('utf-8')
            send_str += cd(folderName, id)
        elif option == "4":
            break
        elif option =="5":
            start = 0
            connection.send(str.encode("Write the file name you want to read: "))
            file = connection.recv(2048).decode('utf-8')
            connection.send(str.encode("Start index from where you want to read (to read from start, write 0): "))
            start = int(connection.recv(2048).decode('utf-8'))
            send_str += fopen(file, start, connection, id)
        elif option == "6":
            connection.send(str.encode("Write the file name you want to delete: "))
            file = connection.recv(2048).decode('utf-8')
            send_str += fdel(file, connection, id)
        elif option == "7":
            connection.send(str.encode("Write the folder/file name you want to move: "))
            name = connection.recv(2048).decode('utf-8')
            send_str += fmove(name, connection, id)
        elif option == "8":
            for i in range(len(data)):
                rwl[file].acquire_read()
                
                return_str += i + ". " + data[i]    
                rwl[file].release()
            connection.send(str.encode(return_str))
        else:
            connection.send(str.encode("\nInvalid Input."))
    #adding the data memory to my ram
    rwl[file].acquire_write()
    ram['data'] = data
    rwl[file].release()
    
    #dump to json
    jsonObj = json.dumps(ram)
    #write to json file
    with open('/home/saifbinkhaki/Desktop/OS lab 12/ram.json','w') as file:
        file.write(jsonObj)
        file.close
    connection.close()
    
while True:
    Client, address = ServerSideSocket.accept()
    print('Connected to: ' + address[0] + ':' + str(address[1]))
    currentLocation.append(ram['root'])
    clientId += 1
    start_new_thread(multi_threaded_client, (Client, clientId))
    ThreadCount += 1
    print('Thread Number: ' + str(ThreadCount))
ServerSideSocket.close()
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))

ip = s.getsockname()[0]
port = 56056
client_id = "-BC0012-3456abcde123"

s.close()
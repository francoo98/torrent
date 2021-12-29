import bencodepy
from hashlib import sha1
import requests
import pprint

def get_torrent_hash():
    torrent_file_path = "./xubuntu-20.04.3-desktop-amd64.iso.torrent"
    buffer = bytes()
    with open(torrent_file_path, "rb") as file:
        buffer = file.read(300)
        index = buffer.find(b"4:infod")
        file.seek(index + 6)
        buffer = file.read()
        a = sha1(buffer[:-1]).digest()
    return a

torrent_file_path = "./xubuntu-20.04.3-desktop-amd64.iso.torrent"
torrent_file = open(torrent_file_path, "rb")

data = bencodepy.bread(torrent_file)
data["announce"] = data.pop(b"announce")
data["comment"] = data.pop(b"comment")
data["created by"] = data.pop(b"created by")
data["creation date"] = data.pop(b"creation date")
data["info"] = data.pop(b"info")
data["info"]["length"] = data["info"].pop(b"length")
data["info"]["name"] = data["info"].pop(b"name")
data["info"]["piece length"] =  data["info"].pop(b"piece length")
data["info"]["pieces"] = data["info"].pop(b"pieces")

#print(list(data))
#print(list(data["info"]))
a = bytearray(str(data["info"]), "UTF-8")
get_params = {}
get_params["info_hash"] = get_torrent_hash()
get_params["peer_id"] = "123f5678x987654321ab"
get_params["port"] = 6881
get_params["downloaded"] = 0
get_params["uploaded"] = 0
get_params["left"] = 1791655936

#b = bytearray(str(data[b"info"]), "UTF-8")
#print(sha1(b).hexdigest())
r = requests.get(data["announce"], params=get_params)
#pprint.pprint(r.content)
pprint.pprint(bencodepy.bdecode(r.content))
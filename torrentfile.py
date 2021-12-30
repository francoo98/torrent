from hashlib import sha1
from requests import get
from pprint import pprint
import bencodepy
import socket


class TorrentFile():

    def __init__(self, file_path: str):
        # self.file_path = file_path
        # decode file and calculate hash
        with open(file_path, "rb") as file:
            buffer = file.read()
            self.meta_data = bencodepy.decode(buffer)
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()
        # request peers from the tracker
        get_params = {
            "info_hash": self.info_hash,
            "peer_id": "-ZK0012-3456abcde123",
            "port": 55556,
            "downloaded": 0,
            "uploaded": 0,
            "left": self.meta_data[b"info"][b"length"]
        }
        self.peers = bencodepy.bdecode(get(self.meta_data[b"announce"], get_params).content)


if __name__ == "__main__":
    id = "-ZK0012-3456abcde123"
    a = TorrentFile("./xubuntu-20.04.3-desktop-amd64.iso.torrent")
    #handshake = b"19BitTorrent protocol\0\0\0\0\0\0\0\0"+a.info_hash+bytes(id, "UTF-8")
    handshake = (19).to_bytes(1, "big") + b"BitTorrent protocol\0\0\0\0\0\0\0\0"+a.info_hash+bytes(id, "utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("172.21.184.95", 55556))
    s.connect((a.peers[b"peers"][0][b"ip"], a.peers[b"peers"][0][b"port"]))
    s.send(handshake)
    print(s.recv(100))
    
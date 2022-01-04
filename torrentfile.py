from hashlib import sha1
from requests import get, Timeout
from pprint import pprint
from math import ceil
from time import sleep
import bencodepy
import socket
#from urllib import urlparse
import requests
import logging

id = "-BC0012-3456abcde123"
local_addr = ("172.28.240.197", 55557)

class TorrentFile():

    def __init__(self, file_path: str):
        # self.file_path = file_path
        # decode file and calculate hash
        with open(file_path, "rb") as file:
            buffer = file.read()
            self.meta_data = bencodepy.decode(buffer)
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()
            self.downloading_file = open("./file", "wb")
        self.peers = self.request_peers()
        for peer in self.peers[b"peers"]:
            peer[b"am_choking"] = 1
            peer[b"am_interested"] = 0
            peer[b"peer_choking"] = 1
            peer[b"peer_interested"] = 0
        print(self.peers)

    def share(self):
        handshake = (19).to_bytes(1, "big") + b"BitTorrent protocol\0\0\0\0\0\0\0\0"+self.info_hash+bytes(id, "utf-8")
        unchoke = (1).to_bytes(4, "big") + (1).to_bytes(1, "big")
        interested = (1).to_bytes(4, "big") + (2).to_bytes(1, "big")
        request = (13).to_bytes(4, "big") + (6).to_bytes(1, "big") + (255).to_bytes(1, "big") + (0).to_bytes(1, "big") + (16).to_bytes(1, "big")

        peer_socket = socket.socket()
        peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_socket.bind(("172.19.182.254", 55556))
        peer_socket.connect((self.peers[b"peers"][0][b"ip"], self.peers[b"peers"][0][b"port"]))
        peer_socket.send(handshake)
        print(peer_socket.recv(68))
        peer_socket.send(interested)
        peer_socket.send(unchoke)
        amount_of_pieces = ceil(self.meta_data[b"info"][b"length"] / self.meta_data[b"info"][b"piece length"])
        for i in range(10):
            request = (13).to_bytes(4, "big") + (6).to_bytes(1, "big") + (i).to_bytes(4, "big") + (0).to_bytes(4, "big") + (16).to_bytes(4, "big")
            peer_socket.send(request)
            ans = peer_socket.recv(16000)
            print(ans[0:20])
            self.downloading_file.write(ans[12:])
        self.downloading_file.close()

    def request_peers(self):
        trackers_list = []
        peers = []
        trackers_list.append(self.meta_data[b"announce"])
        try:
            trackers_list = [tracker.pop() for tracker in self.meta_data[b"announce-list"]]
        except KeyError as err:
            logging.info(str(err.args[0], "utf-8") + "not found in meta_data")
        
        for tracker in trackers_list:
            if b"udp" in tracker:
                self.request_peers_udp()
            else:
                peers = self.request_peers_http(tracker)
        return peers

    def request_peers_http(self, tracker):
        get_params = {
            "info_hash": self.info_hash,
            "peer_id": bytes(id, "utf-8"),
            "port": local_addr[1],
            "downloaded": 0,
            "uploaded": 0,
            "left": self.meta_data[b"info"][b"length"]
        }
        try:
            return bencodepy.bdecode(get(tracker, get_params, timeout=0.5).content)
        except Timeout:
            logging.info(str(tracker, "utf-8") + "timed out")

    


if __name__ == "__main__":
    a = TorrentFile("Introducing Data Science - Big Data, Machine Learning and more, using Python tools (2016).pdf Gooner-[rarbg.to].torrent")
    # a.share()
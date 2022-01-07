import bencodepy
import socket
import logging
from hashlib import sha1
from pprint import pprint
from math import ceil
from trackers import UDPTracker, HTTPTracker

class TorrentMetaData():

    def __init__(self, file_path: str):
        with open(file_path, "rb") as file:
            """ Class atributes """
            self.trackers = []
            self.info_hash: bytes = None
            self.downloading_file = open("./file", "wb")
            self.creation_date = None
            self.comment = None
            self.created_by = None
            self.encoding = None
            self.info = {}

            """ Read and decode metainfo file """
            buffer = file.read()
            meta_data: dict = bencodepy.decode(buffer)
            
            """ Set variables """
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()
            self.creation_date = meta_data[b"creation date"]
            self.comment = meta_data[b"comment"]
            self.created_by = meta_data[b"created by"]
            self.encoding = meta_data[b"encoding"]
            
            """ Set trackers """
            trackers_url = []
            trackers_url.append(meta_data.pop(b"announce"))
            announce_list = meta_data.pop(b"announce-list")
            try:
                for url in announce_list:
                    trackers_url.append(url.pop())
            except Exception:
                print("No hay announce-list")
                
            for url in trackers_url:
                url = str(url, "utf-8")
                if "udp" in url:
                    self.trackers.append(UDPTracker(url))
                else:
                    self.trackers.append(HTTPTracker(url))
            
            info_dict = meta_data[b"info"]
            for key in info_dict:
                self.info[str(key, "utf-8")] = key

    """def share(self):
        handshake = (19).to_bytes(1, "big") + b"BitTorrent protocol\0\0\0\0\0\0\0\0"+self.info_hash+bytes(id, "utf-8")
        unchoke = (1).to_bytes(4, "big") + (1).to_bytes(1, "big")
        interested = (1).to_bytes(4, "big") + (2).to_bytes(1, "big")
        request = (13).to_bytes(4, "big") + (6).to_bytes(1, "big") + \
            (255).to_bytes(1, "big") + \
            (0).to_bytes(1, "big") + (16).to_bytes(1, "big")

        peer_socket = socket.socket()
        peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_socket.bind(local_addr)
        peer_socket.connect((self.peers[b"peers"][0][b"ip"], self.peers[b"peers"][0][b"port"]))
        peer_socket.send(handshake)
        print(peer_socket.recv(68))
        peer_socket.send(interested)
        peer_socket.send(unchoke)
        amount_of_pieces = ceil(
            self.meta_data[b"info"][b"length"] / self.meta_data[b"info"][b"piece length"])
        for i in range(10):
            request = (13).to_bytes(4, "big") + (6).to_bytes(1, "big") + \
                (i).to_bytes(4, "big") + \
                (0).to_bytes(4, "big") + (16).to_bytes(4, "big")
            peer_socket.send(request)
            ans = peer_socket.recv(16000)
            print(ans[0:20])
            self.downloading_file.write(ans[12:])
        self.downloading_file.close()

    def request_peers(self):
        peers = []
        for tracker in self.trackers:
            peers += tracker.request_peers()
        return peers"""


if __name__ == "__main__":
    """a = TorrentFile(
        "./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    print(a.info_hash.hex())
    a.share()
    id = "-ZK0012-3456abcde123"
    handshake = b"19BitTorrent protocol\0\0\0\0\0\0\0\0"+a.info_hash+bytes(id, "UTF-8")
    handshake = (19).to_bytes(1, "big") + b"BitTorrent protocol\0\0\0\0\0\0\0\0"+a.info_hash+bytes(id, "utf-8")
    unchoke = (1).to_bytes(1, "big") + (1).to_bytes(1, "big")
    interested = (1).to_bytes(1, "big") + (2).to_bytes(1, "big")
    request = (13).to_bytes(1, "big") + (6).to_bytes(1, "big") + (255).to_bytes(1, "big") + (0).to_bytes(1, "big") + (16).to_bytes(1, "big")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("172.21.184.95", 55556))
    s.connect((a.peers[b"peers"][0][b"ip"], a.peers[b"peers"][0][b"port"]))
    s.send(handshake)
    print(s.recv(100))
    s.send(interested)
    s.send(request)
    asd = s.recv(100)
    print(asd)"""

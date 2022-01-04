from hashlib import sha1
from requests import get, ConnectTimeout
from pprint import pprint
from math import ceil
import bencodepy
import socket
import logging
from urllib.parse import urlparse
import requests
import trackers

id = "-BC0012-3456abcde123"
local_addr = ("172.28.240.197", 56056)

class PeersNotFound(Exception):
    def __init__(self, message):
        self.message = message

class Peer():
    pass

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
        try:
            self.peers = self.request_peers()
            for peer in self.peers[b"peers"]:
                peer[b"am_choking"] = 1
                peer[b"am_interested"] = 0
                peer[b"peer_choking"] = 1
                peer[b"peer_interested"] = 0
        except PeersNotFound:
            logging.error("Couldn't retrieve peers from trackers.")

    def share(self):
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
        requesters = trackers.TrackerRequestersChain(self.info_hash, self.meta_data)
        trackers_list = [tracker.pop() for tracker in self.meta_data[b"announce-list"]]
        trackers_list.insert(0, self.meta_data[b"announce"])
        for tracker in trackers_list:
            try:
                requesters.request_peers(tracker)
            except socket.timeout:
                print("time out")
            except socket.gaierror:
                print("name or service not known")
            except trackers.BadResponse as err:
                print(err.message)


if __name__ == "__main__":
    a = TorrentFile(
        "./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    a.share()
    """id = "-ZK0012-3456abcde123"
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

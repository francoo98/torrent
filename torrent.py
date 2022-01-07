from torrentfile import TorrentMetaData
from trackers import TrackerError
from pprint import pprint
import client_data
import logging
import socket

class PeersNotFound(Exception):
    def __init__(self, message):
        self.message = message

class Peer():

    def __init__(self, peer_data: dict, torrent):
        self.ip = peer_data[b"ip"]
        self.port = peer_data[b"port"]
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.am_choking = True
        self.am_interested = False
        self.is_choking = True
        self.is_interested = False

    def start(self):
        handshake = (19).to_bytes(1, "big") + bytes("BitTorrent protocol", "utf-8") + b"\0\0\0\0\0\0\0\0" + self.info_hash + bytes(client_data.client_id, "utf-8")
        self.peer_socket.bind(("172.24.112.129", 56056))
        self.peer_socket.connect((self.ip, self.port))
        self.peer_socket.send(handshake)
        response = self.peer_socket.recv(150)
    
    def share(self):
        r = leer_del_socket()
        ver(r)
        if not self.is_choking:
            pieza = enviar_request()

    def request(self, request_data: dict):
        request = bytearray()
        request += request_data["index"].to_bytes(4, "big")
        request += request_data["begin"].to_bytes(4, "big")
        request += request_data["length"].to_bytes(4, "big")
        peer_socket.send(request)
        response = peer_socket.recv(16000)

class Torrent():
    def __init__(self, file_path: str):
        self.torrent_meta_data = TorrentMetaData(file_path)
        # self.client_data = client_data
        self.downloaded = 0
        self.uploaded = 0
        self.left = self.torrent_meta_data.info["length"]
        self.peers = []
        self.request_peers()

    def share(self):
        self.peers[0].start()

    def request_peers(self):
        peers = []
        request_data = {
            "info_hash": self.torrent_meta_data.info_hash,
            "peer_id": client_data.client_id,
            "downloaded": self.downloaded,
            "left": self.left,
            "uploaded": self.uploaded,
            "event": 0,
            "ip": client_data.ip,
            "key": 0,
            "numwant": -1,
            "port": client_data.port}

        trackers = self.torrent_meta_data.trackers
        for tracker in trackers:
            try:
                peers += tracker.request_peers(request_data)
                self.peers += [Peer(peer, self) for peer in peers]
            except TrackerError as err:
                logging.info("El tracker no respondio. " + err.message)

if __name__ == "__main__":
    torrent = Torrent("./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    pprint(torrent.peers[0].ip)
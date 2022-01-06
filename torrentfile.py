from hashlib import sha1
from urllib import parse
from requests import get, Timeout
from pprint import pprint
from math import ceil, lgamma
from time import sleep
from random import randint
import bencodepy
import socket
from urllib.parse import urlparse
import requests
import logging
import argparse

id = "-BC0012-3456abcde123"
local_addr = ("192.168.234.17", 55557)


class BadTrackerResponse(Exception):
    def __init__(self, error_msg, arg):
        self.error_msg = error_msg
        self.arg = arg

class TrackerError(Exception):
    def __init__(self, error_msg, arg = None):
        self.error_msg = error_msg
        self.arg = arg

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
        for peer in self.peers:
            peer[b"am_choking"] = 1
            peer[b"am_interested"] = 0
            peer[b"peer_choking"] = 1
            peer[b"peer_interested"] = 0

    def share(self):
        connected = False
        i = 0

        handshake = (19).to_bytes(1, "big") + b"BitTorrent protocol\0\0\0\0\0\0\0\0"+self.info_hash+bytes(id, "utf-8")
        unchoke = (1).to_bytes(4, "big") + (1).to_bytes(1, "big")
        interested = (1).to_bytes(4, "big") + (2).to_bytes(1, "big")
        request = (13).to_bytes(4, "big") + (6).to_bytes(1, "big") + \
            (255).to_bytes(1, "big") + \
            (0).to_bytes(1, "big") + (16).to_bytes(1, "big")

        peer_socket = socket.socket()
        peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_socket.settimeout(0.5)
        peer_socket.bind(local_addr)

        while not connected:
            try:
                peer_socket.connect((self.peers[i][b"ip"], self.peers[i][b"port"]))
                connected = True
            except ConnectionRefusedError as err:
                print(self.peers[i][b"ip"])
                print(err.strerror)
                i += 1

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
        peer_socket.close()

    def request_peers(self):
        trackers_list = []
        peers = []
        trackers_list.append(self.meta_data[b"announce"])
        try:
            trackers_list = [tracker.pop()
                             for tracker in self.meta_data[b"announce-list"]]
        except KeyError:
            logging.info('b"announce-list"' + "not found in meta_data")

        for tracker in trackers_list:
            try:
                if b"udp" in tracker:
                    peers += self.request_peers_udp(tracker)
                else:
                    peers += self.request_peers_http(tracker)
            except TrackerError as err:
                logging.info(err.error_msg)
        return peers

    def request_peers_udp(self, tracker):
        r = urlparse(tracker)

        tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tracker_socket.settimeout(0.5)
        tracker_socket.bind(local_addr)
        try:
            tracker_socket.connect((r.hostname, r.port))
        except socket.gaierror as err:
            raise TrackerError(err.strerror)

        connection_id = self.udp_connect_request(tracker_socket)
        peers = self.udp_announce(tracker_socket, connection_id)

        tracker_socket.close()
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
            response = bencodepy.bdecode(get(tracker, get_params, timeout=0.5).content)
            return response[b"peers"]
        except Timeout as err:
            raise TrackerError("HTTP GET request to tracker timed out.", tracker)
        except requests.ConnectionError as err:
            raise TrackerError(err.strerror)

    def udp_connect_request(self, tracker_socket: socket.socket):
        transaction_id = randint(0, 4294967295)
        connect_request = (0x41727101980).to_bytes(8, "big") + (0).to_bytes(4, "big") + (transaction_id).to_bytes(4, "big")
        tracker_socket.send(connect_request)
        try:
            connnect_response = tracker_socket.recv(150)
        except socket.timeout:
            raise TrackerError("Tracker timed out.")

        if len(connnect_response) < 16:
            raise TrackerError("Response smaller than 16 bytes.")
        if int.from_bytes(connnect_response[0:4], "big") != 0:
            raise TrackerError("Action field in response is not connect (0).")
        if connnect_response[4:8] != transaction_id.to_bytes(4, "big"):
            raise TrackerError("The tracker answered with a different transaction id.")
        connection_id = connnect_response[8:]
        return connection_id

    def udp_announce(self, tracker_socket, connection_id: bytes):
        peers = []
        transaction_id = randint(0, 4294967295).to_bytes(4, "big")
        announce_request = connection_id + (1).to_bytes(4, "big") + transaction_id + self.info_hash +  bytes(id, "utf-8") + (0).to_bytes(8, "big") + self.meta_data[b"info"][b"length"].to_bytes(8, "big") + (0).to_bytes(8, "big") + (2).to_bytes(4, "big") + (0).to_bytes(4, "big") + (0).to_bytes(4, "big") + (-1).to_bytes(4, "big", signed = True) + (local_addr[1]).to_bytes(2, "big")
        tracker_socket.send(announce_request)
        try:
            response = tracker_socket.recv(150)
        except socket.timeout as err:
            raise TrackerError(err.strerror)

        if len(response) < 20:
            raise TrackerError("Response smaller than 20 bytes.")
        if int.from_bytes(response[0:4], "big") != 1:
            raise TrackerError("Action field in response is not announce (1).")
        if response[4:8] != transaction_id:
            raise TrackerError("The tracker answered with a different transaction id.")

        for i in range(20, len(response), 6):
            ip = str(response[i]) + "." + str(response[i+1]) + "." + str(response[i+2]) + "." + str(response[i+3])
            port = int.from_bytes(response[i+4:i+6], "big")
            peers.append({b"ip": ip, b"port": port})
        
        return peers

        # print(int.from_bytes(response[8:12], "big")) Intervalo
        # print(int.from_bytes(response[12:16], "big")) Leechers
        # print(int.from_bytes(response[16:20], "big")) Seeders

    def udp_scrape(self, connection_id: int, tracker_socket: socket.socket):
        transaction_id = randint(0, 4294967295)
        udp_request = connection_id + \
            (2).to_bytes(4, "big") + \
            (transaction_id).to_bytes(4, "big") + self.info_hash
        tracker_socket.send(udp_request)
        answer = tracker_socket.recv(150)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--log", type=str, default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
    args = parser.parse_args()
    logging.basicConfig(level=args.log)
    a = TorrentFile(
        "The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    a.share()

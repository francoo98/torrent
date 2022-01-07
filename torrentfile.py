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

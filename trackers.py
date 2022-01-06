from urllib.parse import urlparse
from requests import get, Timeout, ConnectionError
import socket
from random import randint
import bencodepy

class TrackerError(Exception):
    def __init__(self, message):
        self.message = message

class Peer():

    def __init__(self):
        self.ip = None
        self.port = None
        self.am_choking = 1
        self.am_interested = 0
        self.is_choking = 1
        self.is_interested = 0
    
    def share(self):
        pass

class Tracker():
    
    def __init__(self, url: str):
        url_parsed = urlparse(url)
        self.name = url_parsed.hostname
        self.port = url_parsed.port

    def request_peers(self, request_data: dict) -> list:
        pass

class UDPTracker(Tracker):
    
    def __init__(self, url: str):
        super().__init__(url)
        self.connection: socket.socket = None
        self.connection_id: bytes = None

    def request_peers(self, request_data: dict) -> list:
        self.connection = self.get_connection((request_data["ip"], request_data["port"]))
        connection_id = self.send_connection_request()
        peers = self.send_announce(connection_id, request_data)

        return peers

    def send_connection_request(self) -> int:
        transaction_id = randint(0, 4294967295)
        connect_request = (0x41727101980).to_bytes(8, "big") + (0).to_bytes(4, "big") + (transaction_id).to_bytes(4, "big")
        self.connection.send(connect_request)
        try:
            connnect_response = self.connection.recv(150)
        except socket.timeout:
            raise TrackerError("Tracker timed out.")

        if len(connnect_response) < 16:
            raise TrackerError("Response smaller than 16 bytes.")
        if int.from_bytes(connnect_response[0:4], "big") != 0:
            raise TrackerError("Action field in response is not connect (0).")
        if connnect_response[4:8] != transaction_id.to_bytes(4, "big"):
            raise TrackerError("The tracker answered with a different transaction id.")
        connection_id = int.from_bytes(connnect_response[8:], "big")
        return connection_id

    def send_announce(self, request_data: dict) -> list:
        peers = []
        transaction_id = randint(0, 4294967295).to_bytes(4, "big")
        announce_request = self.make_announce_request(request_data)
        self.connection.send(announce_request)
        try:
            response = self.connection.recv(150)
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

    def make_announce_request(self, request_data: dict) -> bytes:
        transaction_id = randint(0, 4294967295)
        #announce_request = self.connection_id + (1).to_bytes(4, "big") + transaction_id + self.info_hash +  bytes(client_data[0], "utf-8") + (0).to_bytes(8, "big") + self.meta_data[b"info"][b"length"].to_bytes(8, "big") + (0).to_bytes(8, "big") + (2).to_bytes(4, "big") + (0).to_bytes(4, "big") + (0).to_bytes(4, "big") + (-1).to_bytes(4, "big", signed = True) + (client_data[1][1]).to_bytes(2, "big")
        announce_request = bytearray()
        announce_request += self.connection_id                  
        announce_request += (1).to_bytes(4, "big") # action field, 4 bytes
        announce_request += (transaction_id).to_bytes(4, "big") 
        announce_request += request_data["info_hash"]           
        announce_request += bytes(request_data["peer_id"], "utf-8") 
        announce_request += request_data["downloaded"].to_bytes(8, "big")
        announce_request += request_data["left"].to_bytes(8, "big")
        announce_request += request_data["uploaded"].to_bytes(8, "big")
        announce_request += request_data["event"].to_bytes(4, "big")
        announce_request += (0).to_bytes(4, "big")  # ip address field, 4 bytes, 0 default
        announce_request += (0).to_bytes(4, "big")  # key field, 4 bytes
        announce_request += (-1).to_bytes(4, "big") # num_want field, 4 bytes, -1 default
        announce_request += (request_data["port"]).to_bytes(4, "big")

        return announce_request


    """ La comento porque ahora no uso, quizas sea necesaria mas adelante.
    def udp_scrape(self, connection_id: int, tracker_socket: socket.socket):
        transaction_id = randint(0, 4294967295)
        udp_request = connection_id + \
            (2).to_bytes(4, "big") + \
            (transaction_id).to_bytes(4, "big") + self.info_hash
        tracker_socket.send(udp_request)
        answer = tracker_socket.recv(150)"""

    def get_connection(self, client_data: tuple) -> socket.socket:
        if self.connection == None:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.connection.settimeout(0.5)
            self.connection.bind(client_data(1))
            try:
                self.connection.connect((self.hostname, self.port))
            except socket.gaierror as err:
                raise TrackerError(err.strerror)
        else:
            return self.connection

class HTTPTracker(Tracker):
    
    def request_peers_http(self, request_data: dict):
        """get_params = {
            "info_hash": torrent_meta_data.info_hash,
            "peer_id": bytes(client_data[0], "utf-8"),
            "port": client_data[1][1],
            "downloaded": 0,
            "uploaded": 0,
            "left": torrent_meta_data.info["length"]
        }"""
        try:
            peers = bencodepy.bdecode(get(self.name, request_data, timeout=0.5).content)
            return peers[b"peers"]
        except Timeout as err:
            raise TrackerError("HTTP GET request to tracker timed out.")
        except ConnectionError as err:
            raise TrackerError(err.strerror)

import socket
from urllib.parse import urlparse
import torrentfile
from random import randint

class BadResponse(Exception):
    def __init__(self, message):
        self.message = message

class TrackerRequester():

    def __init__(self, next):
        self.next_requester = next

    def request_peers(self, tracker_url, info_hash: bytes, meta_data):
        pass


class UDPTrackerRequester(TrackerRequester):

    def __init__(self, next):
        super().__init__(next)

    def request_peers(self, tracker_url, info_hash: bytes, meta_data):
        if b"udp" in tracker_url:
            r = urlparse(tracker_url)

            tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tracker_socket.settimeout(0.5)
            tracker_socket.bind(torrentfile.local_addr)
            tracker_socket.connect((r.hostname, r.port))

            self.connection_id = self.connect(tracker_socket)
            
           


            udp_request = connection_id + (2).to_bytes(4, "big") + (transaction_id).to_bytes(4, "big") + info_hash
            tracker_socket.send(udp_request)
            answer = tracker_socket.recv(150)
            print(answer[8:12])
            tracker_socket.close()
        else:
            try:
                return self.next_requester.request_peers(tracker_url, info_hash)
            except Exception as err:
                print("Exception siguiente tracker en cadena")

    def connect(self, tracker_socket: socket.socket):
        transaction_id = 4455667
        connect_request = (0x41727101980).to_bytes(8, "big") + (0).to_bytes(4, "big") + (transaction_id).to_bytes(4, "big")
        tracker_socket.send(connect_request)
        connnect_response = tracker_socket.recv(150)

        if len(connnect_response) < 16:
            raise BadResponse("Response smaller than 16 bytes.")
        #if connnect_response[0:4] != 0:
            #raise BadResponse("Action field in response is not connect (0).")
        if connnect_response[4:8] != transaction_id.to_bytes(4, "big"):
            raise BadResponse("The tracker answered with a different transaction id.")
        connection_id = connnect_response[8:]
        return connection_id

    def announce(self, tracker_socket, info_hash):
        transaction_id = randint(0, 4294967295).to_bytes(4, "big")
        announce_request = self.connection_id + (1).to_bytes(4, "big") + transaction_id + info_hash + bytes(torrentfile.id, "utf-8")


class HTTPTrackerRequester(TrackerRequester):

    """get_params = {
            "info_hash": self.info_hash,
            "peer_id": bytes(id, "utf-8"),
            "port": 55556,
            "downloaded": 0,
            "uploaded": 0,
            "left": self.meta_data[b"info"][b"length"]
        }"""

    pass

class TrackerRequestersChain(TrackerRequester):

    def __init__(self):
        http = HTTPTrackerRequester(next = None)
        udp = UDPTrackerRequester(next = http)
        self.next_requester = udp

    def request_peers(self, tracker_url, info_hash: bytes):
        return self.next_requester.request_peers(tracker_url, info_hash)

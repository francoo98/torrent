from typing import Final
from torrentfile import TorrentMetaData
from trackers import TrackerError
from pprint import pprint
import client_data
import logging
import socket

UNCHOKE: Final = b'\x00\x00\x00\x01\x01'

class PeersNotFound(Exception):
    def __init__(self, message):
        self.message = message

class PeerNotAvailable(Exception):
    def __init__(self, message):
        self.message = message

class Peer():

    def __init__(self, peer_data: dict, torrent):
        self.torrent = torrent
        self.ip = peer_data[b"ip"]
        self.port = peer_data[b"port"]
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

    def start(self):
        port = 55555
        handshake = (19).to_bytes(1, "big") + bytes("BitTorrent protocol", "utf-8") + b"\0\0\0\0\0\0\0\0" + self.torrent.torrent_meta_data.info_hash + bytes(client_data.client_id, "utf-8")
        while True:
            try:
                self.peer_socket.bind((client_data.ip, port))
                break
            except OSError:
                port += 1
        
        try:
            self.peer_socket.settimeout(0.5)
            self.peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.peer_socket.connect((self.ip, self.port))
            self.peer_socket.send(handshake)
            handshake_response = self.peer_socket.recv(1000)
        except socket.timeout as err:
            #print(err.with_traceback(None))
            raise PeerNotAvailable(err.with_traceback(None))
        except ConnectionRefusedError as err:
            #print(err.with_traceback(None))
            raise PeerNotAvailable(err.with_traceback(None))
        except ConnectionResetError as err:
            #print(err.with_traceback(None))
            raise PeerNotAvailable(err.with_traceback(None))
        except OSError as err: # No route to host is one possible error
            #print(err.with_traceback(None))
            raise PeerNotAvailable(err.with_traceback(None))

        #print("# Respuesta de handshake #")
        #print(handshake_response)

        if b"\x13BitTorrent protocol" not in handshake_response:
            return # should raise an exception?

        """ Check for bitfield """
        bitfield_len = 0
        if len(handshake_response) > 68:
            bitfield_len = int.from_bytes(handshake_response[68:72], "big")
            #if len(handshake_response[72:]) < bitfield_len:
            #    raise PeerNotAvailable("Corrupt bitfield")
            self.bitfield = handshake_response[73:73+bitfield_len-1]
        
        """ Check for other message in the same response """
        bitfield_end = 68 + bitfield_len + 4
        if len(handshake_response) > bitfield_end:
            msg_len = int.from_bytes(handshake_response[bitfield_end:bitfield_end+4], "big")
            msg = handshake_response[bitfield_end+4:bitfield_end+4+msg_len+1]
            if len(msg) == msg_len:
                self.__check_msg(msg)

        self.share()

        """print("# Lectura de prueba #")
        response = self.peer_socket.recv(450)
        print(response)

        
        print("# Respuesta de interested #")
        self.send_interested()
        response = self.peer_socket.recv(100)
        print(response)

        print("# Respuesta de solicitud request #")
        block_size = int(self.torrent.torrent_meta_data.info["piece length"] / 2)
        self.request_piece({"index": 0, "begin": 0, "length": block_size})
        self.peer_socket.close()"""
    
    def share(self):
        print("share()")
        self.__send_interested()
        """try:
            r = self.peer_socket.recv(100)
        except socket.timeout as err:
            print(err.with_traceback(None))"""
        
        if not self.peer_choking:
            print("peer not choking")
            block_size = int(self.torrent.torrent_meta_data.info["piece length"] / 2)
            try:
                self.request_piece({"index": 0, "begin": 0, "length": block_size})
            except socket.timeout:
                print("Error de time out.")

    def request_piece(self, request_data: dict):
        print("request_piece()")
        request = bytearray()
        request += request_data["index"].to_bytes(4, "big")
        request += request_data["begin"].to_bytes(4, "big")
        request += request_data["length"].to_bytes(4, "big")
        self.peer_socket.send(request)
        response = self.peer_socket.recv(request_data["length"] + 13)
        print(response[:120])
        if response[4] == 7:
            return response[12:]
    
    def __send_interested(self):
        msg = (1).to_bytes(4, "big") + (2).to_bytes(1, "big")
        self.peer_socket.send(msg)
        self.am_interested = True

    def __check_msg(self, msg: bytes):
        if msg[0] == 0:
            self.peer_choking = True
            return
        if msg[0] == 1:
            self.peer_choking = False
            return
        if msg[0] == 2:
            self.peer_interested = True
            return
        if msg[0] == 3:
            self.peer_interested = False
            return

    def check_socket(self):
        pass

class Torrent():
    def __init__(self, file_path: str):
        self.torrent_meta_data = TorrentMetaData(file_path)
        self.downloading_file = open("./file", "wb")
        # self.client_data = client_data
        self.downloaded = 0
        self.uploaded = 0
        self.left = self.torrent_meta_data.info["length"]
        self.peers = []
        # self.request_peers()

    def share(self):
        # 217.208.123.231:23512
        self.peers = [Peer({b"ip": "217.208.123.231", b"port": 23512}, self)]
        for peer in self.peers:
            try:
                peer.start()
                # break
            except PeerNotAvailable as err:
                logging.info(err.with_traceback(None))
        """for peer in self.peers:
            print("## Trying: " + peer.ip + " " + str(peer.port))
            peer.start()"""

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
                logging.info(err.message)

if __name__ == "__main__":
    logging.basicConfig(level = "INFO")
    torrent = Torrent("./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    torrent.share()
import time
from torrentfile import TorrentMetaData
from trackers import TrackerError
from pprint import pprint
import client_data
import logging
import socket

CHOKE = b"\x00\x00\x00\x01\x00"
UNCHOKE = b"\x00\x00\x00\x01\x01"
INTERESTED = b"\x00\x00\x00\x01\x02"
NOT_INTERESTED = b"\x00\x00\x00\x01\x03"

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
        self.pending = []
        self.bitfield = b""

    def start(self):
        handshake = (19).to_bytes(1, "big") + bytes("BitTorrent protocol", "utf-8") + b"\0\0\0\0\0\0\0\0" + self.torrent.torrent_meta_data.info_hash + bytes(client_data.client_id, "utf-8")
        try:
            self.peer_socket.settimeout(1.5)
            self.peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.peer_socket.connect((self.ip, self.port))
            self.peer_socket.send(handshake)
            handshake_response = self.peer_socket.recv(68)
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

        if b"\x13BitTorrent protocol" not in handshake_response or len(handshake) != 68:
            raise PeerNotAvailable("Peer answered with a corrupt handshake")
        
        """ Check for bitfield 
        bitfield_len = 0
        if len(handshake_response) > 68:
            bitfield_len = int.from_bytes(handshake_response[68:72], "big")
            #if len(handshake_response[72:]) < bitfield_len:
            #    raise PeerNotAvailable("Corrupt bitfield")
            self.bitfield = handshake_response[73:73+bitfield_len-1]
        
        Check for other message in the same response 
        bitfield_end = 68 + bitfield_len + 4
        if len(handshake_response) > bitfield_end:
            msg_len = int.from_bytes(handshake_response[bitfield_end:bitfield_end+4], "big")
            msg = handshake_response[bitfield_end:bitfield_end+4+msg_len+1]
            if len(msg) == msg_len:
                self.__check_msg(msg)"""
        
        self.share()
    
    def share(self):
        print("share()")
        self.peer_socket.send(INTERESTED)
        self.am_interested = True
        self.peer_socket.send(UNCHOKE)
        self.am_choking = False
        
        while True:
            data = b""
            try:
                data = self.peer_socket.recv(4)
                if len(data) == 4:
                    msg = self.peer_socket.recv(int.from_bytes(data, "big"))
                    self.__check_msg(data + msg)
            except socket.timeout:
                pass

            if not self.peer_choking:
                print("peer not choking")
                # block_size = int(self.torrent.torrent_meta_data.info["piece length"] / 2)
                block_size = 16384
                index = 0
                try:
                    if index not in self.pending:
                        self.request_piece({"index": index, "begin": 0, "length": block_size})
                except socket.timeout:
                    print("Error de time out.")


    def request_piece(self, request_data: dict):
        print("request_piece()")
        request = bytearray()
        request += (13).to_bytes(4, "big")
        request += (6).to_bytes(1, "big")
        request += request_data["index"].to_bytes(4, "big")
        request += request_data["begin"].to_bytes(4, "big")
        request += request_data["length"].to_bytes(4, "big")
        self.peer_socket.send(request)
        self.pending.append(request_data["index"])

    def __check_msg(self, msg: bytes):
        if len(msg) < 4:
            return
        if msg == b"\0\0\0\0":
            # keep alive
            return
        if msg[4] == 0:
            self.peer_choking = True
            return
        if msg[4] == 1:
            self.peer_choking = False
            return
        if msg[4] == 2:
            self.peer_interested = True
            return
        if msg[4] == 3:
            self.peer_interested = False
            return
        if msg[4] == 4 and len(msg) == 9:
            piece_index = int.from_bytes(msg[5:9], "big")
            self.__add_piece_to_bitfield(piece_index)
            return
        if msg[4] == 5:
            self.bitfield = msg[5:]
            return
        if msg[4] == 7:
            print(msg[0:120])
            return
        
    def __add_piece_to_bitfield(self, piece_index: int):
        byte_index = int(piece_index/8)
        byte_value = self.bitfield[byte_index]
        bit_index_in_byte = 7 - (piece_index - byte_index * 8)
        byte_value = byte_value | (2**bit_index_in_byte)
        try:
            self.bitfield[byte_index] = byte_value
        except IndexError:
            logging.info("Peer sent have message with wrong piece index")
    
    def check_socket(self):
        pass

class Torrent():

    def __init__(self, file_path: str):
        self.torrent_meta_data = TorrentMetaData(file_path)
        self.downloading_file = open("./file", "wb")
        self.downloaded = 0
        self.uploaded = 0
        self.left = self.torrent_meta_data.info["length"]
        self.peers = []
        self.request_peers()

    def share(self):
        for peer in self.peers:
            try:
                peer.start()
            except PeerNotAvailable as err:
                logging.info(err.with_traceback(None))

    def request_peers(self):
        peers = []
        request_data = {
            "info_hash": self.torrent_meta_data.info_hash,
            "peer_id": client_data.client_id,
            "downloaded": self.downloaded,
            "left": self.left,
            "uploaded": self.uploaded,
            "event": 0,
            "ip": 0,
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
    #start = time.time()
    torrent = Torrent("./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    #finish = time.time()
    #print(finish - start)
    torrent.share()
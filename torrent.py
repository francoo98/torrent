from hashlib import sha1
from math import ceil
from random import randint
from socketserver import BaseRequestHandler
from bitfield import BitField
from filemanager import SingleFileManager
from torrentfile import TorrentMetaData
from trackers import TrackerError
import client_data
import logging
import socket

CHOKE = b"\x00\x00\x00\x01\x00"
UNCHOKE = b"\x00\x00\x00\x01\x01"
INTERESTED = b"\x00\x00\x00\x01\x02"
NOT_INTERESTED = b"\x00\x00\x00\x01\x03"
BLOCK_SIZE = 16384

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
        self.bitfield = None
        self.current_piece = [-1, bytearray(0)] # [1] piece id, [2] data

    @classmethod
    def from_connection(cls, conn, torrent):
        peer_data = {b"ip": conn[1][0], b"port": conn[1][1]}
        peer = cls(peer_data, torrent)
        peer.peer_socket = conn[0]
        peer.share()

    def start(self):
        handshake = (19).to_bytes(1, "big") + bytes("BitTorrent protocol", "utf-8") + b"\0\0\0\0\0\0\0\0" + self.torrent.torrent_meta_data.info_hash + bytes(client_data.client_id, "utf-8")
        try:
            self.peer_socket.settimeout(1.5)
            self.peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.peer_socket.connect((self.ip, self.port))
            self.peer_socket.send(handshake)
            handshake_response = self.peer_socket.recv(68)
        except socket.timeout as err:
            raise PeerNotAvailable(err.with_traceback(None))
        except ConnectionRefusedError as err:
            raise PeerNotAvailable(err.with_traceback(None))
        except ConnectionResetError as err:
            raise PeerNotAvailable(err.with_traceback(None))
        except OSError as err: # No route to host is one possible error
            raise PeerNotAvailable(err.with_traceback(None))

        if b"\x13BitTorrent protocol" not in handshake_response or len(handshake) != 68:
            raise PeerNotAvailable("Peer answered with a corrupt handshake")
        
        self.share()
    
    def share(self):
        self.peer_socket.send(INTERESTED)
        self.am_interested = True
        self.peer_socket.send(UNCHOKE)
        self.am_choking = False
        
        while True:
            try:
                self.__check_input()
            except socket.timeout:
                # print("Timeout de " + self.ip)
                pass
            except PeerNotAvailable as err:
                print(err.message)
                self.peer_socket.close()
                return

            piece_id = randint(0, self.torrent.number_of_pieces - 1)
            if (self.bitfield and not self.peer_choking and self.am_interested 
                and self.torrent.bitfield[piece_id] == 0 and self.current_piece[0] == -1):
                self.current_piece[0] = piece_id 
                for i in range(self.torrent.number_of_blocks):
                    self.request_piece({"index": self.current_piece[0], "begin": i*BLOCK_SIZE, "length": BLOCK_SIZE}) 

            """
            data = b""
            try:
                data = self.peer_socket.recv(4)
                if len(data) == 4:
                    msg = self.peer_socket.recv(int.from_bytes(data, "big"))
                    self.__check_msg(data + msg)
            except socket.timeout:
                print("Timeout")
            
            if not self.peer_choking:
                if self.current_piece[0] == -1:
                    self.current_piece[0] = index
                # print("peer not choking")
                # block_size = int(self.torrent.torrent_meta_data.info["piece length"] / 2)
                n = int(self.torrent.torrent_meta_data.info["piece length"] / BLOCK_SIZE)
                try:
                    if index not in self.pending:
                        # self.request_piece({"index": index, "begin": 0, "length": block_size})
                        while n >= 0:
                            self.request_piece({"index": index, "begin": n*BLOCK_SIZE, "length": BLOCK_SIZE})
                            print("requested")
                            n = n - 1
                except socket.timeout:
                    print("Error de time out.")
            """

    def request_piece(self, request_data: dict):
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
            self.bitfield.add(piece_index)
            return
        if msg[4] == 5:
            bitfield_length = int.from_bytes(msg[0:4], "big") - 1
            if bitfield_length != ceil(self.torrent.number_of_pieces/8) or len(msg[5:]) != ceil(self.torrent.number_of_pieces/8): 
                # raise PeerNotAvailable("Peer sent corrupt bitfield")
                pass
            self.bitfield = BitField.from_bytes(msg[5:])
            return
        if msg[4] == 6:
            self.__answer_block_request(msg)
            return
        if msg[4] == 7:
            offset = int.from_bytes(msg[9:13], "big")
            length = int.from_bytes(msg[0:4], "big") - 9
            self.current_piece[1][offset:offset+length] = msg[13:]
            if sha1(self.current_piece[1]).digest() == self.torrent.torrent_meta_data.info["pieces"][self.current_piece[0]]:
                print("Se recibio una pieza de ID = " + str(self.current_piece[0]))
                self.torrent.add_piece(self.current_piece)
                self.current_piece[0] = -1
                self.current_piece[1] = bytearray(0)
            return
        if msg[4] == 8:
            print("Se cancelo una solicitud de bloque")
            return
        if msg[4] == 9:
            print("Puerto DHT")
            return
        print("LLego un mensaje corrupto")
        
    """def __add_piece_to_bitfield(self, piece_index: int):
        byte_index = int(piece_index/8)
        byte_value = self.bitfield[byte_index]
        bit_index_in_byte = 7 - (piece_index - byte_index * 8)
        byte_value = byte_value | (2**bit_index_in_byte)
        try:
            self.bitfield[byte_index] = byte_value
        except IndexError:
            logging.info("Peer sent have message with wrong piece index")"""
    
    def __check_input(self):
        data = b""
        data = self.peer_socket.recv(4)
        if len(data) == 4:
            msg = self.peer_socket.recv(int.from_bytes(data, "big"))
            self.__check_msg(data + msg)

    def __answer_block_request(self, request_msg):
        piece_id = int.from_bytes(request_msg[5:9], "big")
        if self.torrent.bitfield[piece_id] == True:
            block_offset = int.from_bytes(request_msg[9:13], "big")
            length = int.from_bytes(request_msg[13:17], "big")
            piece = self.torrent.get_piece(piece_id)
            piece[1] = piece[1][block_offset:block_offset+length]
            piece_msg = (9 + len(piece[1])).to_bytes(4, "big") + (7).to_bytes(1, "big") + request_msg[5:9] + request_msg[9:13] + piece[1]
            self.peer_socket.send(piece_msg)

class Torrent():

    def __init__(self, file_path: str):
        self.torrent_meta_data = TorrentMetaData(file_path)
        self.uploaded = 0
        self.peers = []
        self.file_manager = None
        self.number_of_pieces = ceil(self.torrent_meta_data.info["length"]/self.torrent_meta_data.info["piece length"]) 
        self.number_of_blocks = int(self.torrent_meta_data.info["piece length"] / BLOCK_SIZE)
        self.bitfield = None

        if "files" in self.torrent_meta_data.info.keys():
            self.file_manager = None
        else:
            self.file_manager = SingleFileManager(self.torrent_meta_data.info)

        self.bitfield = self.file_manager.calculate_bitfield()
        # self.downloaded = self.__calculate_downloaded()
        self.downloaded = 0
        self.left = self.torrent_meta_data.info["length"] - self.downloaded
        
        # self.request_peers()

    def share(self):
        peer_data = {b"ip": "127.0.0.2", b"port": 56055}
        peer = Peer(peer_data, self)
        peer.start()
        """for peer in self.peers:
            try:
                peer.start()
            except PeerNotAvailable as err:
                logging.info(err.with_traceback(None))"""

    def request_peers(self):
        peers = []
        request_data = {
            "info_hash": self.torrent_meta_data.info_hash,
            "peer_id": client_data.client_id,
            "downloaded": self.downloaded,
            "left": 0,
            "uploaded": self.uploaded,
            "compact": 1,
            "event": "started",
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
    
    def add_piece(self, piece: tuple):
        if self.bitfield[piece[0]] == 0:
            self.file_manager.write_piece(piece)
            self.bitfield.add(piece[0])

    def get_piece(self, piece_id):
        return self.file_manager.get_piece(piece_id)

    """def __calculate_downloaded(self):
        downloaded_pieces = 0
        downloaded_bytes = 0

        for bit in self.bitfield:
            downloaded_pieces += bit

        if self.bitfield[-1] == 1:
            downloaded_pieces -= 1
            downloaded_bytes = self.torrent_meta_data.info["length"] - self.torrent_meta_data.info["piece length"]*(self.number_of_pieces - 1)
        
        downloaded_bytes += downloaded_pieces*self.torrent_meta_data.info["piece length"]

        return downloaded_bytes"""

if __name__ == "__main__":
    logging.basicConfig(level = "INFO")
    torrent = Torrent("./texto.txt.torrent")
    """print(torrent.bitfield.bits)
    for i in range(16):
        print(f"Bit {i} en {torrent.bitfield[i]}")

    print(torrent.number_of_pieces)"""
    torrent.share()
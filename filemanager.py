from hashlib import sha1
from math import ceil
from os import path
from bitfield import BitField

class FileManager():

    def __init__(self, info: dict):
        pass

    def write_piece(self, piece: tuple):
        pass

    def get_piece(self, piece_id: int):
        pass

    def calculate_bitfield(self):
        pass

class SingleFileManager(FileManager):

    def __init__(self, info: dict):
        self.name = str(info["name"], "UTF-8")
        self.length = info["length"]
        self.piece_len = info["piece length"]
        self.pieces = info["pieces"]
        
        try:
            self.file = open("./" + self.name, "x+b")
        except FileExistsError:
            self.file = open("./" + self.name, "r+b")
        
        self.file.seek(0)

    def write_piece(self, piece):
        offset = piece[0]*self.piece_len
        self.file.seek(offset)
        self.file.write(piece[1])

    def get_piece(self, piece_id: int) -> list:
        self.file.seek(piece_id * self.piece_len)
        piece = self.file.read(self.piece_len)
        return [piece_id, piece]

    def calculate_bitfield(self):
        piece_id = 0
        bitfield = BitField(ceil(self.length/self.piece_len/8))

        while (piece := self.file.read(self.piece_len)) != b"":
            phash = sha1(piece).digest()
            if phash == self.pieces[piece_id]:
                bitfield.add(piece_id)
            piece_id += 1

        return bitfield
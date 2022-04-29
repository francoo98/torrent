import logging

class BitField():

    def __init__(self, size: int):
        self.size = size
        self.bits = b"\0" * self.size 

    @classmethod
    def from_bytes(cls, data: bytes):
        bitfield = cls(len(data))
        bitfield.bits = data
        return bitfield


    def add(self, piece_index):
        byte_index = int(piece_index/8)
        byte_value = self.bits[byte_index]
        bit_index_in_byte = 7 - (piece_index - byte_index * 8)
        byte_value = byte_value | (2**bit_index_in_byte)
        try:
            self.bitfield[byte_index] = byte_value
        except IndexError:
            logging.info("Index out of bounds")

    """def value_of(self, piece_index):
        byte_index = int(piece_index/8)
        byte_value = self.bits[byte_index]
        bit_index_in_byte = 7 - (piece_index - byte_index * 8)
        byte_value = byte_value >> bit_index_in_byte"""

    def __getitem__(self, piece_index):
        byte_index = int(piece_index/8)
        byte_value = self.bits[byte_index]
        bit_index_in_byte = 7 - (piece_index - byte_index * 8)
        byte_value = byte_value >> bit_index_in_byte
        byte_value = byte_value & 0b00000001
        return byte_value

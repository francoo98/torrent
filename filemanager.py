class FileManager():

    def __init__(self, info: dict):
        pass

    def write_piece(self, piece: tuple):
        pass

class SingleFileManager(FileManager):

    def __init__(self, info: dict):
        self.name = info[b"name"]
        self.length = info[b"length"]
        self.piece_len = info[b"piece legth"]
        self.file = open("./" + self.name, "xb")

    def write_piece(self, piece: tuple):
        offset = piece(0)*self.piece_len
        self.file.seek(offset)
        self.file.write(piece(1))

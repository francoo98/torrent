class FileManager():

    def __init__(self, info: dict):
        pass

    def write_piece(self, piece: tuple):
        pass

class SingleFileManager(FileManager):

    def __init__(self, info: dict):
        self.name = str(info["name"], "UTF-8")
        self.length = info["length"]
        self.piece_len = info["piece length"]
        self.file = open("./" + self.name, "ab")
        self.file.seek(0)

    def write_piece(self, piece: tuple):
        offset = piece(0)*self.piece_len
        self.file.seek(offset)
        self.file.write(piece(1))
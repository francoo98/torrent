from io import BufferedReader
import bencodepy
from hashlib import sha1

class TorrentFile():
    
    def __init__(self, file_path: str): 
        self.file_path = file_path
        with open(file_path, "rb") as file:
            buffer = file.read()
            self.meta_data = bencodepy.decode(buffer)
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()


if __name__ == "__main__":
    a = TorrentFile("./xubuntu-20.04.3-desktop-amd64.iso.torrent")
    print(a.info_hash.hex())
    print(a.meta_data[b"announce"])
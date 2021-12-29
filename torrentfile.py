from hashlib import sha1
from requests import get
from pprint import pprint
import bencodepy

class TorrentFile():
    
    def __init__(self, file_path: str): 
        # self.file_path = file_path
        # decode file and calculate hash
        with open(file_path, "rb") as file:
            buffer = file.read()
            self.meta_data = bencodepy.decode(buffer)
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()
        # request peers from the tracker
        get_params = {
            "info_hash": self.info_hash,
            "peer_id": "123f5678x987654321ab",
            "port": 55555,
            "downloaded": 0,
            "uploaded": 0,
            "left": self.meta_data[b"info"][b"length"]
        }
        self.peers = get(self.meta_data[b"announce"], get_params)


if __name__ == "__main__":
    a = TorrentFile("./xubuntu-20.04.3-desktop-amd64.iso.torrent")
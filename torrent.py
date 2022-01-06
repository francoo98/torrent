from requests.api import request
from torrentfile import TorrentMetaData
from trackers import Tracker
from pprint import pprint

client_data = ("-BC0012-3456abcde123", ("172.28.240.197", 56056))

class PeersNotFound(Exception):
    def __init__(self, message):
        self.message = message

class Torrent():
    def __init__(self, url: str, client_data: tuple):
        self.torrent_meta_data = TorrentMetaData(url)
        self.client_data = client_data
        self.downloaded = 0
        self.uploaded = 0
        self.left = self.torrent_meta_data.info["length"]
        self.peers = []
        self.request_peers()

    def share(self):
        pass

    def request_peers(self):
        request_data = {
            "info_hash": self.torrent_meta_data.info_hash,
            "peer_id": self.client_data[0],
            "downloaded": self.downloaded,
            "left": self.left,
            "uploaded": self.uploaded,
            "event": 0,
            "ip": self.client_data[1][0],
            "key": 0,
            "numwant": -1,
            "port": self.client_data[1][1]
        }
        trackers = self.torrent_meta_data.trackers
        for tracker in trackers:
            self.peers += tracker.request_peers(request_data)

if __name__ == "__main__":
    torrent = Torrent("./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent",
                        client_data)
    pprint(torrent.peers)
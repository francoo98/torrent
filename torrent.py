from torrentfile import TorrentMetaData
from trackers import Peer, TrackerError
from pprint import pprint
import client_data

class PeersNotFound(Exception):
    def __init__(self, message):
        self.message = message

class Torrent():
    def __init__(self, file_path: str):
        self.torrent_meta_data = TorrentMetaData(file_path)
        # self.client_data = client_data
        self.downloaded = 0
        self.uploaded = 0
        self.left = self.torrent_meta_data.info["length"]
        self.peers = []
        self.request_peers()

    def share(self):
        pass

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
                self.peers += [Peer(peer) for peer in peers]
            except TrackerError as err:
                pass
                # print("El tracker no respondio. " + err.message)

if __name__ == "__main__":
    torrent = Torrent("./The Complete Chess Course - From Beginning to Winning Chess - 21st Century Edition (2016).epub Gooner-[rarbg.to].torrent")
    pprint(torrent.peers[0].ip)
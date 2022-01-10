import bencodepy
import socket
import logging
from hashlib import sha1
from pprint import pprint
from math import ceil
from trackers import UDPTracker, HTTPTracker

class TorrentMetaData():

    def __init__(self, file_path: str):
        with open(file_path, "rb") as file:
            """ Class atributes """
            self.trackers = []
            self.info_hash: bytes = None
            self.creation_date = None
            self.comment = None
            self.created_by = None
            self.encoding = None
            self.info = {}

            """ Read and decode metainfo file """
            buffer = file.read()
            meta_data: dict = bencodepy.decode(buffer)
            
            """ Set variables """
            info_index = buffer.find(b"4:infod")
            self.info_hash = sha1(buffer[info_index+6:-1]).digest()
            self.creation_date = meta_data[b"creation date"]
            self.comment = meta_data[b"comment"]
            self.created_by = meta_data[b"created by"]
            self.encoding = meta_data[b"encoding"]
            
            """ Set trackers """
            trackers_url = []
            trackers_url.append(meta_data.pop(b"announce"))
            announce_list = meta_data.pop(b"announce-list")
            try:
                for url in announce_list:
                    trackers_url.append(url.pop())
            except Exception:
                print("No hay announce-list")
                
            for url in trackers_url:
                url = str(url, "utf-8")
                if "udp" in url:
                    self.trackers.append(UDPTracker(url))
                else:
                    self.trackers.append(HTTPTracker(url))
            
            info_dict = meta_data[b"info"]
            for key in info_dict:
                self.info[str(key, "utf-8")] = info_dict[key]

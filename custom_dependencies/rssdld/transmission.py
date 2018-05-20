import sys, os
import logging
import pprint
import json
import re
from enum import Enum
from time import mktime

from transmission import Transmission as TC

log = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log.setLevel(logging.WARNING)

class TStatus(Enum):
    STOPPED       = 0  # Torrent is stopped
    CHECK_WAIT    = 1  # Queued to check files
    CHECK         = 2  # Checking files
    DOWNLOAD_WAIT = 3  # Queued to download
    DOWNLOAD      = 4  # Downloading
    SEED_WAIT     = 5  # Queued to seed
    SEED          = 6  # Seeding
    ISOLATED      = 7  # Torrent can't find peers

class Torrent(object):
    def __init__(self, map):
        self.name = map['name']
        self.hash = map['hashString']
        self.status = map['status']
        self.eta = map['eta']
        self.totalSize = map['totalSize']
        self.leftUntilDone = map['leftUntilDone']
        self.rateDownload = map['rateDownload']
        if self.totalSize != 0:
            self.progress = 100.0 - float(float(self.leftUntilDone) * 100.0 / float(self.totalSize))
        else:
            self.progress = 0.0

    def __str__(self):
        if self.hash is not None:
            return "{:<32s} {:2d} {:8d} {:%4.2f}% {:8d}".format(self.name, self.status, self.eta, self.progress, self.rateDownload)
        else:
            return "None type"


class Transmission(object):
    def __init__(self, config):
        self.tc = TC(host=config['host'], port=config['port'], 
                     username=config['username'], password=config['password'])

    def get(self, hash):
        log.debug('get %s', hash)
        rsp = self.tc('torrent-get', ids=hash, fields=['name', 'status', 'hashString', 'eta', 'rateDownload', 'leftUntilDone', 'totalSize'])
        try:
            if rsp['torrents']:
                log.debug(rsp)
                return Torrent(rsp['torrents'][0])
        except KeyError: pass
        return None

    def add(self, magnet, download_dir):
        log.debug('add torrent %s in %s', magnet, download_dir)
        rsp = self.tc('torrent-add', filename=magnet, download_dir=download_dir, paused=True)
        log.debug(rsp)
        try:
            if rsp['torrent-added']:
                return True
        except KeyError: pass
        return False

    def start(self, hash):
        log.debug('start %s', hash)
        self.tc('torrent-start', ids=hash)

    def stop(self, hash):
        log.debug('stop %s', hash)
        self.tc('torrent-stop', ids=hash)

    def remove(self, hash):
        log.debug('remove %s', hash)
        self.tc('torrent-remove', ids=hash)

import sys, os
import logging
import re
from enum import Enum
from datetime import datetime, timedelta
from time import mktime

log = logging.getLogger(__name__)


class IState(Enum):
    NONE = 1
    NEW = 2
    DOWNLOADING = 3
    UPDATING = 4
    AVAILABLE = 5

def getQuality(title):
    if '480p' in title:
        return '480p'
    elif '720p' in title:
        return '720p'
    elif '1080p' in title:
        return '1080p'
    else:
        return 'na'

def getNumbering(title):
    try:
        m = re.search('.*S([0-9]{2})E([0-9]{2}).*', title, re.IGNORECASE)
        return [int(m.group(1)), int(m.group(2))]
    except:
        try:
            m = re.search('.*([0-9]{1,2})x([0-9]{2}).*', title, re.IGNORECASE)
            return [int(m.group(1)), int(m.group(2))]
        except:
            return [0, 0]


class Episode(object):

    def __init__(self, item = None, dir = None, **entries):
        self.title = None
        self.published = 0
        self.link = None
        self.uid = 0
        self.showid = 0
        self.showname = None
        self.hash = None
        self.quality = None
        self.episode = 0
        self.season = 0
        self.dir = None
        self.state = IState.NONE.value

        if item:
            self.title = item["title"]
            self.published = int(mktime(item["published_parsed"]))
            self.link = item["link"]
            self.uid = int(item["tv_episode_id"])
            self.showid = int(item["tv_show_id"])
            self.showname = re.sub('[\\/:"*?<>|]+', '', item["tv_show_name"])
            self.hash = item["tv_info_hash"]
            self.quality = getQuality(self.title)
            self.episode = getNumbering(self.title)[1]
            self.season = getNumbering(self.title)[0]
            self.dir = dir.format(SeriesName=self.showname, SeasonNo=self.season)

        if entries:
            self.__dict__.update(entries['entries'])

    def __str__(self):
        if self.showname is not None:
            return "{:<24s} S{:02d}E{:02d} {:6s} {:12s} {:s}".format(self.showname, self.season, self.episode, self.quality, IState(self.state).name, self.title)
        else:
            return "None type"

    def filter_showname(self, filters):
            try:
                if self.showname not in filters['seriesname']:
                    return False
            except:
                pass
            return True

    def filter_quality(self, filters):
            try:
                if self.quality not in filters['quality']:
                    return False
            except:
                pass
            return True

    def filter(self, filters):
        if filters != None:
            if not self.filter_showname(filters):
                #log.debug("\t%s", self)
                return False
            if not self.filter_quality(filters):
                return False
        return True


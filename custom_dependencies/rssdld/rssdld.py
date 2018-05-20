import sys, os
import logging
import re
import json
from enum import Enum
from datetime import datetime, timedelta
from time import mktime
import feedparser

from .showsdb import ShowsDB
from .kodidb import KodiDB
from .episode import Episode, IState
from .transmission import Transmission

log = logging.getLogger(__name__)

class RSSdld(object):
    """"
    A class to read rss feed adn download it's items
    """

    def __init__(self, db, feeds, transmission, kodi):
        #log.debug('RSSdld object init')
        self.feeds = feeds
        self.transmission = transmission,
        self.kodi = kodi
        self.db = ShowsDB(db)
        #log.debug('init transmission client')
        self.tc = Transmission(transmission)
        #log.debug('init kodi client')
        self.kd = KodiDB(kodi)

    def close(self):
        self.db.close()

    def getFeedEpisodes(self, feed):
        pfeed = feedparser.parse(feed['uri'])
        items = []
        for item in pfeed["items"]:
            ep = Episode(item, feed['download_dir'])
            if ep.filter(feed['filters']):
                items.append(ep)
        return items

    def checkFeeds(self):
        # check rss feeds for new items
        log.debug("==== check rss and add new items to db")
        new = 0
        existing = 0
        for feed in self.feeds:
            for ep in self.getFeedEpisodes(feed):
                dbep = self.db.getEpisode(ep.hash)
                if not dbep:
                    ep.state = IState.NEW.value
                    # TODO: ep.date = now()
                    dbep = self.db.addEpisode(ep)
                    new += 1
                    log.debug('add to db : %s', dbep)
                else:
                    existing += 1
                    log.debug('existing  : %s', dbep)
        log.info('checked rss feeds: %d new items, %d exiting items', new, existing)

    def checkProgress(self):
        # add new items in transmission
        log.debug("==== check new items and add them to transmission")
        for ep in self.db.getEpisodes(IState.NEW.value):
            tcitem = self.tc.get(ep.hash)
            #log.debug('tc : %s', tcitem)
            if not tcitem:
                self.tc.add(ep.link, ep.dir)
                log.debug('add to tr : %s', ep)
            else:
                log.debug('existing  : %s', ep)
            ep.state = IState.DOWNLOADING.value
            self.db.updateEpisode(ep)

        # add finished items in kodi
        log.debug("==== check downloaded items and add them to kodi")
        for ep in self.db.getEpisodes(IState.DOWNLOADING.value):
            tcitem = self.tc.get(ep.hash)
            if tcitem:
                #log.debug('tc: %s', tcitem)
                if tcitem.progress != 100.0:
                    log.debug('downloadin: %s', ep)
                    self.tc.start(ep.hash) # might be paused
                else:
                    log.debug('finished  : %s', ep)
                    self.tc.stop(ep.hash)
                    # add to kodi
                    self.kd.updateLibPath(ep.dir)
                    # update state to UPDATING
                    ep.state = IState.UPDATING.value
                    self.db.updateEpisode(ep)
            else:
                log.debug('transmission item not found: %s', ep.hash)

        # mark items found in kodi as available
        log.debug("==== check items were added to kodi")
        for ep in self.db.getEpisodes(IState.UPDATING.value):
            ke = self.kd.getVideo(ep.showname, ep.season, ep.episode)
            if ke and ke.file:
                log.debug('in library: %s', ep)
                # update state to AVAILABLE
                ep.state = IState.AVAILABLE.value
                self.db.updateEpisode(ep)
                # remove from transmission
                self.tc.remove(ep.hash)
            else:
                log.debug('not found : %s', ep)
                #trigger another lib update
                self.kd.updateLibPath(ep.dir)

    def dumpDB(self):
        log.debug("==== get all db items with status")
        for ep in self.db.getEpisodes():
            log.info(ep)

    def getDBitems(self, state=-1, published=-1):
        lst = []
        for ep in self.db.getEpisodes(state, published):
            tr = self.tc.get(ep.hash)
            ke = self.kd.getVideo(ep.showname, ep.season, ep.episode)
            ep.torrent = tr;
            ep.library = ke;
            lst.append(ep)
            #s = json.dumps(ep, default=lambda x: x.__dict__)
            #log.info(s)
        return lst

                
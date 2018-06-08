
import os, sys, json
import logging
from datetime import datetime, timedelta
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_time_interval

# using the folowing requires manual dependencies install (see each custom dependency for requirements.txt)
sys.path.append(os.path.join(sys.path[0], "custom_dependencies"))
_LOGGER = logging.getLogger(__name__)

DOMAIN = "rssshows"
DEPENDENCIES = []

from rssdld.rssdld import RSSdld
from rssdld.episode import IState

EVENT_RSSSHOWS = "rssshows"
EVENT_RSSSHOWS_LATEST = "rssshows_latest"

ATTR_TEXT = 'text'

CONF_FEED_POLL_INTERVAL = 'feed_poll_interval'
DEF_FEED_POLL_INTERVAL = 360
CONF_LIB_UPDATE_INTERVAL = 'lib_update_interval'
DEF_LIB_UPDATE_INTERVAL = 60
CONF_FEEDS = 'feeds'
DEF_FEEDS = []
CONF_TRANSMISSION = 'transmission'
DEF_TRANSMISSION = None
CONF_KODI = 'kodi'
DEF_KODI = None


def setup(hass, config):
    """Set up the rssshows component. """
    feed_poll_inverval = config[DOMAIN].get(CONF_FEED_POLL_INTERVAL, DEF_FEED_POLL_INTERVAL)
    lib_update_interval = config[DOMAIN].get(CONF_LIB_UPDATE_INTERVAL, DEF_LIB_UPDATE_INTERVAL)
    feeds = config[DOMAIN].get(CONF_FEEDS, DEF_FEEDS)
    transmission = config[DOMAIN].get(CONF_TRANSMISSION, DEF_TRANSMISSION)
    kodi = config[DOMAIN].get(CONF_KODI, DEF_KODI)

    RSSshowsManager(feeds, transmission, kodi, feed_poll_inverval, lib_update_interval, hass)

    return True


class RSSshowsManager(object):

    def __init__(self, feeds, transmission, kodi, feed_poll_inverval, lib_update_interval, hass):
        self._feeds = feeds
        self._transmission = transmission
        self._kodi = kodi
        self._feed_poll_inverval = feed_poll_inverval
        self._lib_update_interval = lib_update_interval
        self._hass = hass
        self._last_check = 0
        self._lastep_time = None
        self._db = '/home/homeassistant/.homeassistant/shows.db'
        #self._db = os.path.join(sys.path[0], "shows.db")

        _LOGGER.debug('rssshows: setup component')

        self._feeds_poll()

        track_time_interval(hass, lambda now: self._lib_update(), interval=timedelta(seconds=self._lib_update_interval))
        track_time_interval(hass, lambda now: self._feeds_poll(), interval=timedelta(seconds=self._feed_poll_inverval))

        hass.services.register(DOMAIN, 'latest', lambda call: self._handle_latest(call))


    @staticmethod
    def _convert_time(time):
        #2018-05-10 22:51:52
        return datetime.strptime(time,"%Y-%m-%d %H:%M:%S")


    def _handle_latest(self, call):
        _LOGGER.debug('handle service get latest')

        rssdld = RSSdld(self._db, self._feeds, self._transmission, self._kodi)
        latest = rssdld.getDBitems(published = int(datetime.now().timestamp()) - 86400 * 30)
        rssdld.close()

        ev = {'latest': json.dumps(latest, default=lambda x: x.__dict__)}
        self._hass.bus.fire(EVENT_RSSSHOWS_LATEST, ev)
        _LOGGER.debug('EVENT_RSSSHOWS_LATEST: sent')


    def _update(self):
        _LOGGER.debug('Fetching status')

        rssdld = RSSdld(self._db, self._feeds, self._transmission, self._kodi)
        latest = rssdld.getDBitems(published = int(datetime.now().timestamp()) - 86400 * 7)
        rssdld.close()

        for ep in latest:
            _LOGGER.debug("{:<24s} S{:02d}E{:02d} {:12s} {:s} {:4d}% {:s} pc:{:f}".format(ep.showname, ep.season, ep.episode, IState(ep.state).name, ep.title, 
                ep.torrent.progress if ep.torrent else -1, 
                ep.library.dateadded if ep.library else 'none',
                ep.library.playcount if ep.library else -1))
            
        new = sum((ep.state == IState.NEW.value) for ep in latest)
        downloading = sum((ep.state > IState.NEW.value and ep.state < IState.AVAILABLE.value) for ep in latest)
        unwatched = sum((ep.library != None and ep.library.playcount <= 0) for ep in latest)

        self._hass.states.set('rssshows.status', '{0} new, {1} downloading, {2} unwatched'.format(new, downloading, unwatched), 
            {'icon': 'mdi:video-account', 'friendly_name' : 'Status'})
        _LOGGER.debug('status: {0}'.format(self._hass.states.get('rssshows.status')))

        diff = datetime.now() - self._last_check
        (minutes, sec) = divmod(diff.days * 86400 + diff.seconds, 60)
        self._hass.states.set('rssshows.last_check', '{0} minute(s) ago'.format(minutes), 
            {'icon': 'mdi:timelapse', 'friendly_name' : 'Last check'})
        _LOGGER.debug('last check: {0}'.format(self._hass.states.get('rssshows.last_check')))

        for ep in latest:
            if ep.library:
                lastep_time = self._convert_time(ep.library.dateadded)
                if self._lastep_time == None or lastep_time < self._lastep_time:
                    #self._hass.states.set('rssshows.latest_shows', '{0}'.format(ep.library.dateadded if ep.library else 'none'))
                    #_LOGGER.debug('latest shows: {0}'.format(self._hass.states.get('rssshows.latest_shows')))
                    ev = {ATTR_TEXT: "{:s} S{:02d}E{:02d} {:s}".format(ep.showname, ep.season, ep.episode, ep.title)}
                    self._hass.bus.fire(EVENT_RSSSHOWS, ev)
                    _LOGGER.debug('EVENT_RSSSHOWS: {0}'.format(ev)) 
                    self._lastep_time = lastep_time

        #_LOGGER.debug('get latest shows')
        #available = [ep for ep in latest if ep.library]
        #s = json.dumps(available, default=lambda x: x.__dict__)
        #self._hass.states.set('rssshows.latest_shows', '{0}'.format(s))
        #_LOGGER.debug('latest shows: {0}'.format(self._hass.states.get('rssshows.latest_shows')))
        #_LOGGER.debug('latest shows: count {0}'.format(len(available)))

    def _lib_update(self):
        _LOGGER.debug('Update library')
        rssdld = RSSdld(self._db, self._feeds, self._transmission, self._kodi)
        rssdld.checkProgress()
        rssdld.close()

        self._update()

    def _feeds_poll(self):
        _LOGGER.debug('poll feeds')
        for feed in self._feeds:
            _LOGGER.info('rss feed: %s', feed['uri'])
        rssdld = RSSdld(self._db, self._feeds, self._transmission, self._kodi)
        rssdld.checkFeeds()
        rssdld.close()

        self._last_check = datetime.now()
        self._hass.states.set('rssshows.last_check', 'now')
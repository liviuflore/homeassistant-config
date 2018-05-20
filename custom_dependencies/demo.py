#!/usr/bin/env python3
"""Demo file showing how to use the rssdld library."""

import argparse
import re
import logging
import sys
from datetime import datetime
from time import mktime
from threading import Timer

from rssdld.rssdld import RSSdld
from rssdld.episode import IState


def_config = {
    "feed_poll_interval": 30,
    "lib_update_interval": 10,
    "feeds": [
        {
            #"uri" : "http://showrss.info/show/879.rss",
            "uri" : "http://showrss.info/user/7947.rss?magnets=true&namespaces=true&name=null&quality=null&re=null",
            "download_dir" : "/media/Media/Series/{SeriesName}/Season{SeasonNo:02}/",
            "filters": {
                "SeriesName": ["Timeless", "Fear The Walking Dead", "Westworld", "Colony", "The Expanse", "The 100", "Elementary", "Star Trek Discovery"], 
                "Quality": ["720p"]
            }
        }
    ],
    "transmission": {
        "host": '192.168.1.21',
        "port": 9091,
        "username": "osmc",
        "password": "osmc"
    },
    "kodi": {
        "host": '192.168.1.21',
        "port": 8080,
        "username": "osmc",
        "password": "liviu22"
    }
}


def main():
    """Main function.
    Mostly parsing the command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.json')
    parser.add_argument('-v', '--verbose', action='store_const', const=True)
    args = parser.parse_args()

    # logging
    FORMAT = '%(asctime)-15s %(levelname)-7s %(name)-20s %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG if args.verbose else logging.INFO)

    config = def_config #json.loads(open(args.config))

    downloader = RSSdld('shows.db', config['feeds'], config['transmission'], config['kodi'])

    downloader.checkFeeds()
    downloader.checkProgress()
    #downloader.dumpDB()

    now = int(datetime.now().timestamp())
    # published last day
    for ep in downloader.getDBitems(published = now - 86400 * 7):
        logging.info("{:<24s} S{:02d}E{:02d} {:12s} {:s} {:4d}% {:s}".format(ep.showname, ep.season, ep.episode, IState(ep.state).name, ep.title, ep.torrent.progress if ep.torrent else -1, ep.library.dateadded if ep.library else 'none'))


if __name__ == '__main__':
    main()
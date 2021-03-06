"This module contains feeds-related classes."
import datetime
import sqlite3
from collections import namedtuple
import xml.etree.ElementTree as ET
import feedparser
from dateutil.parser import parse
from apscheduler.schedulers.blocking import BlockingScheduler


DATA_SUBDIR = "rssind/"

Entry = namedtuple("Entry", ['id', 'title', 'link', 'description', 'pub_date'])


class Feed(object):
    """Feed class represents a single news feed."""

    def __init__(self, data, feed_repo):
        """data is the dict representing feed data.
        feed_repo is a FeedRepository object."""
        super(Feed, self).__init__()
        self.url = data['url']
        self.name = data.get('name')
        read_stamp = data.get("last_read")
        if read_stamp:
            self.last_read = datetime.datetime.fromtimestamp(read_stamp, tz=datetime.timezone.utc)
        else:
            self.last_read = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
        self._repo = feed_repo

    def update(self):
        "Updates the feed via network and saves new entries into the database."
        self._repo._update_feed(self)

    def set_read_date(self, datetime_obj=None):
        "Sets the feed's last read date. If datetime is None, uses current time."
        if datetime_obj:
            self.last_read = datetime_obj
        else:
            self.last_read = datetime.datetime.now(tz=datetime.timezone.utc)
        self._save()

    def get_new_entries(self):
        "Returns unread news entries from the database."
        return self._repo._get_feed_entries(self, True)

    def _save(self):
        "Saves feed data into the database."
        self._repo._save_feed(self)

    def __repr__(self):
        return "<Feed url:{} name:{} last_read:{}>".format(
            self.url, self.name, self.last_read.isoformat()
            )


class FeedRepository(object):
    """FeedRepository manages the collection of feeds,
    including storage."""

    def __init__(self, db_path=None):
        super(FeedRepository, self).__init__()
        self.db_path = db_path
        self._load_feeds()

    def _load_feeds(self):
        "Loads the feeds from the database."

        def _read_feed_data():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM feeds;")
                self.feeds = [Feed(dict(zip(data.keys(), data)), self) for data in cur]
                cur.close()

        def _create_schema():
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(
                    """CREATE TABLE feeds (
                            url text PRIMARY KEY,
                            name text NOT NULL,
                            last_read numeric NOT NULL
                        );

                    CREATE TABLE entries (
                            id text PRIMARY KEY,
                            feed_url text NOT NULL,
                            title text,
                            link text,
                            description text,
                            pub_date numeric NOT NULL,
                            FOREIGN KEY (feed_url) REFERENCES feeds (url) ON DELETE CASCADE
                        );

                    CREATE INDEX pub_date ON entries (pub_date);
                    """)

        if self.db_path:
            _read_feed_data()
        else:
            from xdg.BaseDirectory import xdg_data_home
            from os.path import join
            self.db_path = join(xdg_data_home, DATA_SUBDIR + "rssind.db")
            try:
                _read_feed_data()
            except sqlite3.OperationalError:
                from os import makedirs
                makedirs(join(xdg_data_home, DATA_SUBDIR), exist_ok=True)
                _create_schema()
                self.feeds = []

    def _update_feed(self, feed):
        "Updates the feed via network and saves new entries into the database."
        feed = feedparser.parse(feed.url)
        with sqlite3.connect(self.db_path) as conn:
            for entry in feed.entries:
                # > news feed entries not having publishing date and/or id
                # fucking genius idea
                if 'published' not in entry:
                    pub_date = datetime.datetime.now(tz=datetime.timezone.utc)
                else:
                    pub_date = parse(entry.published)
                conn.execute(
                    """INSERT OR IGNORE INTO
                    entries (id, feed_url, title, link, description, pub_date)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """, (entry.get('id', entry.title), feed.url, entry.title,
                          entry.link, entry.get('description', ''), pub_date.timestamp())
                    )

    def _save_feed(self, feed):
        "Saves feed data into the database."
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT OR REPLACE INTO feeds (url, name, last_read) VALUES
                (?, ?, ?);
                """, (feed.url, feed.name, feed.last_read.timestamp()))

    def _get_feed_entries(self, feed, new_only=False):
        "Gets feed entries from the database."
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if new_only:
                cur.execute(
                    """ SELECT id, title, link, description, pub_date FROM entries
                        WHERE feed_url = ? AND pub_date > ?
                        ORDER BY pub_date ASC;
                    """, (feed.url, feed.last_read.timestamp()))
            else:
                cur.execute(
                    """ SELECT id, title, link, description, pub_date FROM entries
                        WHERE feed_url = ? ORDER BY pub_date ASC;
                    """, (feed.url))
            return [Entry(*r) for r in cur]

    def add_by_url(self, feed_url, name=None):
        """Permanently adds a new feed.
        If name is None then it is requested from the feed itself over the network."""
        feed_data = {"url": feed_url}
        if name:
            feed_data['name'] = name
        else:
            f = feedparser.parse(feed_url)
            feed_data['name'] = f.feed.title
        feed = Feed(feed_data, self)
        feed._save()
        self.feeds.append(feed)

    def import_opml(self, path):
        """This method imports a set of feeds from the OPML file designated by path."""
        tree = ET.parse(path)
        root = tree.getroot()
        for feed_el in root.find('body').findall('outline'):
            if feed_el.get('type') == 'rss':
                self.add_by_url(feed_el.get('xmlUrl'), feed_el.get('text'))

    def check_feeds(self):
        """Updates all feeds and returns a list of feeds which have new entries.
        """
        lst = []
        for feed in self.feeds:
            feed.update()
            if feed.get_new_entries():
                lst.append(feed)
        return lst

    def start_updater(self, interval, clbk):
        """Starts feed autoupdater with the specified interval in minutes.
        The callback will be called with a list of feeds which have new entries.
        This is a blocking call."""
        self._scheduler = BlockingScheduler(executors={
            'default': {'type': 'threadpool', 'max_workers': 1}
            })

        def job():
            clbk(self.check_feeds())

        self._scheduler.add_job(job, trigger='interval', minutes=interval)
        self._scheduler.start()

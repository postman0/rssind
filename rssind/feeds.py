"This module contains feeds-related classes."
import datetime
import sqlite3
from collections import namedtuple
import feedparser
import apscheduler
from dateutil.parser import parse
from dateutil.tz import tzutc


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
        readstr = data.get("last_read")
        if readstr:
            self.last_read = parse(readstr)
        else:
            self.last_read = datetime.datetime.min.replace(tzinfo=tzutc())
        self._repo = feed_repo

    def update(self):
        "Updates the feed via network and saves new entries into the database."
        self._repo._update_feed(self)

    def set_read_date(self, datetime_obj=None):
        "Sets the feed's last read date. If datetime is None, uses current time."
        if datetime_obj:
            self.last_read = datetime_obj
        else:
            self.last_read = datetime.datetime.now(tzutc())
        self._save()

    def get_new_entries(self):
        return self._repo._get_feed_entries(self, True)

    def _save(self):
        "Saves feed data into the database."
        self._repo._save_feed(self)


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
                            last_read text NOT NULL
                        );

                    CREATE TABLE entries (
                            id text PRIMARY KEY,
                            feed_url text,
                            title text,
                            link text,
                            description text,
                            pub_date text NOT NULL,
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
                conn.execute(
                    """INSERT OR IGNORE INTO
                    entries (id, feed_url, title, link, description, pub_date)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """, (entry.id, feed.url, entry.title,
                          entry.link, entry.description, parse(entry.published).isoformat())
                    )

    def _save_feed(self, feed):
        "Saves feed data into the database."
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT OR REPLACE INTO feeds (url, name, last_read) VALUES
                (?, ?, ?);
                """, (feed.url, feed.name, feed.last_read.isoformat()))

    def _get_feed_entries(self, feed, new_only=False):
        "Gets feed entries from the database."
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if new_only:
                cur.execute(
                    """ SELECT id, title, link, description, pub_date FROM entries
                        WHERE feed_url = ? AND pub_date > ? ORDER BY pub_date ASC;
                    """, (feed.url, feed.last_read.isoformat()))
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

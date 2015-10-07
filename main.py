"rssind is a yet another rss feeds aggregator."
from rssind import RssIndicator


def main():
    "Starts the application."
    rssind = RssIndicator()
    rssind.start()

if __name__ == '__main__':
    main()

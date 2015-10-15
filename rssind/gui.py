"This module contains GUI classes."
from gi.repository import Gtk, AppIndicator3
from signal import signal, SIGINT, SIG_DFL
from .feeds import FeedRepository


class RssIndicator(object):
    "The main GUI class responsible for the indicator in the system tray."

    def __init__(self, ind_id="RssIndicator"):
        "ind_id is the indicator's id."

        self.ind_id = ind_id
        self.ind = AppIndicator3.Indicator.new(
            self.ind_id, "application-rss+xml",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.rebuild_menu()

    def rebuild_menu(self, new_feeds=None):
        "Builds indicator's menu from new feed entries."
        menu = Gtk.Menu()
        for feed in new_feeds or []:
            itm = Gtk.ImageMenuItem.new_from_stock("application-rss+xml", None)
            itm.set_label(feed.name)
            menu.append(itm)
            for entry in feed.get_new_entries():
                menu.append(Gtk.MenuItem.new_with_label(entry.title))
        menu.append(Gtk.SeparatorMenuItem())
        exit_item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        exit_item.connect("activate", Gtk.main_quit)
        menu.append(exit_item)
        menu.show_all()
        self.ind.set_menu(menu)

    def start(self):
        "This method starts the application."
        self.feed_repo = FeedRepository()
        self.rebuild_menu(self.feed_repo.check_feeds())
        signal(SIGINT, SIG_DFL)
        Gtk.main()

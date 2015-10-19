"This module contains GUI classes."
from threading import Thread
from gi.repository import Gtk, Gdk, AppIndicator3, GLib
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

    def rebuild_menu(self, new_feeds=None):
        "Builds indicator's menu from new feed entries."

        menu = Gtk.Menu()
        def _set_feed_as_read(feed, menu_item):
            feed.set_read_date()
            # loop over the children, removing items from the read feed
            found = False
            for item in menu:
                if found:
                    if type(item) == Gtk.MenuItem:
                        print(item)
                        menu.remove(item)
                    else:
                        break
                else:
                    if item is menu_item:
                        found = True
                        menu.remove(item)

        for feed in new_feeds or []:
            itm = Gtk.ImageMenuItem.new_from_stock("application-rss+xml", None)
            itm.set_label(feed.name)
            itm.connect("activate", 
                (lambda feed: lambda menu_item: _set_feed_as_read(feed, menu_item))(feed))
            menu.append(itm)
            for entry in feed.get_new_entries():
                entry_item = Gtk.MenuItem.new_with_label(entry.title)
                entry_item.connect("activate",
                    (lambda entry:
                        lambda menuitem: Gtk.show_uri(None, entry.link, Gdk.CURRENT_TIME))(entry))
                menu.append(entry_item)
        menu.append(Gtk.SeparatorMenuItem())
        exit_item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        exit_item.connect("activate", Gtk.main_quit)
        menu.append(exit_item)
        menu.show_all()
        self.ind.set_menu(menu)

    def _start_updater(self):
        self._upd_thread = Thread(target=lambda:
            self.feed_repo.start_updater(5, #TODO how do i configure this shit
                lambda feeds: GLib.idle_add(self.rebuild_menu, feeds)))
        self._upd_thread.daemon = True
        self._upd_thread.start()

    def start(self):
        "This method starts the application."
        self.feed_repo = FeedRepository()
        self.rebuild_menu(self.feed_repo.check_feeds())
        self._start_updater()
        signal(SIGINT, SIG_DFL)
        Gtk.main()

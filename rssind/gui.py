"This module contains GUI classes."
from gi.repository import Gtk, AppIndicator3
from signal import signal, SIGINT, SIG_DFL


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

        exit_item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        exit_item.connect("activate", Gtk.main_quit)
        self.menu = Gtk.Menu()
        self.menu.append(exit_item)
        self.menu.show_all()

        self.ind.set_menu(self.menu)

    @staticmethod
    def start():
        "This method starts the application."

        signal(SIGINT, SIG_DFL)
        Gtk.main()

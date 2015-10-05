from gi.repository import Gtk, AppIndicator3
from signal import signal, SIGINT, SIG_DFL

class RssIndicator(object):
	"The main GUI class."

	def __init__(self, id="RssIndicator"):
		"id is the indicator's id."

		self.id = id
		self.ind = AppIndicator3.Indicator.new(self.id, "application-rss+xml", AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
		self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
		self.ind.set_menu(Gtk.Menu())


	def start(self):
		"This method starts the application."

		signal(SIGINT, SIG_DFL)
		Gtk.main()

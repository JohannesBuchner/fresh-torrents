
import pygtk
pygtk.require('2.0')
import gtk
import time
from threading import Thread


def find_child_by_name(window, name):
	r = find_child_by_name_recurse(window, name)
	if r == False:
		raise LookupError("GUI item '%s' could not be found"  % name)
	else:
		return r
		

def find_child_by_name_recurse(window, name):
	if not isinstance(window, (gtk.Container, gtk.Window)):
		return False
	for c in window.get_children():
		if c.get_name() == name:
			return c
		else:
			r = find_child_by_name_recurse(c, name)
			if r != False:
				return r
	return False



class TitleCountUpdater(Thread):
	running = True
	def __init__(self, titlepattern, window, model):
		self.model = model
		self.window = window
		self.titlepattern = titlepattern
		Thread.__init__(self)
	def stop(self):
		self.running = False
	def run(self):
		while self.running:
			print 'model now supports:',self.model.get_n_columns()
			self.window.set_title(self.titlepattern % (self.model.get_n_columns(),))
			time.sleep(4)


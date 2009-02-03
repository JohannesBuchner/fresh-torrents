#!/usr/bin/env python

copyright = """
Copyright (c) 2008, Johannes Buchner
All rights reserved.
"""
license = """
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY <copyright holder> ``AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
import re
import pango
import webbrowser

from freshtorrentshelpers import *

gtk.gdk.threads_init()

prog_name = "freshtorrents"
prog_comments = """Finds popular torrents"""
prog_version = "1.0.1"
prog_authors = ['Johannes Buchner']
prog_copyright = copyright
prog_license = license
prog_website = "http://freshtorrents.sourceforge.net/"

prog_help_text = """Fresh Torrents (%s)

It provides you with an alternative view on popular, cheap (bandwidth-wise) and new torrents giving you infinite filtering freedom.

You can find new torrents with an high amount of seeders/leechers. The weighing of what is important to you (number of seeders, number of leechers, age) is in your hands.

Additionally, you can filter out torrents (e.g. older than n days, less than n seeders, etc.).

Go to the website for more usage hints and for new versions (more features, etc.)!

http://freshtorrents.sf.net/"""

gladefilename = "freshtorrents.glade"
window = 'freshtorrents'
title = 'Fresh torrents'
gladefile = os.path.join(os.path.dirname(sys.argv[0]), gladefilename)

(NAME_COLUMN,
DESC_COLUMN, 
TORRENT_COLUMN,
AGE_COLUMN,
SIZE_COLUMN,
SEEDERS_COLUMN,
LEECHERS_COLUMN,
WEIGHTED_VALUE_COLUMN) = range(8)

class FreshTorrents:
	wTree = None
	mainwindow = None
	engine = None
	age, seeders, leechers = (None, None, None)
	age_min, seeders_min, leechers_min = (None, None, None)
	age_max, seeders_max, leechers_max = (None, None, None)
	results = None
	model = None
	
	def __init__(self):
		self.wTree = gtk.glade.XML(gladefile) 
		self.mainwindow = self.wTree.get_widget(window)
		if not (self.mainwindow):
			print "No such window. "
			sys.exit(2)
		self.mainwindow.show_all()
		self.mainwindow.set_title(title)
		self.mainwindow.connect("destroy", self.on_quit)
		self.init_signals(self.wTree, "on_")
		
		self.statusbar = find_child_by_name(self.mainwindow, 'statusbar')
		
		self.age = find_child_by_name(self.mainwindow, 'age')
		self.seeders = find_child_by_name(self.mainwindow, 'seeders')
		self.leechers = find_child_by_name(self.mainwindow, 'leechers')
		
		self.age_min = find_child_by_name(self.mainwindow, 'age_min')
		self.seeders_min = find_child_by_name(self.mainwindow, 'seeders_min')
		self.leechers_min = find_child_by_name(self.mainwindow, 'leechers_min')
		
		self.age_max = find_child_by_name(self.mainwindow, 'age_max')
		self.seeders_max = find_child_by_name(self.mainwindow, 'seeders_max')
		self.leechers_max = find_child_by_name(self.mainwindow, 'leechers_max')
		
		self.content = find_child_by_name(self.mainwindow, 'content')	
		self._apply_weight()
		self._apply_min()
		self._apply_max()
		
		self.model = gtk.ListStore( str, str, str, long, long, long, long, long )
		self.content.set_model(self.model)
		#self.content.set_headers_visible(False)
		self.content.append_column( gtk.TreeViewColumn('name', gtk.CellRendererText(), text=NAME_COLUMN ))
		# 1: descurl
		# 2: torrenturl
		self.content.append_column( gtk.TreeViewColumn('age', gtk.CellRendererText(), text=AGE_COLUMN ))
		self.content.append_column( gtk.TreeViewColumn('MB', gtk.CellRendererText(), text=SIZE_COLUMN ))
		self.content.append_column( gtk.TreeViewColumn('seeders', gtk.CellRendererText(), text=SEEDERS_COLUMN ))
		self.content.append_column( gtk.TreeViewColumn('leechers', gtk.CellRendererText(), text=LEECHERS_COLUMN ))
		# 6: weighted value
		self.content.append_column( gtk.TreeViewColumn('weight', gtk.CellRendererText(), text=WEIGHTED_VALUE_COLUMN ))
		
		self.model.set_sort_column_id(WEIGHTED_VALUE_COLUMN, gtk.SORT_DESCENDING)

		self.content.set_search_column(NAME_COLUMN)
		self.content.set_search_equal_func(self.search_function)
		
		self.update_progress()
		#on_backend_update("thepiratebay|205") # for DEBUGGING
	
	def init_signals(self, tree, beginstr):
		dict = {}
		for key in dir(self.__class__):
			if key.startswith(beginstr):
				dict[key] = getattr(self, key)
		tree.signal_autoconnect(dict)
	
	def on_quit(self, param):
		print "Quitting program. Thanks for using."
		if self.engine is not None:
			self.engine.stop()
		gtk.main_quit()

	def on_about(self, param):	
		about_dialog = self.wTree.get_widget("about_dialog")
		about_dialog.set_name(prog_name)
		about_dialog.set_comments(prog_comments)
		about_dialog.set_version(prog_version)
		about_dialog.set_copyright(prog_copyright)
		about_dialog.set_license(prog_license)
		about_dialog.set_authors(prog_authors)
		about_dialog.run()
		about_dialog.hide()
	
	def on_help(self, param):
		secondary_text = prog_help_text % prog_version
		text = prog_comments
		msg = gtk.MessageDialog(self.mainwindow, gtk.DIALOG_MODAL | 
			gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, 
			str(text))
		msg.format_secondary_text(secondary_text)
		msg.run()
		msg.destroy()
		
	def problem(self, msg):
		self.errormsg(self.mainwindow, msg)
	
	def info(self, msg):
		self.errormsg(self.mainwindow, msg, gtk.MESSAGE_INFO)
	
	def errormsg(self, parent, msg, type=gtk.MESSAGE_ERROR):
		text = str(msg).replace("&","&amp;").replace("<","&gt;").replace(">","&lt;")
		
		if parent == None:
			parent = self.mainwindow
		dialog = gtk.MessageDialog(parent, 
			gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL, 
			type, gtk.BUTTONS_OK, text)
		dialog.run()
		dialog.destroy()
	
		
	def ask(self, question, information):
		def responseToDialog(entry, dialog, response):
			dialog.response(response)
		
		dialog = gtk.MessageDialog(
			None,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_QUESTION,
			gtk.BUTTONS_OK,
			None)
		dialog.set_markup(question)
		entry = gtk.Entry()
		entry.connect("activate", responseToDialog, dialog, gtk.RESPONSE_OK)
		hbox = gtk.HBox()
		hbox.pack_start(gtk.Label("Name:"), False, 5, 5)
		hbox.pack_end(entry)
		dialog.format_secondary_markup(information)
		dialog.vbox.pack_end(hbox, True, True, 0)
		dialog.show_all()
		print dialog.run()
		text = entry.get_text()
		dialog.destroy()
		return text
	
	# This should be fast
	def search_function(self, model, column, key, iter, data=None): 
		criteria = (key.lower().replace("."," ")).split(" ")
		values = self.model.get_value(iter, NAME_COLUMN).lower().replace("."," ").split(" ")
		weight = self.model.get_value(iter, WEIGHTED_VALUE_COLUMN)
		if weight == 0:
			return True
		
		missing_criteria = filter(lambda c:c.strip() != "" and c.strip() not in values, criteria)
		#print "searching: ",criteria, values, missing_criteria
		if len(missing_criteria) == 0:
			return False
		if len(missing_criteria) == 1: # typing not done yet?
			missing_criterium = missing_criteria[0]
			if criteria[-1] == missing_criterium:
				# you get a last chance
				for v in values:
					if v.__contains__(missing_criterium):
						return False
		return True
	
	def on_backend_update(self, a=None, b=None, c=None, d=None, e=None, f=None):
		(backendname, category) = a.get_tooltip_text().split("|")
		modulename = backendname.lower().replace(" ","")
		classname  = backendname.title().replace(" ","")
		
		if category == "":
			category = self.ask("<b>Category ID?</b>", 
				"Please enter a category ID for " + modulename + ".\n"+
				"You can find this information on the providers website (a part of the url). ")
			# TODO: ask user for category id
		if category is None:
			return
		try:
			backend = __import__(modulename)
			backend = reload(backend)
		
			self.select_engine(getattr(backend, classname), category)
		except StandardError, e:
			print e
			self.problem("""Loading backend %s failed.
			
Maybe the backend isn't implemented yet."""%modulename)
			
		
	def select_engine(self, backendclass, subtype):
		if self.engine is not None:
			self.engine.stop()
		
		self.engine = backendclass(self, subtype)
		self.model.clear()
		self.engine.start()
		for i in range(5):
			self.on_fetch_more()
		self.statusbar.set_text("engine started")

	def __call__(self, value):
		if value is None:
			self.statusbar.set_text("Fetched: %d entries" % self.engine.get_entries_count())
			return
		
		row = [
				value['name'], value['descurl'], value['torrenturl'], 
				int(value['age']), int(value['size']/1024/1024), 
				int(min(sys.maxint,int(value['seeders']))), int(min(sys.maxint,int(value['leechers']))), 
				0
			]
		iter = self.model.append( row )
		self.model.set(iter, WEIGHTED_VALUE_COLUMN, self.calc_weight(iter))

	def on_content_row_activated(self, b, c=None, e=None, f=None, g=None):
		self.open_link(False)
	
	def open_link(self, direct=False):
		(view, iter) = self.content.get_selection().get_selected()
		torrenturl = view.get_value(iter, TORRENT_COLUMN)
		descurl = view.get_value(iter, DESC_COLUMN)
		if direct: 
			url = torrenturl
		else: 
			url = descurl
		webbrowser.open(url)
	
	def on_fetch_more(self, a=None):
		if self.engine is None:
			self.problem("No backend selected!")
		else:
			self.statusbar.set_text("fetching entries")
			self.engine.push_entries_limit()
		
		
	def on_content_button_press_event(self, treeview, event, e=None, f=None, g=None):
		treeview.grab_focus()
		# Figure out which item they right clicked on
		path = treeview.get_path_at_pos(int(event.x),int(event.y))
		# Get the selection
		selection = treeview.get_selection()

		# Get the selected path(s)
		rows = selection.get_selected_rows()

		# If they didnt right click on a currently selected row, change the selection
		if rows is None or path[0] not in rows[1]:
			selection.unselect_all()
			selection.select_path(path[0])

		if event.button == 3:
			self.open_link(False)
		if event.button == 2:
			self.open_link(True)
		return True
	
	def _apply_weight(self):
		self.s_weight = self.seeders.get_value()
		self.l_weight = self.leechers.get_value()
		self.a_weight = self.age.get_value()
	
	def on_apply_clicked(self, b=None):
		self._apply_weight()
		self.apply_filter()
	
	def apply_filter(self):
		self.content.freeze_child_notify()
		# we hang out the model to pause sorting
		oldmodel = self.content.get_model()
		self.content.set_model(None)
		self.model.set_default_sort_func( (lambda m, it1, it2, data=None : 0) )
		# iterating would not be possible if the sorting would happen all the time
		self.model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
		
		self.statusbar.set_text("filtering ...")
		iter = self.model.get_iter_first()
		n = 0
		while iter is not None:
			n = n + 1
			self.model.set_value(iter, WEIGHTED_VALUE_COLUMN, self.calc_weight(iter))
			iter = self.model.iter_next(iter)
			

		self.statusbar.set_text("%s entries filtered and sorted" % (n,))
		
		# ok, now we can sort
		self.model.set_sort_column_id(WEIGHTED_VALUE_COLUMN, gtk.SORT_DESCENDING)
		self.content.thaw_child_notify()
		self.content.set_model(oldmodel)
	
	def update_progress(self):
		pass
			
	def on_apply_max_clicked(self, b=None):
		self._apply_max()
		self.apply_filter()
	
	def _apply_max(self):
		self.s_max = self.seeders_max.get_value()
		if self.s_max == -1:
			self.s_max = None
		self.l_max = self.leechers_max.get_value()
		if self.l_max == -1:
			self.l_max = None
		self.a_max = self.age_max.get_value()
		if self.a_max == -1:
			self.a_max = None
				
	def on_apply_min_clicked(self, b=None):
		self._apply_min()
		self.apply_filter()
	
	def _apply_min(self):
		self.s_min = self.seeders_min.get_value()
		if self.s_min == -1:
			self.s_min = None
		self.l_min = self.leechers_min.get_value()
		if self.l_min == -1:
			self.l_min = None
		self.a_min = self.age_min.get_value()
		if self.a_min == -1:
			self.a_min = None
	
	# this function should be fast
	def calc_weight(self, iter):
		a = self.model.get_value(iter, AGE_COLUMN)
		s = self.model.get_value(iter, SEEDERS_COLUMN)
		l = self.model.get_value(iter, LEECHERS_COLUMN)
		if self.a_min is not None and a < self.a_min: return 0
		if self.a_max is not None and a > self.a_max: return 0
		if self.s_min is not None and s < self.s_min: return 0
		if self.s_max is not None and s > self.s_max: return 0
		if self.l_min is not None and l < self.l_min: return 0
		if self.l_max is not None and l > self.l_max: return 0
		return min(sys.maxint, a*self.a_weight + s*self.s_weight + l*self.l_weight)
		

if __name__ == "__main__":
	gs = FreshTorrents()
	gtk.main()


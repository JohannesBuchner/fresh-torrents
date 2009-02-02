import urllib
import re
import os
from threading import Thread
import time
import datetime
import tempfile 

MAX_AGE = 24 # hours

class TorrentSite(Thread):
	callback = None
	category = None
	queries = 0
	running = True
	entries_limit = 0
	entries = 0
	page = 0
	
	def __init__(self, cb, category, tmpdir = None):
		Thread.__init__(self)
		self.callback = cb
		self.category = category
		if tmpdir is None:
			d = tempfile.mkdtemp()
			tmpdir = os.path.dirname(d)
			os.rmdir(d)
		self.tmpdir = os.path.join(tmpdir, self.get_backend_name())
		self._checktmp()
	
	def push_entries_limit(self, n = 5*30):
		self.entries_limit = self.entries_limit + n
	
	def get_entries_count(self):
		return self.entries
	
	def run(self):
		while self.running:
			while self.running and self.entries < self.entries_limit:
				current_entries = self._fetch_current_entries()
				
				self.page = self.page + 1
				self.entries = self.entries + len(current_entries)
				self.callback(None)
				
				if len(current_entries) == 0: # the site ran out of torrents ...
					self.entries_limit = self.entries - 1
				
				for entry in current_entries:
					self.callback(entry)
			
			self.callback(None)
			time.sleep(1)

	def stop(self):
		self.running = False

	def _get_next_unparsed_content(self):
		if self.queries % 4 == 3:
			for i in range(30):
				if self.running:
					time.sleep(0.3)
		url = self.urlschema % { 'category':self.category, 'n':self.page }
		print "loading", url
		page = urllib.urlopen(url)
		self.queries = self.queries + 1
		return "".join(page.readlines())

	def _checktmp(self):
		if not os.access(self.tmpdir, os.F_OK):
			try:
				os.mkdir(self.tmpdir)
			except Exception, e:
				print "creating cachedir failed: ", e
				return false
	
	def parse_size(self, size, unit):
		factor = 1
		size = float(size)
		unit = unit.lower()
		if unit == 'gib':
			factor = 1000*1000*1000
		elif unit == 'mib':
			factor = 1000*1000
		elif unit == 'kib':
			factor = 1000
		elif unit == 'gb':
			factor = 1024*1024*1024
		elif unit == 'mb':
			factor = 1024*1024
		elif unit == 'kb':
			factor = 1024
		return int(factor*size)

	def _cacher(self, n):
		self._checktmp()
		cachefilename = os.path.join(self.tmpdir, "%s-%s-%s.page" % (self.backendname, self.category, n))
		
		try:
			if int(time.time() - os.stat(cachefilename).st_mtime) < 60*60*MAX_AGE:
				f = file(cachefilename, 'r')
				return "".join(f.readlines())
		except Exception, e: 
			pass
		line = self._get_next_unparsed_content()
		if line is None:
			return None
		
		try:
			self._write_to_cache(line, cachefilename)
		except Exception, e: 
			pass
		return line
	
	def _write_to_cache(self, content, cachefilename):
		f = file(cachefilename, 'w')
		f.write(content)
		f.close()
	
	def cleanup_string(self, name):
		return name.replace("\n"," ").strip()


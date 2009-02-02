import urllib
import re
import os
from threading import Thread
import time
import datetime



spacer = '[^<>]*'
start = '<tr[^<>]*>'
name = '<td[^<>]*><a[^<>]*>[^<>]*</a></td>[^<>]*<td><a.href="([^"]*)".class="detLink"[^<>]*>([^<>]*)</a></td>'
date = '<td>([^<>]*)</td>'
torrenturl = '<td><a.href="([^"]*)"[^<>]*><img[^<>]*></a>(?:[^<>]*<img[^<>]*>)*</td>'
size = '<td[^<>]*>([.0-9]*)&nbsp;([A-Za-z]*)</td>'
seeders = '<td[^<>]*>([0-9]*)</td>'
leechers = '<td[^<>]*>([0-9]*)</td>'
end = '</tr>'

exp = start + spacer + name + spacer + date + spacer + torrenturl + spacer + size + spacer + seeders + spacer + leechers  + spacer + end

MAX_AGE = 24 # hours
ENTRIES_PER_PAGE = 30

class Thepiratebay(Thread):
	callback = None
	category = None
	urlschema = 'http://thepiratebay.org/browse/%(category)s/%(n)s/7'
	entryschema = ''
	page = 0
	queries = 0
	running = True
	entries_limit = 0
	entries = 0
	
	def __init__(self, cb, category, tmpdir = '/tmp/tpb/'):
		Thread.__init__(self)
		self.callback = cb
		self.category = category
		self.tmpdir = tmpdir
	
	def push_entries_limit(self, n=5*ENTRIES_PER_PAGE):
		self.entries_limit = self.entries_limit + n
		print "limit is now", self.entries_limit
	
	def get_entries_count(self):
		return self.entries
	
	def run(self):
		while self.running:
			while self.running and self.entries < self.entries_limit:
				entries = self._fetch_current_entries()
				for entry in entries:
					self.callback(entry)
				self.page = self.page + 1
				self.entries = self.entries + len(entries)
				self.callback(None)
				#time.sleep(0.3)
			
			self.callback(None)
			time.sleep(1)

	def stop(self):
		self.running = False

	def _fetch_current_entries(self):
		page = self._cacher(self.page)
		ms = re.findall(exp, page, re.MULTILINE | re.DOTALL)
		entries = []
		for m in ms:
			if not self.running:
				break
			(descrelurl, name, unparseddate, torrenturl, size, unit, seeders, leechers) = m
			entries.append( {
				'descurl':'http://thepiratebay.org'+descrelurl,
				'name': name.strip(),
				'torrenturl': torrenturl,
				'age': (datetime.date.today()-self.parse_date(unparseddate)).days,
				'seeders': seeders,
				'leechers': leechers,
				'size': self.parse_size(size, unit),
			})
		return entries
	
	def parse_date(self, unparseddate):
		d = unparseddate.replace('&nbsp;', ' ')
		if d.startswith("Today"):
			return datetime.date.today()
		if d.startswith("Y-day"):
			return datetime.date.today() - datetime.timedelta(1)
		m = re.match('([0-9]{2})-([0-9]{2}) ([0-9]{4})', d)
		
		if m is not None:
			(month, day, year) = m.groups()
			try:
				d = datetime.date(int(year), int(month), int(day))
				return d
			except ValueError, e:
				print e
		
		m = re.match('([0-9]{2})-([0-9]{2}) ', d)
		year = time.strftime('%Y')
		if m is not None:
			(month, day) = m.groups()
			try:
				d = datetime.date(int(year), int(month), int(day))
				return d
			except ValueError, e:
				print e
		
		print 'Unknown date format:', d
		return datetime.date(1970,1,1)
	
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
		
	def _cacher(self, n):
		self._checktmp()
		cachefilename = os.path.join(self.tmpdir, "tpb-%s-%s.page" % (self.category, n))
		
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

if __name__ == "__main__":
	def mockcb(v):
		print 'mockcb',v
	pb = PirateBay(mockcb, 202)
	pb.start()


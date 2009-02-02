from torrentsite import TorrentSite
import urllib
import re
import datetime
import time

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

ENTRIES_PER_PAGE = 30

class Legaltorrents(TorrentSite):
	urlschema = 'http://thepiratebay.org/browse/%(category)s/%(n)s/7'
	queries = 0
	
	def __init__(self, cb, category, tmpdir = '/tmp/tpb/'):
		TorrentSite.__init__(self, cb, category, tmpdir = '/tmp/tpb/')
	
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
	
if __name__ == "__main__":
	def mockcb(v):
		print 'mockcb',v
	pb = Thepiratebay(mockcb, 202)
	pb.push_entries_limit()
	pb.start()
	time.sleep(5)
	pb.stop()


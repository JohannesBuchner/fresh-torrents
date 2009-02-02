from torrentsite import TorrentSite
import urllib
import re
import datetime
import time

spacer = '[^<>]*'
span = '[^<>]*(?:<span[^<>]*>[^<>]*</span>)?[^<>]*'
start = '<tr[^<>]*>'
intro = '<td[^<>]*><a[^<>]*><img[^<>]*></a></td>'
name = '<td[^<>]*><a.href="([^"]*)"[^<>]*>([^<>]*)</a>' + span + '</td>'
torrenturl = '<td[^<>]*><a.href="([^"]*)"[^<>]*><img[^<>]*></a>' + span + '</td>'
date = '<td[^<>]*>([^<>]*)</td>'
seeders = '<td[^<>]*>([0-9]*)</td>'
leechers = '<td[^<>]*>([0-9]*)</td>'
rest = '<td[^<>]*>[^<>]*</td>' + spacer + '<td[^<>]*>[^<>]*</td>' + spacer + '<td[^<>]*>[^<>]*</td>' 
end = '</tr[^<>]*>'

exp = start + spacer + intro + spacer + name + spacer + torrenturl + spacer + date + spacer + seeders + spacer + leechers + spacer + rest + spacer + end


class Legittorrents(TorrentSite):
	urlschema = 'http://www.legittorrents.info/index.php?page=torrents&active=1&category=%(category)s&order=seeds&by=DESC&pages=%(n)s'
	queries = 0
	backendname = "LegitTorrents"
	page = 1

	def get_backend_name(self):
		return self.backendname

	def _fetch_current_entries(self):
		page = self._cacher(self.page)
		ms = re.findall(exp, page, re.MULTILINE | re.DOTALL)
		entries = []
		for m in ms:
			if not self.running:
				break
			(reldescurl, name, reltorrenturl, unparseddate, seeders, leechers) = m
			entries.append( {
				'descurl':'http://www.legittorrents.info/'+reldescurl.replace("&amp;","&"),
				'name': self.cleanup_string(name),
				'torrenturl': 'http://www.legittorrents.info/'+reltorrenturl.replace("&amp;","&"),
				'age': (datetime.date.today()-self.parse_date(unparseddate)).days,
				'seeders': seeders,
				'leechers': leechers,
				'size': 0, # not supported
			})
		return entries
	
	def push_entries_limit(self, n = 15*5):
		TorrentSite.push_entries_limit(self, n)

	def parse_date(self, d):
		m = re.match('([0-9]{2})/([0-9]{2})/([0-9]{4})', d)
		
		if m is not None:
			(day, month, year) = m.groups()
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
	pb = Legittorrents(mockcb, 1)
	pb.push_entries_limit()
	pb.start()
	time.sleep(5)
	pb.push_entries_limit()
	time.sleep(5)
	pb.stop()


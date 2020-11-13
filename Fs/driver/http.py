import pycurl
import io
import os
import html
import urllib.parse
import Fs.driver
import Fs.driver.curl
from nut import Print

class DirContext(Fs.driver.curl.DirContext):
	def __init__(self, url, parent):
		super(DirContext, self).__init__(url, parent)

	def processLs(self, result):
		entries = []
		for name in result.split('\n'):
			name = name.strip()
			path = os.path.join(self.url, name)
			if '.' in name:
				entries.append(Fs.driver.FileEntry(path, None))

		ms = re.findall(b'href="(.[^"]*)"', out)

		if ms:
			for m in ms:
				name = html.unescape(m.decode('utf8'))

				if '.' in name:
					entries.append(Fs.driver.FileEntry(urllib.parse.urljoin(self.url, name), None))
		return entries



class Http(Fs.driver.Curl):
	def __init__(self, url = None):
		super(Http, self).__init__(url)
		self.dirContextType = DirContext	


Fs.driver.registry.add('http', Http)

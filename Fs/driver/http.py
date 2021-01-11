import os
import re
import html
import urllib.parse
import Fs.driver
import Fs.driver.curl

class DirContext(Fs.driver.curl.DirContext):
	"""DirContext class
	"""

	def processLs(self, result):
		entries = []
		for name in result.split('\n'):
			name = name.strip()
			path = os.path.join(self.url, name)
			if '.' in name:
				entries.append(Fs.driver.FileEntry(path, None))

		ms = re.findall('href="(.[^"]*)"', result)

		if ms:
			for m in ms:
				name = html.unescape(m.decode('utf8'))

				if '.' in name:
					entries.append(Fs.driver.FileEntry(urllib.parse.urljoin(self.url, name), None))
		return entries


class Http(Fs.driver.curl.Curl):
	"""Http class
	"""
	def __init__(self, url=None):
		super().__init__(url)
		self.dirContextType = DirContext


Fs.driver.registry.add('http', Http)

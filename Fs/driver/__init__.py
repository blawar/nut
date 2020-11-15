import sys
import Fs.driver.registry
import urllib.parse
import os.path
from nut import Config

class DirContext:
	def __init__(self, url, parent):
		self.url = url
		self.parent = parent

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def isFile(self):
		return False

	def ls(self):
		return []

	def close(self):
		pass

class FileContext:
	def __init__(self, url, sz, mode, parent):
		self.url = url
		self.sz = sz
		self.mode = mode
		self.parent = parent

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def read(self, sz=None):
		return 0

	def chunk(self, callback, offset=None, size=None):
		return 0

	def open(self, mode='rb'):
		return False

	def close(self):
		return False

class Entry:
	def __init__(self, url):
		self.url = url
		self.size = None

	def baseName(self):
		return os.path.basename(self.url)

	def mtime(self):
		return None

class DirEntry(Entry):
	def __init__(self, url):
		super(DirEntry, self).__init__(url)

	def isFile(self):
		return False

	def baseName(self):
		return os.path.basename(self.url)

	def mtime(self):
		return None

class FileEntry(Entry):
	def __init__(self, url, sz):
		super(FileEntry, self).__init__(url)
		self.size = sz

	def isFile(self):
		return True

	def baseName(self):
		return os.path.basename(self.url)

	def mtime(self):
		return None

class Interface:
	def __init__(self, url=None):
		self.url = url
		self.dirContextType = DirContext
		self.fileContextType = FileContext

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def close(self):
		pass

	def openDir(self, url):
		return self.dirContextType(url, self)

	def openFile(self, url, mode='rb'):
		return self.fileContextType(url, None, mode, self)

def getScheme(url):
	if ':' not in url:
		return ''

	return url.split(':')[0].lower()


def openDir(url):
	return Fs.driver.registry.get(getScheme(url)).openDir(url)

def openFile(url, mode='rb'):
	return Fs.driver.registry.get(getScheme(url)).openFile(url, mode)


customSchemes = ['gdrive:']
def join(url1, url2):
	if not url1:
		return url2

	if not url2:
		return url1

	for s in customSchemes:
		if url1.startswith(s):
			dummyScheme = 'http://localhost'
			tempUrl = dummyScheme + url1[len(s):]
			if not tempUrl.endswith('/'):
				tempUrl = tempUrl + '/'
			tempUrl = urllib.parse.urljoin(tempUrl, url2)
			return s + tempUrl[len(dummyScheme):]

	if Fs.driver.registry.isNative(url1):
		return os.path.join(url1, url2).replace('/', '\\')
	return urllib.parse.urljoin(url1, url2)

def isWindows():
	if "win" in sys.platform[:3].lower():
		return True
	else:
		return False

def cleanPath(path=None):
	if not path:
		return None

	if not Fs.driver.registry.isNative(path):
		return path.replace('\\', '/')

	bits = path.replace('\\', '/').split('/')
	drive = bits[0]
	bits = bits[1:]

	if drive in Config.paths.mapping():
		url = Config.paths.mapping()[drive]

		path = os.path.abspath(
			os.path.join(
				os.path.abspath(url),
				'/'.join(bits)
			)
		)
	elif isWindows():
		path = os.path.abspath(os.path.join(drive+'/', '/'.join(bits)))
	else:
		path = os.path.abspath('/'.join(bits))

	return path

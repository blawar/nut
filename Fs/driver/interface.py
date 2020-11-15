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

class DirEntry:
	def __init__(self, url):
		self.url = url

	def isFile(self):
		return False

class FileEntry:
	def __init__(self, url, sz):
		self.url = url
		self.sz = sz

	def isFile(self):
		return True

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

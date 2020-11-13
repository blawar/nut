import os
import Fs.driver
from nut import Print

class FileContext(Fs.driver.FileContext):
	def __init__(self, url, sz, mode, parent):
		super(FileContext, self).__init__(url, sz, mode, parent)
		self.handle = open(self.url, self.mode)

	def close(self):
		if self.handle:
			self.handle.close()
			self.handle = None

	def read(self, sz = None):
		return self.handle.read(sz)

	def chunk(self, callback):
		chunkSize = 0x100000

		r = self.handle

		try:
			while True:
				chunk = r.read(chunkSize)

				if not chunk:
					break

				callback(chunk)
		except BaseException as e:
			Print.info('native chunk exception: ' + str(e))

class DirContext(Fs.driver.DirContext):
	def __init__(self, url, parent):
		super(DirContext, self).__init__(url, parent)

	def ls(self):
		entries = []
		for f in os.listdir(self.url):
			path = os.path.join(self.url,f)
			if os.path.isfile(path):
				entries.append(Fs.driver.FileEntry(path, None))
		return entries



class Native(Fs.driver.Interface):
	def __init__(self, url = None):
		super(Native, self).__init__(url)
		self.dirContextType = DirContext
		self.fileContextType = FileContext

	


Fs.driver.registry.add('', Native)

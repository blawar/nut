import pycurl
import io
import os
import Fs.driver
from nut import Print

class FileContext(Fs.driver.FileContext):
	def __init__(self, url, sz, mode, parent):
		super(FileContext, self).__init__(url, sz, mode, parent)

	def close(self):
		pass

	def setup(self, curl, offset, size):
		if offset or sz:

			if sz:

				offset = int(offset or 0)
				sz = int(sz)

				tmp = '%d-%d' % (offset, offset + size - 1)
			else:
				offset = int(offset or 0)
				tmp = '%d-' % (offset)

			curl.setopt(pycurl.RANGE, tmp)

	def read(self, sz=None):
		curl = pycurl.Curl()
		curl.setopt(pycurl.URL, self.url)
		output = io.BytesIO()
		curl.setopt(pycurl.WRITEFUNCTION, output.write)
		self.setup(curl, None, sz)
		curl.perform()

		return output.getvalue()

	def chunk(self, callback, offset=None, size=None):
		try:
			curl = pycurl.Curl()
			curl.setopt(pycurl.URL, self.url)
			output = io.BytesIO()
			curl.setopt(pycurl.WRITEFUNCTION, callback)
			self.setup(curl, offset, size)
			curl.perform()
		except BaseException as e:
			Print.info('curl chunk exception: ' + str(e))

class DirContext(Fs.driver.DirContext):
	def __init__(self, url, parent):
		super(DirContext, self).__init__(url, parent)

	def processLs(self, result):
		entries = []
		for name in result.split('\n'):
			name = name.strip()
			path = os.path.join(self.url, name)
			if '.' in name:
				entries.append(Fs.driver.FileEntry(path, None))
		return entries

	def ls(self):
		curl = pycurl.Curl()
		curl.setopt(pycurl.URL, self.url)
		output = io.BytesIO()
		curl.setopt(pycurl.DIRLISTONLY, 1)
		curl.setopt(pycurl.WRITEFUNCTION, output.write)
		curl.perform()

		return self.processLs(output.getvalue().decode('utf8'))


class Curl(Fs.driver.Interface):
	def __init__(self, url=None):
		super(Curl, self).__init__(url)
		self.dirContextType = DirContext
		self.fileContextType = FileContext


Fs.driver.registry.add('ftp', Curl)

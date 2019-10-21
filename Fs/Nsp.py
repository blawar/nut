from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from Fs.File import File
from hashlib import sha256
import Fs.Type
import os
import os.path
import re
import pathlib
from nut import Config
from nut import Print
from nut import Nsps
from tqdm import tqdm
import shutil

MEDIA_SIZE = 0x200

class Nsp:
	def __init__(self, path = None, mode = 'rb'):
		self.path = None
		self.titleId = None
		self.hasValidTicket = None
		self.timestamp = None
		self.version = None
		self.fileSize = None
		self.fileModified = None
		
		if path:
			self.setPath(path)			

	def getFileSize(self):
		if self.fileSize == None:
			self.fileSize = os.path.getsize(self.path)
		return self.fileSize

	def getFileModified(self):
		if self.fileModified == None:
			self.fileModified = os.path.getmtime(self.path)
		return self.fileModified

	def loadCsv(self, line, map = ['id', 'path', 'version', 'timestamp', 'fileSize']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				Print.info('invalid map index: ' + str(i) + ', ' + str(len(map)))
				continue
			
			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())

	def serialize(self, map = ['id', 'path', 'version', 'timestamp', 'fileSize']):
		r = []
		for i in map:
				
			methodName = 'get' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda: methodName)
			r.append(str(method()))
		return '|'.join(r)

	def __lt__(self, other):
		return str(self.path) < str(other.path)
				
	def __iter__(self):
		return self.files.__iter__()

		
	def setId(self, id):
		if re.match('[A-F0-9]{16}', id, re.I):
			self.titleId = id

	def getId(self):
			return self.titleId or ('0' * 16)

	def setTimestamp(self, timestamp):
		try:
			self.timestamp = int(str(timestamp), 10)
		except:
			pass

	def getTimestamp(self):
		return str(self.timestamp or '')

	def setVersion(self, version):
		if version and len(version) > 0:
			self.version = version

	def getVersion(self):
		return self.version or ''
		
	def isUpdate(self):
		return self.titleId is not None and self.titleId.endswith('800')
		
	def isDLC(self):
		return self.titleId is not None and not self.isUpdate() and not self.titleId.endswith('000')
			
	def setPath(self, path):			
		self.path = path
		self.version = '0'
		
		z = re.search('.*\[([a-fA-F0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0].upper()
		else:
			Print.info('could not get title id from filename, name needs to contain [titleId] : ' + path)
			self.titleId = None

		z = re.match('.*\[v([0-9]+)\].*', path, re.I)
		if z:
			self.version = z.groups()[0]

		ext = pathlib.Path(path).suffix

	def getPath(self):
		return self.path or ''
			
	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Nsp, self).open(path or self.path, mode, cryptoType, cryptoKey, cryptoCounter)

	def dict(self):
		return {"titleId": self.titleId, "hasValidTicket": self.hasValidTicket, 'version': self.version, 'fileSize': self.fileSize, 'path': self.path }
		
	def fileName(self):
		return os.path.basename(self.path)
		

		
			
	

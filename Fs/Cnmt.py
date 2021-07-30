from Fs.File import File
import Fs.Type
from binascii import hexlify as hx, unhexlify as uhx
from nut import Print
from nut import Keys
from nut import blockchain

class MetaEntry:
	def __init__(self, f):
		self.titleId = hx(f.read(8)[::-1]).decode()
		self.version = f.readInt32()
		self.type = f.readInt8()
		self.install = f.readInt8()

		f.readInt16()  # junk

class ContentEntry:
	def __init__(self, f):
		self.offset = f.tell()
		self.hash = f.read(32)
		self.ncaId = hx(f.read(16)).decode()
		self.size = f.readInt48()
		self.type = f.readInt8()
		self.f = f

		f.readInt8()  # junk

	def setHash(self, hash):
		self.f.seek(self.offset)
		self.f.write(hash)

	def setContentId(self, ncaId):
		self.f.seek(self.offset + 32)
		self.f.write(uhx(ncaId), 16)


class Cnmt(File):
	def __init__(self, path=None, mode=None, cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(Cnmt, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

		self.titleId = None
		self.version = None
		self.titleType = None
		self.headerOffset = None
		self.contentEntryCount = None
		self.metaEntryCount = None
		self.contentEntries = []
		self.metaEntries = []

	def open(self, file=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(Cnmt, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()

		self.titleId = hx(self.read(8)[::-1]).decode()
		self.version = self.readInt32()
		self.titleType = self.readInt8()

		self.readInt8()  # junk

		self.headerOffset = self.readInt16()
		self.contentEntryCount = self.readInt16()
		self.metaEntryCount = self.readInt16()

		self.contentEntries = []
		self.metaEntries = []

		self.seek(0x18)
		self.requiredDownloadSystemVersion = self.readInt32()

		self.seek(0x20)
		self.requiredSystemVersion = None
		self.requiredApplicationVersion = None
		self.applicationId = None

		if cnmt.titleType == 0x80: #base
			self.applicationId = self.readInt64()
			self.requiredSystemVersion = self.readInt32()
			self.requiredApplicationVersion = self.readInt32()

		if cnmt.titleType == 0x81: #patch
			self.applicationId = self.readInt64()
			self.requiredSystemVersion = self.readInt32()

		if cnmt.titleType == 0x82: #DLC
			self.applicationId = self.readInt64()
			self.requiredApplicationVersion = self.readInt32()

		self.seek(0x20 + self.headerOffset)
		for i in range(self.contentEntryCount):
			self.contentEntries.append(ContentEntry(self))

		for i in range(self.metaEntryCount):
			self.metaEntries.append(MetaEntry(self))

	def setHash(self, contentId, hash):
		contentId = contentId.lower()

		if '.' in contentId:
			contentId = contentId.split('.')[0]

		for entry in self.contentEntries:
			if entry.ncaId == contentId:
				entry.setHash(uhx(hash))


	def renameNca(self, oldName, newName, hash = None):
		oldName = oldName.lower()
		newName = newName.lower()

		if '.' in oldName:
			oldName = oldName.split('.')[0]

		if '.' in newName:
			newName = newName.split('.')[0]

		if oldName == newName:
			return False

		for entry in self.contentEntries:
			if entry.ncaId == oldName:
				if hash:
					entry.setHash(uhx(hash))
				entry.setContentId(newName)
				return True

		return False

	def printInfo(self, maxDepth=3, indent=0):
		tabs = '\t' * indent
		Print.info('\n%sCnmt\n' % (tabs))
		Print.info('%stitleId = %s' % (tabs, self.titleId))
		Print.info('%sversion = %x' % (tabs, self.version))
		Print.info('%stitleType = %x' % (tabs, self.titleType))

		for i in self.contentEntries:
			Print.info('%s\tncaId: %s  type = %x, hash = %s' % (tabs, i.ncaId, i.type, hx(i.hash).decode('utf8' )))
		super(Cnmt, self).printInfo(maxDepth, indent)

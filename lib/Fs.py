import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from File import File
from File import BufferedFile
import Type
import os
import re
import pathlib
import Keys
import Config
import Print
import Nsps
from tqdm import tqdm

MEDIA_SIZE = 0x200


def factory(name):
	if name.endswith('.xci'):
		f = Xci()
	elif name.endswith('.nsp'):
		f = Nsp()
	elif name.endswith('.nsx'):
		f = Nsp()
	elif name.endswith('.nca'):
		f =  Nca()
	elif name.endswith('.tik'):
		f =  Ticket()
	else:
		f = File()

	return f

class SectionTableEntry:
	def __init__(self, d):
		self.mediaOffset = int.from_bytes(d[0x0:0x4], byteorder='little', signed=False)
		self.mediaEndOffset = int.from_bytes(d[0x4:0x8], byteorder='little', signed=False)
		
		self.offset = self.mediaOffset * MEDIA_SIZE
		self.endOffset = self.mediaEndOffset * MEDIA_SIZE
		
		self.unknown1 = int.from_bytes(d[0x8:0xc], byteorder='little', signed=False)
		self.unknown2 = int.from_bytes(d[0xc:0x10], byteorder='little', signed=False)
		self.sha1 = None
		
class SectionFilesystem(File):
	def __init__(self, buffer, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):		
		self.buffer = buffer
		self.sectionStart = 0
		self.fsType = None
		self.cryptoType = None
		self.size = 0
		self.cryptoCounter = None
		self.magic = None
		
		#if buffer:
		#	Hex.dump(buffer)
			
		self.files = []
		
		if buffer:
			self.buffer = buffer
			try:
				self.fsType = Type.Fs(buffer[0x3])
			except:
				self.fsType = buffer[0x3]

			try:
				self.cryptoType = Type.Crypto(buffer[0x4])
			except:
				self.cryptoType = buffer[0x4]
			
			self.cryptoCounter = bytearray((b"\x00"*8) + buffer[0x140:0x148])
			self.cryptoCounter = self.cryptoCounter[::-1]
			
			cryptoType = self.cryptoType
			cryptoCounter = self.cryptoCounter
		#else:
		#	Print.info('no sfs buffer')
			
		super(SectionFilesystem, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)
		
	def __getitem__(self, key):
		if isinstance(key, str):
			for f in self.files:
				if f.name == key:
					return f
		elif isinstance(key, int):
			return self.files[key]
				
		raise IOError('FS File Not Found')
		
	def printInfo(self, indent):
		tabs = '\t' * indent
		Print.info(tabs + 'magic = ' + str(self.magic))
		Print.info(tabs + 'fsType = ' + str(self.fsType))
		Print.info(tabs + 'cryptoType = ' + str(self.cryptoType))
		Print.info(tabs + 'size = ' + str(self.size))
		Print.info(tabs + 'offset = ' + str(self.offset))
		if self.cryptoCounter:
			Print.info(tabs + 'cryptoCounter = ' + str(hx(self.cryptoCounter)))
			
		if self.cryptoKey:
			Print.info(tabs + 'cryptoKey = ' + str(hx(self.cryptoKey)))
		
		Print.info('\n%s\t%s\n' % (tabs, '*' * 64))
		Print.info('\n%s\tFiles:\n' % (tabs))
		
		for f in self:
			f.printInfo(indent+1)
			Print.info('\n%s\t%s\n' % (tabs, '*' * 64))


class PFS0File(File):
	def __init__(self):
		super(PFS0File, self).__init__()
		self.name = None
		self.offset = None
		self.size = None
		self.path = None
	
	def printInfo(self, indent):
		tabs = '\t' * indent
		Print.info(tabs + 'name = ' + str(self.name))
		super(PFS0File, self).printInfo(indent)
		
class PFS0(SectionFilesystem):
	def __init__(self, buffer, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(PFS0, self).__init__(buffer, path, mode, cryptoType, cryptoKey, cryptoCounter)
		
		if buffer:
			self.size = int.from_bytes(buffer[0x48:0x50], byteorder='little', signed=False)
			self.sectionStart = int.from_bytes(buffer[0x40:0x48], byteorder='little', signed=False)
		
	def getHeader():
		stringTable = '\x00'.join(file.name for file in self.files)
		
		headerSize = 0x10 + len(self.files) * 0x18 + len(stringTable)
		remainder = 0x10 - headerSize % 0x10
		headerSize += remainder
	
		h = b''
		h += b'PFS0'
		h += len(self.files).to_bytes(4, byteorder='little')
		h += (len(stringTable)+remainder).to_bytes(4, byteorder='little')
		h += b'\x00\x00\x00\x00'
		
		stringOffset = 0
		
		for f in range(len(self.files)):
			header += f.offset.to_bytes(8, byteorder='little')
			header += f.size.to_bytes(8, byteorder='little')
			header += stringOffset.to_bytes(4, byteorder='little')
			header += b'\x00\x00\x00\x00'
			
			stringOffset += len(f.name) + 1
			
		h += stringTable.encode()
		h += remainder * b'\x00'
		
		return h
		
	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		r = super(PFS0, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		#self.setupCrypto()
		#Print.info('cryptoType = ' + hex(self.cryptoType))
		#Print.info('titleKey = ' + (self.cryptoKey.hex()))
		#Print.info('cryptoCounter = ' + (self.cryptoCounter.hex()))

		self.magic = self.read(4)
		if self.magic != b'PFS0':
			raise IOError('Not a valid PFS0 partition ' + str(self.magic))
			

		fileCount = self.readInt32()
		stringTableSize = self.readInt32()
		self.readInt32() # junk data

		self.seek(0x10 + fileCount * 0x18)
		stringTable = self.read(stringTableSize)
		stringEndOffset = stringTableSize
		
		headerSize = 0x10 + 0x18 * fileCount + stringTableSize
		self.files = []

		for i in range(fileCount):
			i = fileCount - i - 1
			self.seek(0x10 + i * 0x18)

			offset = self.readInt64()
			size = self.readInt64()
			nameOffset = self.readInt32() # just the offset
			name = stringTable[nameOffset:stringEndOffset].decode('utf-8').rstrip(' \t\r\n\0')
			stringEndOffset = nameOffset

			self.readInt32() # junk data

			f = factory(name)

			f._path = name
			f.offset = offset
			f.size = size
			
			self.files.append(self.partition(offset + headerSize, f.size, f))

		self.files.reverse()

		'''
		self.seek(0x10 + fileCount * 0x18)
		stringTable = self.read(stringTableSize)
		
		for i in range(fileCount):
			if i == fileCount - 1:
				self.files[i].name = stringTable[self.files[i].nameOffset:].decode('utf-8').rstrip(' \t\r\n\0')
			else:
				self.files[i].name = stringTable[self.files[i].nameOffset:self.files[i+1].nameOffset].decode('utf-8').rstrip(' \t\r\n\0')
		'''
				
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sPFS0\n' % (tabs))
		super(PFS0, self).printInfo(indent)

class HFS0(PFS0):
	def __init__(self, buffer, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(HFS0, self).__init__(buffer, path, mode, cryptoType, cryptoKey, cryptoCounter)

	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		r = super(SectionFilesystem, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()

		self.magic = self.read(0x4);
		if self.magic != b'HFS0':
			raise IOError('Not a valid HFS0 partition ' + str(self.magic))
			

		fileCount = self.readInt32()
		stringTableSize = self.readInt32()
		self.readInt32() # junk data

		self.seek(0x10 + fileCount * 0x40)
		stringTable = self.read(stringTableSize)
		stringEndOffset = stringTableSize
		
		headerSize = 0x10 + 0x40 * fileCount + stringTableSize
		self.files = []

		for i in range(fileCount):
			i = fileCount - i - 1
			self.seek(0x10 + i * 0x40)

			offset = self.readInt64()
			size = self.readInt64()
			nameOffset = self.readInt32() # just the offset
			name = stringTable[nameOffset:stringEndOffset].decode('utf-8').rstrip(' \t\r\n\0')
			stringEndOffset = nameOffset

			self.readInt32() # junk data

			if name in ['update', 'secure', 'normal']:
				f = HFS0(None)
				#f = factory(name)
			else:
				f = factory(name)

			f._path = name
			f.offset = offset
			f.size = size
			self.files.append(self.partition(offset + headerSize, f.size, f))

		self.files.reverse()

	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sHFS0\n' % (tabs))
		super(PFS0, self).printInfo(indent)

		
class ROMFS(SectionFilesystem):
	def __init__(self, buffer, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(ROMFS, self).__init__(buffer, path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.magic = buffer[0x8:0xC]

	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		r = super(ROMFS, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		
def GetSectionFilesystem(buffer, cryptoKey):
	fsType = buffer[0x3]
	if fsType == Type.Fs.PFS0:
		return PFS0(buffer, cryptoKey = cryptoKey)
		
	if fsType == Type.Fs.ROMFS:
		return ROMFS(buffer, cryptoKey = cryptoKey)
		
	return SectionFilesystem(buffer, cryptoKey = cryptoKey)
	
class NcaHeader(File):
	def __init__(self, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		self.signature1 = None
		self.signature2 = None
		self.magic = None
		self.isGameCard = None
		self.contentType = None
		self.cryptoType = None
		self.keyIndex = None
		self.size = None
		self.titleId = None
		self.sdkVersion = None
		self.cryptoType2 = None
		self.rightsId = None
		self.titleKeyDec = None
		self.masterKey = None
		self.sectionTables = []
		self.keys = []
		
		super(NcaHeader, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)
		
	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(NcaHeader, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signature1 = self.read(0x100)
		self.signature2 = self.read(0x100)
		self.magic = self.read(0x4)
		self.isGameCard = self.readInt8()
		self.contentType = self.readInt8()

		try:
			self.contentType = Type.Content(self.contentType)
		except:
			pass

		self.cryptoType = self.readInt8()
		self.keyIndex = self.readInt8()
		self.size = self.readInt64()
		self.titleId = hx(self.read(8)[::-1]).decode('utf-8').upper()
		
		self.readInt32() # padding
		

		self.sdkVersion = self.readInt32()
		self.cryptoType2 = self.readInt8()
		
		self.read(0xF) # padding
		
		self.rightsId = hx(self.read(0x10))
		
		if self.magic not in [b'NCA3', b'NCA2']:
			raise Exception('Failed to decrypt NCA header: ' + str(self.magic))
		
		self.sectionHashes = []
		
		for i in range(4):
			self.sectionTables.append(SectionTableEntry(self.read(0x10)))
			
		for i in range(4):
			self.sectionHashes.append(self.sectionTables[i])

		self.masterKey = (self.cryptoType if self.cryptoType > self.cryptoType2 else self.cryptoType2)-1

		if self.masterKey < 0:
			self.masterKey = 0
		
		
		self.encKeyBlock = self.getKeyBlock()
		#for i in range(4):
		#	offset = i * 0x10
		#	key = encKeyBlock[offset:offset+0x10]
		#	Print.info('enc %d: %s' % (i, hx(key)))

		if Keys.keyAreaKey(self.masterKey, self.keyIndex):
			crypto = aes128.AESECB(Keys.keyAreaKey(self.masterKey, self.keyIndex))
			self.keyBlock = crypto.decrypt(self.encKeyBlock)
			self.keys = []
			for i in range(4):
				offset = i * 0x10
				key = self.keyBlock[offset:offset+0x10]
				#Print.info('dec %d: %s' % (i, hx(key)))
				self.keys.append(key)
		else:
			self.keys = [None, None, None, None, None, None, None]
		

		if self.hasTitleRights():
			if self.titleId.upper() in Titles.keys() and Titles.get(self.titleId.upper()).key:
				self.titleKeyDec = Keys.decryptTitleKey(uhx(Titles.get(self.titleId.upper()).key), self.masterKey)
			else:
				pass
				#Print.info('could not find title key!')
		else:
			self.titleKeyDec = self.key()

	def key(self):
		#return self.keys[2]
		return self.keys[self.cryptoType]

	def hasTitleRights(self):
		return self.rightsId != (b'0' * 32)

	def getKeyBlock(self):
		self.seek(0x300)
		return self.read(0x40)

	def setKeyBlock(self, value):
		if len(value) != 0x40:
			raise IOError('invalid keyblock size')

		self.seek(0x300)
		return self.write(value)

	def getCryptoType(self):
		self.seek(0x206)
		return self.readInt8()

	def setCryptoType(self, value):
		self.seek(0x206)
		self.writeInt8(value)

	def getCryptoType2(self):
		self.seek(0x220)
		return self.readInt8()

	def setCryptoType2(self, value):
		self.seek(0x220)
		self.writeInt8(value)

	def getRightsId(self):
		self.seek(0x230)
		return self.readInt128('big')

	def setRightsId(self, value):
		self.seek(0x230)
		self.writeInt128(value, 'big')


class Nca(File):
	def __init__(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		self.header = None
		self.sectionFilesystems = []
		super(Nca, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)
			
	def __iter__(self):
		return self.sectionFilesystems.__iter__()
		
	def __getitem__(self, key):
		return self.sectionFilesystems[key]

	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):

		super(Nca, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)

		self.header = NcaHeader()
		self.partition(0x0, 0xC00, self.header, Type.Crypto.XTS, uhx(Keys.get('header_key')))
		#Print.info('partition complete, seeking')
		self.header.seek(0x400)
		#Print.info('reading')
		#Hex.dump(self.header.read(0x200))
		#exit()

		for i in range(4):
			fs = GetSectionFilesystem(self.header.read(0x200), cryptoKey = self.header.titleKeyDec)
			#Print.info('fs type = ' + hex(fs.fsType))
			#Print.info('fs crypto = ' + hex(fs.cryptoType))
			#Print.info('st end offset = ' + str(self.header.sectionTables[i].endOffset - self.header.sectionTables[i].offset))
			#Print.info('fs offset = ' + hex(self.header.sectionTables[i].offset))
			#Print.info('fs section start = ' + hex(fs.sectionStart))
			#Print.info('titleKey = ' + hex(self.header.titleKeyDec))
			try:
				self.partition(self.header.sectionTables[i].offset + fs.sectionStart, self.header.sectionTables[i].endOffset - self.header.sectionTables[i].offset, fs, cryptoKey = self.header.titleKeyDec)
			except BaseException as e:
				pass
				#Print.info(e)
				#raise

			if fs.fsType:
				self.sectionFilesystems.append(fs)
		
		
		self.titleKeyDec = None
		self.masterKey = None

		
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sNCA Archive\n' % (tabs))
		super(Nca, self).printInfo(indent)
		
		Print.info(tabs + 'magic = ' + str(self.header.magic))
		Print.info(tabs + 'titleId = ' + str(self.header.titleId))
		Print.info(tabs + 'rightsId = ' + str(self.header.rightsId))
		Print.info(tabs + 'isGameCard = ' + hex(self.header.isGameCard))
		Print.info(tabs + 'contentType = ' + str(self.header.contentType))
		Print.info(tabs + 'cryptoType = ' + str(self.cryptoType))
		Print.info(tabs + 'Size: ' + str(self.header.size))
		Print.info(tabs + 'crypto master key: ' + str(self.header.cryptoType))
		Print.info(tabs + 'crypto master key: ' + str(self.header.cryptoType2))
		Print.info(tabs + 'key Index: ' + str(self.header.keyIndex))
		
		Print.info('\n%sPartitions:' % (tabs))
		
		for s in self:
			s.printInfo(indent+1)
			
class GamecardInfo(File):
	def __init__(self, file = None):
		super(GamecardInfo, self).__init__()
		if file:
			self.open(file)
	
	def open(self, file, mode='rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(GamecardInfo, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.firmwareVersion = self.readInt64()
		self.accessControlFlags = self.readInt32()
		self.readWaitTime = self.readInt32()
		self.readWaitTime2 = self.readInt32()
		self.writeWaitTime = self.readInt32()
		self.writeWaitTime2 = self.readInt32()
		self.firmwareMode = self.readInt32()
		self.cupVersion = self.readInt32()
		self.empty1 = self.readInt32()
		self.updatePartitionHash = self.readInt64()
		self.cupId = self.readInt64()
		self.empty2 = self.read(0x38)
		
class GamecardCertificate(File):
	def __init__(self, file = None):
		super(GamecardCertificate, self).__init__()
		self.signature = None
		self.magic = None
		self.unknown1 = None
		self.unknown2 = None
		self.data = None
		
		if file:
			self.open(file)
			
	def open(self, file, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(GamecardCertificate, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signature = self.read(0x100)
		self.magic = self.read(0x4)
		self.unknown1 = self.read(0x10)
		self.unknown2 = self.read(0xA)
		self.data = self.read(0xD6)

			
class Xci(File):
	def __init__(self, file = None):
		super(Xci, self).__init__()
		self.header = None
		self.signature = None
		self.magic = None
		self.secureOffset = None
		self.backupOffset = None
		self.titleKekIndex = None
		self.gamecardSize = None
		self.gamecardHeaderVersion = None
		self.gamecardFlags = None
		self.packageId = None
		self.validDataEndOffset = None
		self.gamecardInfo = None
		
		self.hfs0Offset = None
		self.hfs0HeaderSize = None
		self.hfs0HeaderHash = None
		self.hfs0InitialDataHash = None
		self.secureMode = None
		
		self.titleKeyFlag = None
		self.keyFlag = None
		self.normalAreaEndOffset = None
		
		self.gamecardInfo = None
		self.gamecardCert = None
		self.hfs0 = None
		
		if file:
			self.open(file)
		
	def readHeader(self):
	
		self.signature = self.read(0x100)
		self.magic = self.read(0x4)
		self.secureOffset = self.readInt32()
		self.backupOffset = self.readInt32()
		self.titleKekIndex = self.readInt8()
		self.gamecardSize = self.readInt8()
		self.gamecardHeaderVersion = self.readInt8()
		self.gamecardFlags = self.readInt8()
		self.packageId = self.readInt64()
		self.validDataEndOffset = self.readInt64()
		self.gamecardInfo = self.read(0x10)
		
		self.hfs0Offset = self.readInt64()
		self.hfs0HeaderSize = self.readInt64()
		self.hfs0HeaderHash = self.read(0x20)
		self.hfs0InitialDataHash = self.read(0x20)
		self.secureMode = self.readInt32()
		
		self.titleKeyFlag = self.readInt32()
		self.keyFlag = self.readInt32()
		self.normalAreaEndOffset = self.readInt32()
		
		self.gamecardInfo = GamecardInfo(self.partition(self.tell(), 0x70))
		self.gamecardCert = GamecardCertificate(self.partition(0x7000, 0x200))
		print('xci header size:' + str(self.hfs0HeaderSize))
		

	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		r = super(Xci, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.readHeader()
		self.seek(0xF000)
		self.hfs0 = HFS0(None, cryptoKey = None)
		self.partition(0xf000, None, self.hfs0, cryptoKey = None)
		
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sXCI Archive\n' % (tabs))
		super(Xci, self).printInfo(indent)
		
		Print.info(tabs + 'magic = ' + str(self.magic))
		Print.info(tabs + 'titleKekIndex = ' + str(self.titleKekIndex))
		
		Print.info(tabs + 'gamecardCert = ' + str(hx(self.gamecardCert.magic + self.gamecardCert.unknown1 + self.gamecardCert.unknown2 + self.gamecardCert.data)))

		self.hfs0.printInfo()
		

class Nsp(PFS0):
		
	def __init__(self, path = None, mode = 'rb'):
		self.path = None
		self.titleId = None
		self.hasValidTicket = None
		self.timestamp = None
		self.version = None

		super(Nsp, self).__init__(None, path, mode)
		
		if path:
			self.setPath(path)
			#if files:
			#	self.pack(files)
				
		if self.titleId and self.isUnlockable():
			Print.info('unlockable title found ' + self.path)
		#	self.unlock()

	def loadCsv(self, line, map = ['id', 'path', 'version', 'timestamp', 'hasValidTicket']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				Print.info('invalid map index: ' + str(i) + ', ' + str(len(map)))
				continue
			
			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())

	def serialize(self, map = ['id', 'path', 'version', 'timestamp', 'hasValidTicket']):
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
		
	def title(self):
		if not self.titleId:
			raise IOError('NSP no titleId set')
			
		if self.titleId in Titles.keys():
			return Titles.get(self.titleId)
			
		t = Title.Title()
		t.setId(self.titleId)
		Titles.data()[self.titleId] = t
		return t

	def getUpdateFile(self):
		title = self.title()

		if title.isUpdate or title.isDLC or not title.updateId:
			return None

		for i, nsp in Nsps.files.items():
			if nsp.titleId == title.updateId:
				return nsp

		return None

	def isUpdateAvailable(self):
		title = self.title()

		if self.titleId and title.version != None and self.version < title.version and str(title.version) != '0':
			return {'id': title.id, 'baseId': title.baseId, 'currentVersion': self.version, 'newVersion': title.version}

		if not title.isUpdate and not title.isDLC and Titles.contains(title.updateId):
			updateFile = self.getUpdateFile()

			if updateFile:
				return updateFile.isUpdateAvailable()

			updateTitle = Titles.get(title.updateId)

			if updateTitle.version and str(updateTitle.version) != '0':
				return {'id': updateTitle.id, 'baseId': title.baseId, 'currentVersion': None, 'newVersion': updateTitle.version}

		return None
		
	def readMeta(self):
		self.open()
		try:
			#a = self.application()
			#if a.header.titleId:
			#	self.titleId = a.header.titleId
			#	self.title().setRightsId(a.header.rightsId)

			t = self.ticket()
			rightsId = hx(t.getRightsId().to_bytes(0x10, byteorder='big')).decode('utf-8').upper()
			self.titleId = rightsId[0:16]
			self.title().setRightsId(rightsId)
			Print.debug('rightsId = ' + rightsId)
			Print.debug(self.titleId + ' key = ' +  str(t.getTitleKeyBlock()))
			self.setHasValidTicket(t.getTitleKeyBlock() != 0)
		except BaseException as e:
			Print.info('readMeta filed ' + self.path + ", " + str(e))
			raise
		self.close()

	def unpack(self, path):
		os.makedirs(path, exist_ok=True)

		for nspF in self:
			filePath = os.path.abspath(path + '/' + nspF._path)
			f = open(filePath, 'wb')
			nspF.rewind()
			i = 0

			pageSize = 0x10000

			while True:
				buf = nspF.read(pageSize)
				if len(buf) == 0:
					break
				i += len(buf)
				f.write(buf)
			f.close()
			Print.info(filePath)

	def setHasValidTicket(self, value):
		if self.title().isUpdate:
			self.hasValidTicket = True
			return

		try:
			self.hasValidTicket = (True if value and int(value) != 0 else False) or self.title().isUpdate
		except:
			pass

	def getHasValidTicket(self):
		if self.title().isUpdate:
			return 1
		return (1 if self.hasValidTicket and self.hasValidTicket == True else 0)

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
			
	def setPath(self, path):			
		self.path = path
		self.version = '0'
		
		z = re.match('.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0].upper()
		else:
			Print.info('could not get title id from filename, name needs to contain [titleId] : ' + path)
			self.titleId = None

		z = re.match('.*\[v([0-9]+)\].*', path, re.I)
		if z:
			self.version = z.groups()[0]

		ext = pathlib.Path(path).suffix
		if ext == '.nsp':
			if self.hasValidTicket == None:
				self.setHasValidTicket(True)
		elif ext == '.nsx':
			if self.hasValidTicket == None:
				self.setHasValidTicket(False)
		else:
			return

	def getPath(self):
		return self.path or ''
			
	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Nsp, self).open(path or self.path, mode, cryptoType, cryptoKey, cryptoCounter)
					
	def move(self):
		if not self.path:
			Print.error('no path set')
			return False
		
		if not self.fileName():
			Print.error('could not get filename for ' + self.path)
			return False

		if os.path.abspath(self.fileName()).lower() == os.path.abspath(self.path).lower():
			return False
		if os.path.isfile(self.fileName()) and os.path.abspath(self.path) == os.path.abspath(self.fileName()):
			Print.info('duplicate title: ')
			Print.info(os.path.abspath(self.path))
			Print.info(os.path.abspath(self.fileName()))
			return False

		try:
			Print.info(self.path + ' -> ' + self.fileName())
			os.makedirs(os.path.dirname(self.fileName()), exist_ok=True)
			newPath = self.fileName()
			os.rename(self.path, newPath)
			self.path = newPath
		except BaseException as e:
			Print.info('failed to rename file! %s -> %s  : %s' % (self.path, self.fileName(), e))
		
		return True
		
	def cleanFilename(self, s):
		s = re.sub('\s+\Demo\s*', ' ', s, re.I)
		s = re.sub('\s*\[DLC\]\s*', '', s, re.I)
		s = re.sub('[\/\\\:\*\?\"\<\>\|\.\s™©®()\~]+', ' ', s)
		return s.strip()

	def dict(self):
		return {"titleId": self.titleId, "hasValidTicket": self.hasValidTicket, 'version': self.version, 'timestamp': self.timestamp, 'path': self.path }
		
	def fileName(self):
		bt = None
		if not self.titleId in Titles.keys():
			if not Title.getBaseId(self.titleId) in Titles.keys():
				Print.info('could not find title key for ' + self.titleId + ' or ' + Title.getBaseId(self.titleId))
				return None
			bt = Titles.get(Title.getBaseId(self.titleId))
			t = Title()
			t.loadCsv(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
		else:
			t = Titles.get(self.titleId)
		
			if not t.baseId in Titles.keys():
				Print.info('could not find baseId for ' + self.path)
				return None
			bt = Titles.get(t.baseId)
		
		if t.isDLC:
			format = Config.paths.titleDLC
		elif t.isDemo:
			if t.idExt != 0:
				format = Config.paths.titleDemoUpdate
			else:
				format = Config.paths.titleDemo
		elif t.idExt != 0:
			format = Config.paths.titleUpdate
		else:
			format = Config.paths.titleBase
			
		format = format.replace('{id}', self.cleanFilename(t.id))
		format = format.replace('{region}', self.cleanFilename(t.region or ''))
		format = format.replace('{name}', self.cleanFilename(t.name or ''))
		format = format.replace('{version}', str(self.version or 0))
		format = format.replace('{baseId}', self.cleanFilename(bt.id))
		format = format.replace('{baseName}', self.cleanFilename(bt.name or ''))
		
		if self.hasValidTicket:
			format = os.path.splitext(format)[0] + '.nsp'
		else:
			format = os.path.splitext(format)[0] + '.nsx'
		
		return format
		
	def ticket(self):
		for f in (f for f in self if type(f) == Ticket):
			return f
		raise IOError('no ticket in NSP')
		
	def cnmt(self):
		for f in (f for f in self if f._path.endswith('.cnmt.nca')):
			return f
		raise IOError('no cnmt in NSP')

	def xml(self):
		for f in (f for f in self if f._path.endswith('.xml')):
			return f
		raise IOError('no XML in NSP')

	def hasDeltas(self):
		return b'DeltaFragment' in self.xml().read()
		
	def application(self):
		for f in (f for f in self if f._path.endswith('.nca') and not f._path.endswith('.cnmt.nca')):
			return f
		raise IOError('no application in NSP')
		
	def isUnlockable(self):
		return (not self.hasValidTicket) and self.titleId and Titles.contains(self.titleId) and Titles.get(self.titleId).key
		
	def unlock(self):
		#if not self.isOpen():
		#	self.open('r+b')

		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database!')

		self.ticket().setTitleKeyBlock(int(Titles.get(self.titleId).key, 16))
		Print.info('setting title key to ' + Titles.get(self.titleId).key)
		self.ticket().flush()
		self.close()
		self.hasValidTicket = True
		self.move()

	def setMasterKeyRev(self, newMasterKeyRev):
		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database! ' + self.titleId)

		ticket = self.ticket()
		masterKeyRev = ticket.getMasterKeyRevision()
		titleKey = ticket.getTitleKeyBlock()
		newTitleKey = Keys.changeTitleKeyMasterKey(titleKey.to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(masterKeyRev), Keys.getMasterKeyIndex(newMasterKeyRev))
		rightsId = ticket.getRightsId()

		if rightsId != 0:
			raise IOError('please remove titlerights first')

		if (newMasterKeyRev == None and rightsId == 0) or masterKeyRev == newMasterKeyRev:
			Print.info('Nothing to do')
			return

		Print.info('rightsId =\t' + hex(rightsId))
		Print.info('titleKey =\t' + str(hx(titleKey.to_bytes(16, byteorder='big'))))
		Print.info('newTitleKey =\t' + str(hx(newTitleKey)))
		Print.info('masterKeyRev =\t' + hex(masterKeyRev))



		for nca in self:
			if type(nca) == Nca:
				if nca.header.getCryptoType2() != masterKeyRev:
					pass
					raise IOError('Mismatched masterKeyRevs!')

		ticket.setMasterKeyRevision(newMasterKeyRev)
		ticket.setRightsId((ticket.getRightsId() & 0xFFFFFFFFFFFFFFFF0000000000000000) + newMasterKeyRev)
		ticket.setTitleKeyBlock(int.from_bytes(newTitleKey, 'big'))

		for nca in self:
			if type(nca) == Nca:
				if nca.header.getCryptoType2() != newMasterKeyRev:
					Print.info('writing masterKeyRev for %s, %d -> %s' % (str(nca._path),  nca.header.getCryptoType2(), str(newMasterKeyRev)))

					encKeyBlock = nca.header.getKeyBlock()

					if sum(encKeyBlock) != 0:
						key = Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex)
						Print.info('decrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
						crypto = aes128.AESECB(key)
						decKeyBlock = crypto.decrypt(encKeyBlock)

						key = Keys.keyAreaKey(Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex)
						Print.info('encrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex))
						crypto = aes128.AESECB(key)

						reEncKeyBlock = crypto.encrypt(decKeyBlock)
						nca.header.setKeyBlock(reEncKeyBlock)


					if newMasterKeyRev >= 3:
						nca.header.setCryptoType(2)
						nca.header.setCryptoType2(newMasterKeyRev)
					else:
						nca.header.setCryptoType(newMasterKeyRev)
						nca.header.setCryptoType2(0)


	def removeTitleRights(self):
		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database! ' + self.titleId)

		ticket = self.ticket()
		masterKeyRev = ticket.getMasterKeyRevision()
		titleKeyDec = Keys.decryptTitleKey(ticket.getTitleKeyBlock().to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(masterKeyRev))
		rightsId = ticket.getRightsId()

		Print.info('rightsId =\t' + hex(rightsId))
		Print.info('titleKeyDec =\t' + str(hx(titleKeyDec)))
		Print.info('masterKeyRev =\t' + hex(masterKeyRev))



		for nca in self:
			if type(nca) == Nca:
				if nca.header.getCryptoType2() != masterKeyRev:
					pass
					raise IOError('Mismatched masterKeyRevs!')


		ticket.setRightsId(0)

		for nca in self:
			if type(nca) == Nca:
				if nca.header.getRightsId() == 0:
					continue

				Print.info('writing masterKeyRev for %s, %d' % (str(nca._path),  masterKeyRev))
				crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))

				encKeyBlock = crypto.encrypt(titleKeyDec * 4)
				nca.header.setRightsId(0)
				nca.header.setKeyBlock(encKeyBlock)
				Hex.dump(encKeyBlock)
			
		
	def pack(self, files):
		if not self.path:
			return False
			
		Print.info('\tRepacking to NSP...')
		
		hd = self.generateHeader(files)
		
		totSize = len(hd) + sum(os.path.getsize(file) for file in files)
		if os.path.exists(self.path) and os.path.getsize(self.path) == totSize:
			Print.info('\t\tRepack %s is already complete!' % self.path)
			return
			
		t = tqdm(total=totSize, unit='B', unit_scale=True, desc=os.path.basename(self.path), leave=False)
		
		t.write('\t\tWriting header...')
		outf = open(self.path, 'wb')
		outf.write(hd)
		t.update(len(hd))
		
		done = 0
		for file in files:
			t.write('\t\tAppending %s...' % os.path.basename(file))
			with open(file, 'rb') as inf:
				while True:
					buf = inf.read(4096)
					if not buf:
						break
					outf.write(buf)
					t.update(len(buf))
		t.close()
		
		Print.info('\t\tRepacked to %s!' % outf.name)
		outf.close()

	def generateHeader(self, files):
		filesNb = len(files)
		stringTable = '\x00'.join(os.path.basename(file) for file in files)
		headerSize = 0x10 + (filesNb)*0x18 + len(stringTable)
		remainder = 0x10 - headerSize%0x10
		headerSize += remainder
		
		fileSizes = [os.path.getsize(file) for file in files]
		fileOffsets = [sum(fileSizes[:n]) for n in range(filesNb)]
		
		fileNamesLengths = [len(os.path.basename(file))+1 for file in files] # +1 for the \x00
		stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(filesNb)]
		
		header =  b''
		header += b'PFS0'
		header += pk('<I', filesNb)
		header += pk('<I', len(stringTable)+remainder)
		header += b'\x00\x00\x00\x00'
		for n in range(filesNb):
			header += pk('<Q', fileOffsets[n])
			header += pk('<Q', fileSizes[n])
			header += pk('<I', stringTableOffsets[n])
			header += b'\x00\x00\x00\x00'
		header += stringTable.encode()
		header += remainder * b'\x00'
		
		return header

class Ticket(File):
	def __init__(self, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Ticket, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

		self.signatureType = None
		self.signature = None
		self.signaturePadding = None

		self.issuer = None
		self.titleKeyBlock = None
		self.keyType = None
		self.masterKeyRevision = None
		self.ticketId = None
		self.deviceId = None
		self.rightsId = None
		self.accountId = None

		self.signatureSizes = {}
		self.signatureSizes[Type.TicketSignature.RSA_4096_SHA1] = 0x200
		self.signatureSizes[Type.TicketSignature.RSA_2048_SHA1] = 0x100
		self.signatureSizes[Type.TicketSignature.ECDSA_SHA1] = 0x3C
		self.signatureSizes[Type.TicketSignature.RSA_4096_SHA256] = 0x200
		self.signatureSizes[Type.TicketSignature.RSA_2048_SHA256] = 0x100
		self.signatureSizes[Type.TicketSignature.ECDSA_SHA256] = 0x3C

	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Ticket, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signatureType = self.readInt32()
		try:
			self.signatureType = Type.TicketSignature(self.signatureType)
		except:
			raise IOError('Invalid ticket format')

		self.signaturePadding = 0x40 - ((self.signatureSizes[self.signatureType] + 4) % 0x40)

		self.seek(0x4 + self.signatureSizes[self.signatureType] + self.signaturePadding)

		self.issuer = self.read(0x40)
		self.titleKeyBlock = self.read(0x100)
		self.readInt8() # unknown
		self.keyType = self.readInt8()
		self.read(0x4) # unknown
		self.masterKeyRevision = self.readInt8()
		self.read(0x9) # unknown
		self.ticketId = hx(self.read(0x8)).decode('utf-8')
		self.deviceId = hx(self.read(0x8)).decode('utf-8')
		self.rightsId = hx(self.read(0x10)).decode('utf-8')
		self.accountId = hx(self.read(0x4)).decode('utf-8')
		self.seek(0x286)
		self.masterKeyRevision = self.readInt8()

	def seekStart(self, offset):
		self.seek(0x4 + self.signatureSizes[self.signatureType] + self.signaturePadding + offset)

	def getSignatureType(self):
		self.seek(0x0)
		self.signatureType = self.readInt32()
		return self.signatureType

	def setSignatureType(self, value):
		self.seek(0x0)
		self.signatureType = value
		self.writeInt32(value)
		return self.signatureType


	def getSignature(self):
		self.seek(0x4)
		self.signature = self.read(self.signatureSizes[self.getSignatureType()])
		return self.signature

	def setSignature(self, value):
		self.seek(0x4)
		self.signature = value
		self.write(value, self.signatureSizes[self.getSignatureType()])
		return self.signature


	def getSignaturePadding(self):
		self.signaturePadding = 0x40 - ((self.signatureSizes[self.signatureType] + 4) % 0x40)
		return self.signaturePadding


	def getIssuer(self):
		self.seekStart(0x0)
		self.issuer = self.read(0x40)
		return self.issuer

	def setIssuer(self, value):
		self.seekStart(0x0)
		self.issuer = value
		self.write(value, 0x40)
		return self.issuer


	def getTitleKeyBlock(self):
		self.seekStart(0x40)
		#self.titleKeyBlock = self.readInt(0x100, 'big')
		self.titleKeyBlock = self.readInt(0x10, 'big')
		return self.titleKeyBlock

	def setTitleKeyBlock(self, value):
		self.seekStart(0x40)
		self.titleKeyBlock = value
		#self.writeInt(value, 0x100, 'big')
		self.writeInt(value, 0x10, 'big')
		return self.titleKeyBlock


	def getKeyType(self):
		self.seekStart(0x141)
		self.keyType = self.readInt8()
		return self.keyType

	def setKeyType(self, value):
		self.seekStart(0x141)
		self.keyType = value
		self.writeInt8(value)
		return self.keyType


	def getMasterKeyRevision(self):
		self.seekStart(0x146)
		self.masterKeyRevision = self.readInt8()
		return self.masterKeyRevision

	def setMasterKeyRevision(self, value):
		self.seekStart(0x146)
		self.masterKeyRevision = value
		self.writeInt8(value)
		return self.masterKeyRevision


	def getTicketId(self):
		self.seekStart(0x150)
		self.ticketId = self.readInt64('big')
		return self.ticketId

	def setTicketId(self, value):
		self.seekStart(0x150)
		self.ticketId = value
		self.writeInt64(value, 'big')
		return self.ticketId


	def getDeviceId(self):
		self.seekStart(0x158)
		self.deviceId = self.readInt64('big')
		return self.deviceId

	def setDeviceId(self, value):
		self.seekStart(0x158)
		self.deviceId = value
		self.writeInt64(value, 'big')
		return self.deviceId


	def getRightsId(self):
		self.seekStart(0x160)
		self.rightsId = self.readInt128('big')
		return self.rightsId

	def setRightsId(self, value):
		self.seekStart(0x160)
		self.rightsId = value
		self.writeInt128(value, 'big')
		return self.rightsId


	def getAccountId(self):
		self.seekStart(0x170)
		self.accountId = self.readInt32('big')
		return self.accountId

	def setAccountId(self, value):
		self.seekStart(0x170)
		self.accountId = value
		self.writeInt32(value, 'big')
		return self.accountId





	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sTicket\n' % (tabs))
		super(Ticket, self).printInfo(indent)
		Print.info(tabs + 'signatureType = ' + str(self.signatureType))
		Print.info(tabs + 'keyType = ' + str(self.keyType))
		Print.info(tabs + 'masterKeyRev = ' + str(self.masterKeyRevision))
		Print.info(tabs + 'ticketId = ' + str(self.ticketId))
		Print.info(tabs + 'deviceId = ' + str(self.deviceId))
		Print.info(tabs + 'rightsId = ' + hex(self.getRightsId()))
		Print.info(tabs + 'accountId = ' + str(self.accountId))
		Print.info(tabs + 'titleKey = ' + hex(self.getTitleKeyBlock()))
		#Print.info(tabs + 'magic = ' + str(self.magic))
		#Print.info(tabs + 'titleKekIndex = ' + str(self.titleKekIndex))

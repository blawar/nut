import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from File import File
import Type

import Keys

MEDIA_SIZE = 0x200

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
		
		#if buffer:
		#	Hex.dump(buffer)
			
		self.files = []
		
		if buffer:
			self.buffer = buffer
			self.fsType = buffer[0x3]
			self.cryptoType = buffer[0x4]
			
			self.cryptoCounter = bytearray((b"\x00"*8) + buffer[0x140:0x148])
			self.cryptoCounter = self.cryptoCounter[::-1]
			
			cryptoType = self.cryptoType
			cryptoCounter = self.cryptoCounter
		#else:
		#	print('no sfs buffer')
			
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
		print(tabs + 'magic = ' + str(self.magic))
		print(tabs + 'fsType = ' + str(self.fsType))
		print(tabs + 'cryptoType = ' + str(self.cryptoType))
		print(tabs + 'size = ' + str(self.size))
		print(tabs + 'offset = ' + str(self.offset))
		if self.cryptoCounter:
			print(tabs + 'cryptoCounter = ' + str(hx(self.cryptoCounter)))
			
		if self.cryptoKey:
			print(tabs + 'cryptoKey = ' + str(hx(self.cryptoKey)))
		
		print('\n%s\t%s\n' % (tabs, '*' * 64))
		print('\n%s\tFiles:\n' % (tabs))
		
		for f in self:
			f.printInfo(indent+1)
			print('\n%s\t%s\n' % (tabs, '*' * 64))


class PFS0File(File):
	def __init__(self):
		super(PFS0File, self).__init__()
		self.name = None
		self.offset = None
		self.size = None
		self.path = None
	
	def printInfo(self, indent):
		tabs = '\t' * indent
		print(tabs + 'name = ' + str(self.name))
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
		#print('cryptoType = ' + hex(self.cryptoType))
		#print('titleKey = ' + (self.cryptoKey.hex()))
		#print('cryptoCounter = ' + (self.cryptoCounter.hex()))

		self.magic = self.read(4)
		if self.magic != b'PFS0':
			raise IOError('Not a valid PFS0 partition ' + str(self.magic))
			

		fileCount = self.readInt32()
		stringTableSize = self.readInt32()
		self.readInt32() # junk data
		
		headerSize = 0x10 + 0x18 * fileCount + stringTableSize
		self.files = []

		for i in range(fileCount):
			self.seek(0x10 + i * 0x18)
			f = PFS0File()
			f.offset = self.readInt64()
			f.size = self.readInt64()
			f.name = 'NULL'
			f.nameOffset = self.readInt32() # just the offset
			self.readInt32() # junk data
			self.partition(f.offset + headerSize, f.size, f)
			
			self.files.append(f)

		stringTable = self.read(stringTableSize)
		
		for i in range(fileCount):
			if i == fileCount - 1:
				self.files[i].name = stringTable[self.files[i].nameOffset:].decode('utf-8').rstrip(' \t\r\n\0')
			else:
				self.files[i].name = stringTable[self.files[i].nameOffset:self.files[i+1].nameOffset].decode('utf-8').rstrip(' \t\r\n\0')
				
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		print('\n%sPFS0\n' % (tabs))
		super(PFS0, self).printInfo(indent)
		'''
		print(tabs + 'titleId = ' + str(self.header.titleId))
		print(tabs + 'rightsId = ' + str(self.header.rightsId))
		print(tabs + 'isGameCard = ' + hex(self.header.isGameCard))
		print(tabs + 'contentType = ' + hex(self.header.contentType))
		print(tabs + 'NCA Size: ' + str(self.header.size))
		print(tabs + 'NCA crypto master key: ' + str(self.header.cryptoType))
		print(tabs + 'NCA crypto master key: ' + str(self.header.cryptoType2))
		
		print('\n%sPartitions:' % (tabs))
		
		for s in self:
			s.printInfo(indent+1)
			print(tabs + 'magic = ' + str(s.magic))
			print(tabs + 'fsType = ' + str(s.fsType))
			print(tabs + 'cryptoType = ' + str(s.cryptoType))
			print(tabs + 'size = ' + str(s.size))
			print(tabs + 'offset = ' + str(s.offset))
			print(tabs + 'cryptoCounter = ' + str(hx(s.cryptoCounter)))
			print(tabs + 'cryptoKey = ' + str(hx(s.cryptoKey)))
			
			print('\n%s\t%s\n' % (tabs, '*' * 64))
			'''

		
class ROMFS(SectionFilesystem):
	def __init__(self, buffer, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(ROMFS, self).__init__(buffer, path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.magic = None
		
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
		self.keyBlobIndex = None
		self.sectionTables = []
		
		super(NcaHeader, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)
		
	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(NcaHeader, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signature1 = self.read(0x100)
		self.signature2 = self.read(0x100)
		self.magic = self.read(0x4)
		self.isGameCard = self.readInt8()
		self.contentType = self.readInt8()
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
			
		self.keyArea = self.read(0x40)
		
		self.keyBlobIndex = (self.cryptoType if self.cryptoType > self.cryptoType2 else self.cryptoType2)-1
		
		if self.titleId.upper() in Titles.keys() and Titles.get(self.titleId.upper()).key:
			self.titleKeyDec = Keys.decryptTitleKey(uhx(Titles.get(self.titleId.upper()).key), self.keyBlobIndex)
		else:
			pass


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
		
		self.header.seek(0x400)

		for i in range(4):
			fs = GetSectionFilesystem(self.header.read(0x200), cryptoKey = self.header.titleKeyDec)

			#print('st end offset = ' + str(self.sectionTables[i].endOffset - self.sectionTables[i].offset))
			#print('offset = ' + hex(self.header.sectionTables[i].offset))
			#print('titleKey = ' + hex(self.header.titleKeyDec))
			try:
				self.partition(self.header.sectionTables[i].offset + fs.sectionStart, self.header.sectionTables[i].endOffset - self.header.sectionTables[i].offset, fs, cryptoKey = self.header.titleKeyDec)
			except BaseException as e:
				print(e)

			if fs.fsType:
				self.sectionFilesystems.append(fs)
		
		
		self.titleKeyDec = None
		self.keyBlobIndex = None

		
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		print('\n%sNCA Archive\n' % (tabs))
		super(Nca, self).printInfo(indent)
		
		print(tabs + 'titleId = ' + str(self.header.titleId))
		print(tabs + 'rightsId = ' + str(self.header.rightsId))
		print(tabs + 'isGameCard = ' + hex(self.header.isGameCard))
		print(tabs + 'contentType = ' + hex(self.header.contentType))
		print(tabs + 'NCA Size: ' + str(self.header.size))
		print(tabs + 'NCA crypto master key: ' + str(self.header.cryptoType))
		print(tabs + 'NCA crypto master key: ' + str(self.header.cryptoType2))
		
		print('\n%sPartitions:' % (tabs))
		
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
		
	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Xci, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.readHeader()
		
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		print('\n%sXCI Archive\n' % (tabs))
		super(Xci, self).printInfo(indent)
		
		print(tabs + 'magic = ' + str(self.magic))
		print(tabs + 'titleKekIndex = ' + str(self.titleKekIndex))
		
		print(tabs + 'gamecardCert = ' + str(hx(self.gamecardCert.magic + self.gamecardCert.unknown1 + self.gamecardCert.unknown2 + self.gamecardCert.data)))
		#print(tabs + 'NCA crypto master key: ' + str(self.cryptoType))
		#print(tabs + 'NCA crypto master key: ' + str(self.cryptoType2))
		
		

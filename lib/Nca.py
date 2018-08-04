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
	def __init__(self, d, sha1):
		self.mediaOffset = int.from_bytes(d[0x0:0x4], byteorder='little', signed=False)
		self.mediaEndOffset = int.from_bytes(d[0x4:0x8], byteorder='little', signed=False)
		
		self.offset = self.mediaOffset * MEDIA_SIZE
		self.endOffset = self.mediaEndOffset * MEDIA_SIZE
		
		self.unknown1 = int.from_bytes(d[0x8:0xc], byteorder='little', signed=False)
		self.unknown2 = int.from_bytes(d[0xc:0x10], byteorder='little', signed=False)
		self.sha1 = sha1
		
		#print('media offset: ' + str(self.mediaOffset * MEDIA_SIZE) + ', end offset: ' + str(self.mediaEndOffset * MEDIA_SIZE))

		
class SectionFilesystem(File):
	def __init__(self, buffer = None, f = None, offset = None, size = None, titleKeyDec = None):
		super(SectionFilesystem, self).__init__()
		
		self.buffer = buffer
		self.fsType = None
		self.cryptoType = None
		self.size = 0
		self.cryptoCounter = None
		self.cryptoKey = titleKeyDec
		
		if f:
			f.partition(offset, size, self)
		else:
			self.f = None
			
		self.files = []
		
		if buffer:
			self.buffer = buffer
			self.fsType = buffer[0x3]
			self.cryptoType = buffer[0x4]
			
			self.cryptoCounter = bytearray((b"\x00"*8) + buffer[0x140:0x148])
			self.cryptoCounter = self.cryptoCounter[::-1]
			
			if self.cryptoType == Type.Crypto.CTR:
				self.setAESCTR()
		
	def setCounter(self, ofs):
		ctr = self.cryptoCounter.copy()
		ofs >>= 4
		for j in range(8):
			ctr[0x10-j-1] = ofs & 0xFF
			ofs >>= 8
		return bytes(ctr)
		
	def open(self, file = None, mode = 'rb'):			
		if isinstance(file, str):
			super(SectionFilesystem, self).open(self.path, mode)
		elif isinstance(file, File):
			self.f = file
		else:
			raise IOError('SFS:open invalid file')
		
		return True

class PFS0File(File):
	def __init__(self):
		super(PFS0File, self).__init__()
		self.name = None
		self.offset = None
		self.size = None
		self.path = None
		
class PFS0(SectionFilesystem):
	def __init__(self, buffer = None, f = None, offset = None, size = None, titleKeyDec = None):
		super(PFS0, self).__init__(buffer, f, offset, size, titleKeyDec)
		if buffer:
			self.size = int.from_bytes(buffer[0x48:0x50], byteorder='little', signed=False)
			self.sectionStart = int.from_bytes(buffer[0x40:0x48], byteorder='little', signed=False)
			
	def __getitem__(self, key):
		if isinstance(key, str):
			for f in self.files:
				if f.name == key:
					return f
		elif isinstance(key, int):
			return self.files[key]
				
		raise IOError('PFSO File Not Found')
		
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
		
	def open(self, path = None, mode = 'rb'):
		r = super(PFS0, self).open(path, mode)
		
		if not r:
			raise IOError('Could not open file ' + self.path)
			
		if self.read(4) != b'PFS0':
			raise IOError('Not a valid PFS0 partition')

		fileCount = self.readInt32()
		stringTableSize = self.readInt32()
		self.readInt32() # junk data
		
		headerSize = 0x10 + 0x18 * fileCount + stringTableSize
		
		self.files = []
		for i in range(fileCount):
			f = PFS0File()
			f.offset = self.readInt64()
			f.size = self.readInt64()
			f.name = ''
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

		
class ROMFS(SectionFilesystem):
	def __init__(self, buffer = None, f = None, offset = None, size = None, titleKeyDec = None):
		super(ROMFS, self).__init__(buffer, f, offset, size, titleKeyDec)
		
def GetSectionFilesystem(buffer = None, f = None, offset = None, size = None, titleKeyDec = None):
	fsType = buffer[0x3]
	if fsType == Type.Fs.PFS0:
		return PFS0(buffer, f, offset, size, titleKeyDec)
		
	if fsType == Type.Fs.ROMFS:
		return ROMFS(buffer, f, offset, size, titleKeyDec)
		
	return SectionFilesystem(buffer, f, offset, size, titleKeyDec)

class Nca(File):
	def __init__(self, file = None):
		super(Nca, self).__init__()
		self.header = None
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
		self.sectionFilesystems = []
		
		if file:
			self.open(file)
			
	def __iter__(self):
		return self.sectionFilesystems.__iter__()
		
	def __getitem__(self, key):
		return self.sectionFilesystems[key]

	def open(self, file = None):
		if isinstance(file, str):
			super(Nca, self).open(file, "rb")
		elif isinstance(file, File):
			self.f = file
		else:
			raise IOError('NCA:open invalid file')
			
		self.readHeader()
		
		if not self.titleId.upper() in Titles.keys():
			print('could not find title key!!! ' + self.titleId)

		
	def readHeader(self):
		self.sectionTables = []
		self.sectionFilesystems = []
		self.seek(0)
		
		self.header = self.read(0x0C00)
		cipher = aes128.AESXTS(uhx(Keys.get('header_key')))
		
		try:
			if self.header[0x200:0x204].decode("utf-8") not in ['NCA3', 'NCA2']:
				self.header = cipher.decrypt(self.header)
		except:
			self.header = cipher.decrypt(self.header)
		
		self.magic = self.header[0x200:0x204].decode("utf-8")
		
		if self.magic not in ['NCA3', 'NCA2']:
			raise Exception('Failed to decrypt NCA header: ' + self.magic)
			
		self.isGameCard = self.header[0x204]
		self.contentType = self.header[0x205]
		self.cryptoType = self.header[0x206]
		self.keyIndex = self.header[0x207]
		self.size = int.from_bytes(self.header[0x208:0x210], byteorder='little', signed=False)
		self.titleId = self.header[0x210:0x218][::-1].hex()
		self.sdkVersion = int.from_bytes(self.header[0x21c:0x220], byteorder='little', signed=False)
		self.cryptoType2 = self.header[0x220]
		self.rightsId = self.header[0x230:0x240].hex()
		self.titleKeyDec = None
		self.keyBlobIndex = (self.cryptoType if self.cryptoType > self.cryptoType2 else self.cryptoType2)-1
		
		if self.titleId.upper() in Titles.keys() and Titles.get(self.titleId.upper()).key:
			self.titleKeyDec = Keys.decryptTitleKey(uhx(Titles.get(self.titleId.upper()).key), self.keyBlobIndex)
		else:
			pass
			#print('could not find title key!')
		
		for i in range(4):
			start = 0x240 + i * 0x10
			end = start + 4
			
			hashStart = 0x280 + i * 0x20
			hashEnd = hashStart + 0x20
			st = SectionTableEntry(self.header[start:end], self.header[hashStart:hashEnd])
			self.sectionTables.append(st)
			
			start = 0x400 + i * 0x200
			end = start + 0x200

			fs = GetSectionFilesystem(self.header[start:end], self, st.offset, None, self.titleKeyDec)
			
			if fs.fsType:
				self.sectionFilesystems.append(fs)
		
		#print('')
		#print('title id ' + str(self.titleId))
		#print('size ' + str(self.size))
		#print('magic: ' + self.magic)
		#print('nca crypto type: ' + str(self.cryptoType))
		
	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		print('\n%sNCA Archive\n' % (tabs))
		super(Nca, self).printInfo(indent)
		
		print(tabs + 'titleId = ' + str(self.titleId))
		print(tabs + 'rightsId = ' + str(self.rightsId))
		print(tabs + 'NCA crypto master key: ' + str(self.cryptoType))
		print(tabs + 'NCA crypto master key: ' + str(self.cryptoType2))
		
		print('\n%sPartitions:' % (tabs))
		
		for s in self:
			s.printInfo(indent+1)
			print(tabs + 'fsType = ' + str(s.fsType))
			print(tabs + 'cryptoType = ' + str(s.cryptoType))
			print(tabs + 'size = ' + str(s.size))
			print(tabs + 'offset = ' + str(s.offset))
			print(tabs + 'cryptoCounter = ' + str(hx(s.cryptoCounter)))
			print(tabs + 'cryptoKey = ' + str(hx(s.cryptoKey)))
			
			print('\n%s\t%s\n' % (tabs, '*' * 64))
			
class GamecardInfo(File):
	def __init__(self, file = None):
		super(GamecardInfo, self).__init__()
		if file:
			self.open(file)
	
	def open(self, file):
		super(GamecardInfo, self).open(file)
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
			
	def open(self, file):
		super(GamecardCertificate, self).open(file)
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
		
	def open(self, file = None):
		super(Xci, self).open(file)
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
		
		

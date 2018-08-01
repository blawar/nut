import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from enum import IntEnum
from Crypto.Cipher import AES
from Crypto.Util import Counter
from File import File
import Keys

MEDIA_SIZE = 0x200

class FsType(IntEnum):
	PFS0 = 0x2
	ROMFS = 0x3
	
class CrypoType(IntEnum):
	NONE = 1
	XTS = 2
	CTR = 3
	BKTR = 4
	NCA0 = 0x3041434

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

		
class SectionFilesystem:
	def __init__(self, buffer = None):
		self.filePath = None
		self.buffer = buffer
		self.fsType = None
		self.cryptoType = None
		self.size = -1
		self.sectionCtr = None
		self.f = None
		self.files = []
		
		if buffer:
			self.buffer = buffer
			self.fsType = buffer[0x3]
			self.cryptoType = buffer[0x4]
			self.sectionCtr = bytearray((b"\x00"*8) + buffer[0x140:0x148])
			self.sectionCtr = self.sectionCtr[::-1]
		
	def calcCtr(self, ofs):
		ctr = self.sectionCtr.copy()
		ofs >>= 4
		for j in range(8):
			ctr[0x10-j-1] = ofs & 0xFF
			ofs >>= 8
		return bytes(ctr)
		
	def openFile(self, path = None):
		if path:
			self.path = path
			
		if not self.path:
			return False
			
		self.f = File(self.path, 'rb')
		
		return True

class PFS0File:
	def __init__(self):
		self.name = None
		self.offset = None
		self.size = None
		self.path = None
		
class PFS0(SectionFilesystem):
	def __init__(self, buffer = None):
		super(PFS0, self).__init__(buffer)
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
		
	def openFile(self, path = None):
		r = super(PFS0, self).openFile(path)
		
		if not r:
			raise IOError('Could not open file ' + self.path)
			
		if self.f.read(4) != b'PFS0':
			raise IOError('Not a valid PFS0 partition')

		fileCount = self.f.readInt32()
		stringTableSize = self.f.readInt32()
		self.f.readInt32() # junk data
		
		self.files = []
		for i in range(fileCount):
			f = PFS0File()
			f.offset = self.f.readInt64()
			f.size = self.f.readInt64()
			f.name = ''
			f.nameOffset = self.f.readInt32() # just the offset
			self.f.readInt32() # junk data
			
			self.files.append(f)

		stringTable = self.f.read(stringTableSize)
		
		for i in range(fileCount):
			if i == fileCount - 1:
				self.files[i].name = stringTable[self.files[i].nameOffset:].decode('utf-8').strip()
			else:
				self.files[i].name = stringTable[self.files[i].nameOffset:self.files[i+1].nameOffset].decode('utf-8').strip()
		
class ROMFS(SectionFilesystem):
	def __init__(self, buffer = None):
		super(ROMFS, self).__init__(buffer)
		
def GetSectionFilesystem(buffer):	
	fsType = buffer[0x3]
	if fsType == FsType.PFS0:
		return PFS0(buffer)
		
	if fsType == FsType.ROMFS:
		return ROMFS(buffer)
		
	return SectionFilesystem(buffer)

class Nca:
	def __init__(self, fileName = None):
		self.fileName = fileName
			
		self.header = None
		self.titleId = None
		self.sectionTables = []
		self.sectionFilesystems = []
		
		if fileName:
			self.open()

	def open(self, fileName = None):
		if fileName:
			self.fileName = fileName
			
		print('opening ' + self.fileName)
		self.f = open(self.fileName, "rb")
		self.readHeader()
		
		if not self.titleId.upper() in Titles.keys():
			print('could not find title key!!! ' + self.titleId)
		
		crypto = aes128.AESCTR(Keys.decryptTitleKey(uhx(Titles.get(self.titleId.upper()).key), 0), self.sectionFilesystems[1].calcCtr(self.sectionTables[1].offset))
		self.f.seek(self.sectionTables[1].offset)
		body = self.f.read(0x300)

		Hex.dump(crypto.decrypt(body))		
		
	def readHeader(self):
		self.sectionTables = []
		self.sectionFilesystems = []
		
		self.header = self.f.read(0x0C00)
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
		self.rightsId = self.header[0x230:0x240][::-1].hex()
		
		for i in range(4):
			start = 0x240 + i * 0x10
			end = start + 4
			
			hashStart = 0x280 + i * 0x20
			hashEnd = hashStart + 0x20
			self.sectionTables.append(SectionTableEntry(self.header[start:end], self.header[hashStart:hashEnd]))
			
			start = 0x400 + i * 0x200
			end = start + 0x200
			self.sectionFilesystems.append(GetSectionFilesystem(self.header[start:end]))
		
		print('')
		print('title id ' + str(self.titleId))
		print('size ' + str(self.size))
		print('magic: ' + self.magic)
		print('nca crypto type: ' + str(self.cryptoType))
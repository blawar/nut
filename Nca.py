import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from enum import IntEnum
from Crypto.Cipher import AES
from Crypto.Util import Counter
import Keys

header_key = 'AEAAB1CA08ADF9BEF12991F369E3C567D6881E4E4A6A47A51F6E4877062D542D'
key = '3aa8e6d97c620e57a92ce77c9527f766'

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
		
		print('media offset: ' + str(self.mediaOffset * MEDIA_SIZE) + ', end offset: ' + str(self.mediaEndOffset * MEDIA_SIZE))

		
class SectionFilesystem:
	def __init__(self, buffer):
		self.buffer = buffer
		self.fsType = buffer[0x3]
		self.cryptoType = buffer[0x4]
		self.size = -1
		self.sectionCtr = bytearray((b"\x00"*8) + buffer[0x140:0x148])
		self.sectionCtr = self.sectionCtr[::-1]
		#self.currentCtr = self.calcCtr(0)
		
	def calcCtr(self, ofs):
		ctr = self.sectionCtr.copy()
		ofs >>= 4
		for j in range(8):
			ctr[0x10-j-1] = ofs & 0xFF
			ofs >>= 8
		return bytes(ctr)

class PFS0(SectionFilesystem):
	def __init__(self, buffer):
		super(PFS0, self).__init__(buffer)
		#self.size = int.from_bytes(buffer[0x28:0x2C], byteorder='little', signed=False)
		self.size = int.from_bytes(buffer[0x48:0x50], byteorder='little', signed=False)
		self.sectionStart = int.from_bytes(buffer[0x40:0x48], byteorder='little', signed=False)
		#self.sectionStart = buffer[0x40:0x48]
		
		print('fs size: ' + str(self.size))
		print('crypto: ' + str(self.cryptoType))
		print('section start: ' + str(self.sectionStart))
		
class ROMFS(SectionFilesystem):
	def __init__(self, buffer):
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
		
		crypto = aes128.AESCTR(Keys.decryptTitleKey(uhx(key), 0), self.sectionFilesystems[1].calcCtr(self.sectionTables[1].offset))
		self.f.seek(self.sectionTables[1].offset)
		body = self.f.read(0x300)

		Hex.dump(crypto.decrypt(body))		
		
	def readHeader(self):
		self.sectionTables = []
		self.sectionFilesystems = []
		
		self.header = self.f.read(0x0C00)
		cipher = aes128.AESXTS(uhx(header_key))
		
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
import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from Crypto.Cipher import AES
from Crypto.Util import Counter
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
			self.f = File(self.path, mode)
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
			
		if self.f.read(4) != b'PFS0':
			raise IOError('Not a valid PFS0 partition')

		fileCount = self.f.readInt32()
		stringTableSize = self.f.readInt32()
		self.f.readInt32() # junk data
		
		headerSize = 0x10 + 0x18 * fileCount + stringTableSize
		
		self.files = []
		for i in range(fileCount):
			f = PFS0File()
			f.offset = self.f.readInt64()
			f.size = self.f.readInt64()
			f.name = ''
			f.nameOffset = self.f.readInt32() # just the offset
			self.f.readInt32() # junk data
			self.f.partition(f.offset + headerSize, f.size, f)
			
			self.files.append(f)

		stringTable = self.f.read(stringTableSize)
		
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

class Nca:
	def __init__(self, file = None):			
		self.header = None
		self.titleId = None
		self.sectionTables = []
		self.sectionFilesystems = []
		
		if file:
			self.open(file)
			
	def __iter__(self):
		return self.sectionFilesystems.__iter__()
		
	def __getitem__(self, key):
		return self.sectionFilesystems[key]

	def open(self, file = None):
		#print('nca open')
		if isinstance(file, str):
			self.f = File(file, "rb")
		elif isinstance(file, File):
			self.f = file
		else:
			raise IOError('NCA:open invalid file')
			
		self.readHeader()
		
		if not self.titleId.upper() in Titles.keys():
			print('could not find title key!!! ' + self.titleId)
		
		self.sectionFilesystems[1].seek(0)

		#Hex.dump(self.sectionFilesystems[1].read(0x300))
		
	def readHeader(self):
		self.sectionTables = []
		self.sectionFilesystems = []
		self.f.seek(0)
		
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
		self.rightsId = self.header[0x230:0x240].hex()
		self.titleKeyDec = None
		
		if self.titleId.upper() in Titles.keys():
			self.titleKeyDec = Keys.decryptTitleKey(uhx(Titles.get(self.titleId.upper()).key), 0)
		
		for i in range(4):
			start = 0x240 + i * 0x10
			end = start + 4
			
			hashStart = 0x280 + i * 0x20
			hashEnd = hashStart + 0x20
			st = SectionTableEntry(self.header[start:end], self.header[hashStart:hashEnd])
			self.sectionTables.append(st)
			
			start = 0x400 + i * 0x200
			end = start + 0x200

			self.sectionFilesystems.append(GetSectionFilesystem(self.header[start:end], self.f, st.offset, None, self.titleKeyDec))
		
		#print('')
		#print('title id ' + str(self.titleId))
		#print('size ' + str(self.size))
		#print('magic: ' + self.magic)
		#print('nca crypto type: ' + str(self.cryptoType))
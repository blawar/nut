import aes128
import Title
import Titles
import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk

header_key = 'AEAAB1CA08ADF9BEF12991F369E3C567D6881E4E4A6A47A51F6E4877062D542D'

class Nca:
	def __init__(self, fileName = None):
		self.fileName = fileName
		
		if fileName:
			self.open()
			
		self.header = None
		self.titleId = None

	def open(self, fileName = None):
		if fileName:
			self.fileName = fileName
			
		print('opening ' + self.fileName)
		self.f = open(self.fileName, "rb")
		self.readHeader()
		
	def readHeader(self):
		self.header = self.f.read(0x0C00)
		cipher = aes128.AESXTS(uhx(header_key))
		
		try:
			if self.header[0x200:0x204].decode("utf-8") not in ['NCA3', 'NCA2']:
				self.header = cipher.decrypt(self.header)
		except:
			self.header = cipher.decrypt(self.header)
		
		self.magic = self.header[0x200:0x204].decode("utf-8")
		self.isGameCard = self.header[0x204]
		self.contentType = self.header[0x205]
		self.cryptoType = self.header[0x206]
		self.keyIndex = self.header[0x207]
		self.size = int.from_bytes(self.header[0x208:0x20f], byteorder='little', signed=False)
		self.titleId = self.header[0x210:0x218][::-1].hex()
		print('title id ' + str(self.titleId))
		print('size ' + str(self.size))
		print('magic: ' + self.magic)
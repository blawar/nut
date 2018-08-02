from enum import IntEnum
import Type
import aes128

class File:
	def __init__(self, path = None, mode = None):
		self.offset = 0
		self.size = None
		self.f = None
		self.crypto = None
		self.cryptoKey = None
		self.cryptoType = Type.Crypto.NONE
		self.cryptoCounter = None
		self.isPartition = False
		
		if path:
			self.open(path, mode)
			
	def setAESCTR(self, key = None, counter = None):
		if key:
			self.cryptoKey = key
			
		if counter:
			self.cryptoCounter = counter

		self.crypto = aes128.AESCTR(self.cryptoKey, self.setCounter(self.offset))
		self.cryptoType = Type.Crypto.CTR
			
	def partition(self, offset = 0, size = None, n = None):
		if not n:
			n = File()
		#print('partition: ' + str(self) + ', ' + str(n))
			
		n.offset = offset
		
		if not size:
			size = self.size - n.offset - self.offset
			
		n.size = size
		n.f = self
		n.isPartition = True
		
		return n
		
	def read(self, size = None):
		if not size:
			size = self.size
		if self.crypto:
			r = self.crypto.decrypt(self.f.read(size))
			return r
		return self.f.read(size)
		
	def readInt8(self, byteorder='little', signed = False):
		return self.f.read(1)
		
	def readInt16(self, byteorder='little', signed = False):
		return int.from_bytes(self.f.read(2), byteorder=byteorder, signed=signed)
		
	def readInt32(self, byteorder='little', signed = False):
		return int.from_bytes(self.f.read(4), byteorder=byteorder, signed=signed)
		
	def readInt64(self, byteorder='little', signed = False):
		return int.from_bytes(self.f.read(8), byteorder=byteorder, signed=signed)
		
	def write(self, buffer):
		return self.f.write(buffer)
	
	def seek(self, offset, from_what = 0):
		if not self.isOpen():
			raise IOError('Trying to seek on closed file')

		f = self.f
		

		if from_what == 0:
			# seek from begining
			if self.crypto:
				self.crypto.set_ctr(self.setCounter(self.offset + offset))
				
			return f.seek(self.offset + offset)
		elif from_what == 1:
			# seek from current position
			r = f.seek(self.offset + offset)
			
			if self.crypto:
				self.crypto.set_ctr(self.setCounter(self.offset + self.tell()))
				
			return r
		elif from_what == 2:
			# see from end
			if offset > 0:
				raise Exception('Invalid seek offset')
				
			return f.seek(self.offset + offset + self.size)
			
		raise Exception('Invalid seek type')
		
	def rewind(self, offset = None):
		if offset:
			self.seek(-offset, 1)
		else:
			self.seek(0)
		
	def open(self, path, mode):
		if self.isOpen():
			self.close()
			
		self.f = open(path, mode)
		
		self.f.seek(0,2)
		self.size = self.f.tell()
		self.f.seek(0,0)
		
	def close(self):
		self.f.close()
		self.f = None
		
	def tell(self):
		return self.f.tell() - self.offset
		
	def isOpen(self):
		return self.f != None
		
	def setCounter(self, ofs):
		ctr = self.sectionCtr.copy()
		ofs >>= 4
		for j in range(8):
			ctr[0x10-j-1] = ofs & 0xFF
			ofs >>= 8
		return bytes(ctr)
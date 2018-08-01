
class File:
	def __init__(self, path = None, mode = None):
		self.parent = None
		self.offset = 0
		self.size = None
		self.f = None
		if path:
			self.open(path, mode)
			
	def partition(self, f, offset = 0, size = None):
		if self.isOpen():
			self.close()
		
		n = File()
		n.parent = self
		n.offset = self.offset + offset
		
		if not size:
			size = self.size - n.offset - self.offset
			
		n.size = size
		n.f = f
		
		return n
		
	def read(self, size):
		return self.f.read(size)
		
	def readInt32(self, byteorder='little', signed = False):
		return int.from_bytes(self.f.read(4), byteorder=byteorder, signed=signed)
		
	def readInt64(self, byteorder='little', signed = False):
		return int.from_bytes(self.f.read(8), byteorder=byteorder, signed=signed)
		
	def write(self, buffer):
		return self.f.write(buffer)
	
	def seek(self, offset, from_what = 0):
		#if self.parent:
		#	f = self.parent
		#else:
		#	f = self.f
		f = self.f

		if from_what == 0:
			# seek from begining
			return f.seek(self.offset + offset)
		#elif from_what == 1:
			# seek from current position
		#	pass
		elif from_what == 2:
			# see from end
			if offset > 0:
				raise Exception('Invalid seek offset')
				
			return f.seek(self.offset + offset + self.size)
			
		raise Exception('Invalid seek type')
		
	def open(self, path, mode):
		if self.isOpen():
			self.close()
			
		self.f = open(path, mode)
		
	def close(self):
		close(self.f)
		self.f = None
		
	def isOpen(self):
		return self.f != None
import tqdm
import time
import threading

global lst
lst = []
lock = threading.Lock()

def print_(s):
	if isActive():
		if lst[0].isOpen():
			lst[0].tqdm.write(s)
	else:
		print(s)

def isActive():
	for i in lst:
		if i.isOpen():
			return True
	return False

def create(size, desc = None, unit='B'):
	#lock.acquire()
	position = len(lst)

	for i, s in enumerate(lst):
		if not s.isOpen():
			position = i
			break

	s = Status(size, position, desc=desc, unit=unit)

	if position >= len(lst):
		lst.append(s)
	else:
		lst[position] = s

	#lock.release()
	return s

class Status:
	def __init__(self, size, position = 0, desc = None, unit='B'):
		self.position = position
		self.size = size
		self.i = 0
		self.timestamp = time.clock()

		#if position == 0:
		self.tqdm = tqdm.tqdm(total=size, unit=unit, unit_scale=True, position = position, desc=desc, leave=False, ascii = True)
		#else:
		#	self.size = None
		#	self.tqdm = None

	def add(self, v=1):
		#lock.acquire()
		if self.isOpen():
			self.i += v
			self.tqdm.update(v)
		#lock.release()

	def update(self, v=1):
		self.add(v)

	def __del__(self):
		self.close()

	def close(self):
		if self.isOpen():
			#lock.acquire()
			try:
				self.tqdm.close()
			except:
				pass
			self.tqdm = None
			self.size = None
			#lock.release()

	def setDescription(self, desc, refresh = False):
		if self.isOpen():
			#lock.acquire()
			self.tqdm.set_description(str(self.position) + '> ' + desc, refresh = refresh)
			#lock.release()

	def isOpen(self):
		return True if self.size != None else False
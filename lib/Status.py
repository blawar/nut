import tqdm
import Print
import time

global lst
lst = []

def create(size, desc = None, unit='B'):
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
	return s

class Status:
	def __init__(self, size, position = 0, desc = None, unit='B'):
		self.size = size
		self.i = 0
		self.timestamp = time.clock()

		self.tqdm = tqdm.tqdm(total=size, unit=unit, unit_scale=True, desc=desc, leave=False, position = position)

	def add(self, v=1):
		if self.tqdm:
			self.i += v
			self.tqdm.update(v)

	def update(self, v=1):
		self.add(v)

	def __del__(self):
		self.close()

	def close(self):
		if self.tqdm:
			self.tqdm.close()
			self.tqdm = None

	def setDescription(self, desc, refresh = False):
		if self.tqdm:
			self.tqdm.set_description(desc, refresh = refresh)

	def isOpen(self):
		return True if self.tqdm else False
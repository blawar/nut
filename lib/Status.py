import tqdm
import Print

global lst
lst = []

def create(size):
	position = len(lst)

	for i, s in enumerate(lst):
		pass

	s = Status(size, len(lst))
	lst.append(s)
	return s

class Status:
	def __init__(self, size, position = 0, desc = None):
		self.size = size
		self.i = 0

		self.tqdm = tqdm.tqdm(total=size, unit='B', unit_scale=True, desc=desc, leave=False, position = position)

	def add(self, v):
		if self.tqdm:
			self.i += v
			self.tqdm.update(v)

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
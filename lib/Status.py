import tqdm
import time
import threading
import Config
import json
import sys

global threadRun
global lst
lst = []
lock = threading.Lock()
threadRun = True

def print_(s):
	for i in lst:
		if i.isOpen():
			try:
				i.tqdm.write(s)
				return
			except:
				pass
	print(s)

def isActive():
	for i in lst:
		if i.isOpen():
			return True
	return False

def loopThread():
	global threadRun
	while threadRun:
		time.sleep(1)
		if Config.jsonOutput:
			data = []
			for i in lst:
				if i.isOpen():
					try:
						data.append({'description': i.desc, 'i': i.i, 'size': i.size, 'elapsed': time.clock() - i.timestamp, 'speed': i.a / (time.clock() - i.ats) })
						i.a = 0
						i.ats = time.clock()
					except:
						pass
			print_(json.dumps(data))
			sys.stdout.flush()

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
		self.a = 0
		self.ats = time.clock()
		self.timestamp = time.clock()
		self.desc = desc

		if not Config.jsonOutput:
			self.tqdm = tqdm.tqdm(total=size, unit=unit, unit_scale=True, position = position, desc=desc, leave=False, ascii = True)
		else:
			self.tqdm = None

	def add(self, v=1):
		#lock.acquire()
		if self.isOpen():
			self.i += v
			self.a += v
			try:
				self.tqdm.update(v)
			except:
				self.close()
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
		self.desc = desc
		if self.isOpen():
			#lock.acquire()
			try:
				self.tqdm.set_description(desc, refresh = refresh)
			except:
				self.close()
			#lock.release()

	def isOpen(self):
		return True if self.size != None else False

def start():
	global threadRun
	threadRun = True
	thread = threading.Thread(target = loopThread, args =[])
	#thread.daemon = True
	thread.start()

def close():
	global threadRun
	threadRun = False
	#thread.close()
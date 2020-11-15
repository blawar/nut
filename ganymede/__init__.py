import nut
import json
import os
from hashlib import sha256
import urllib.parse

def _sha256(buf):
	hash = sha256()
	hash.update(buf)

	return hash.hexdigest().upper()

class Storage:
	def __init__(self, j):
		self.path = None
		self.index = None
		self.tfl = None
		self.prefix = 'https://localhost/'
		self.maxStorageSize = 0
		self.maxStorageFileSize = 0
		self.maxFileSize = 0
		self.minFileSize = 0
		self.totalSize = 0

		self.map = {}

		for key in j:
			if key in self.__dict__:
				self.__dict__[key] = j[key]

		self.maxStorageSize = int(self.maxStorageSize)
		self.maxStorageFileSize = int(self.maxStorageFileSize)
		self.maxFileSize = int(self.maxFileSize)
		self.minFileSize = int(self.minFileSize)

		os.makedirs(self.path, exist_ok=True)
		os.makedirs(os.path.dirname(self.index), exist_ok=True)
		os.makedirs(os.path.dirname(self.tfl), exist_ok=True)

		self.load()

	def contains(self, tid, version):
		return tid.upper() in self.map

	def fits(self, sz):
		return (self.maxFileSize == 0 or sz <= self.maxFileSize) and (self.maxStorageSize == 0 or (self.size() + sz <= self.maxStorageSize))

	def refreshSize(self):
		self.totalSize = 0
		for tid, o in self.map.items():
			for version, data in o.items():
				self.totalSize += (data['size'])

	def load(self):
		try:
			with open(self.index, encoding="utf-8-sig") as f:
				try:
					self.map = json.loads(f.read())
				except BaseException:
					print('json file is corrupted: %s' % self.index)
					raise

		except BaseException as e:
			print('except ' + str(e))
			pass
		self.refreshSize()

	def save(self):
		with open(self.index, 'w') as outfile:
			json.dump(self.map, outfile, indent=4)

	def encodeFilePath(self, obj, row):
		return self.prefix + obj['file'] + '#' + urllib.parse.quote(os.path.basename(row['path']))

	def saveTfl(self):
		files = []
		for tid, o in self.map.items():
			for version, data in o.items():

				if len(data['files']) == 1:
					url = self.encodeFilePath(data['files'][0], data)
					files.append(url)
				elif len(data['files']) > 1:
					lastSize = -1
					bits = []
					for f in data['files']:
						url = self.encodeFilePath(f, data)
						if f['size'] != lastSize:
							bits.append(str(f['size']))
							lastSize = int(f['size'])
						bits.append(urllib.parse.quote(url, safe='_'))
					files.append('jbod:' + ('/'.join(bits)))

		with open(self.tfl, 'w') as outfile:
			json.dump({'files': files}, outfile, indent=4)

	def size(self):
		return self.totalSize

	def isFull(self):
		return self.maxStorageSize != 0 and self.size() >= self.maxStorageSize

	def freeSpace(self):
		if self.maxStorageSize == 0:
			return 0xFFFFFFFFFFFFFFFF

		return self.maxStorageSize - self.size()

	def split(self, filePath, size):
		if not size:
			size = os.path.getsize(filePath)

		result = []

		with open(filePath, 'rb') as r:
			while True:
				buffer = r.read(self.maxStorageFileSize)
				if not buffer:
					break

				hash = _sha256(buffer)

				with open(os.path.join(self.path, hash), 'wb') as w:
					w.write(buffer)

				result.append({'file': hash, 'size': len(buffer)})

		return result

	def push(self, tid, version, filePath, size=0):
		if self.contains(tid, version):
			return True

		if not size:
			size = os.path.getsize(filePath)

		if not self.fits(size):
			return False

		entry = {'path': filePath, 'size': size}

		tid = tid.upper()

		version = str(version)

		if tid not in self.map:
			self.map[tid] = {}

		entry['files'] = self.split(filePath, size)

		self.map[tid][version] = entry
		self.save()
		self.saveTfl()
		return True

	def findFileToMove(self, free, blacklist=[]):
		if free <= 0:
			return None

		currentFile = None

		for tid, o in self.map.items():
			for version, data in o.items():
				if currentFile is None or (currentFile['size'] < data['size'] and data['size'] <= free):
					if data['path'] not in blacklist:
						currentFile = {'tid': tid, 'version': version, 'files': data['files'], 'size': data['size'], 'path': data['path']}

		return currentFile

	def move(self, file, storage):
		moveLog = {}
		try:
			for f in file['files']:
				src = os.path.join(self.path, os.path.basename(f['file']))
				dest = os.path.join(storage.path, os.path.basename(f['file']))
				os.rename(src, dest)
				moveLog[dest] = src

			if file['tid'] not in storage.map:
				storage.map[file['tid']] = {}

			#storage.map[file['tid']][file['version']] = {'files': file['files'], 'size': file['size']}
			storage.map[file['tid']][file['version']] = self.map[file['tid']][file['version']]
			del self.map[file['tid']][file['version']]
			storage.save()
			self.save()
		except BaseException:
			for dest, src in moveLog.items():
				try:
					os.rename(dest, src)
				except BaseException:
					pass
			raise
			print('move exception')
			return False
		self.refreshSize()
		storage.refreshSize()
		print('storage1: %dMB, storage2: %dMB' % (self.size(), storage.size()))
		#print('moved %s : %s from %s -> %s' % (file['tid'], file['version'], self.path, storage.path))
		return True

	def print(self):
		print('path:\t%s' % str(self.path))
		print('index:\t%s' % str(self.index))
		print('tfl:\t%s' % str(self.tfl))

		print('maxStorageSize:\t%sMB' % (int(self.maxStorageSize) // 1000000))
		print('maxStorageFileSize:\t%sMB' % (int(self.maxStorageFileSize) // 1000000))
		print('maxFileSize:\t%sMB' % (int(self.maxFileSize) // 1000000))
		print('minFileSize:\t%sMB' % (int(self.minFileSize) // 1000000))
		print('\n\n')


class Config:
	def __init__(self, confFile):
		with open(confFile, encoding='utf8') as f:
			j = json.load(f)

		self.storages = []

		for e in j['storages']:
			self.storages.append(Storage(e))

	def print(self):
		for i in self.storages:
			i.print()


class Ganymede:
	def __init__(self, conf):
		self.config = Config(conf)
		self.fix()

	def print(self):
		self.config.print()

	def verify(self):
		return False

	def contains(self, tid, version):
		for storage in self.config.storages:
			if storage.contains(tid, version):
				return True
		return False

	def moveFile(self, storage, file):
		for storage2 in self.config.storages:
			if storage2.path == storage.path:
				continue

			if storage2.fits(file['size']):
				if storage.move(file, storage2):
					return True
			else:
				print('does not fit on ' + storage2.path + ', ' + str(storage2.freeSpace() // 1000000))
		return False

	def fix(self):
		print('fixing...')
		for storage in self.config.storages:
			blacklist = []
			print('storage: %s %dMB' % (storage.path, storage.size() // 1000000))
			while storage.isFull():
				file = storage.findFileToMove(storage.freeSpace() * -1, blacklist)

				if not file:
					continue

				if not self.moveFile(storage, file):
					print('failed to move %s : %s' % (file['tid'], file['version']))

				blacklist.append(file['path'])
		for storage in self.config.storages:
			storage.saveTfl()
		print('fix fin')

	def push(self, tid, version, filePath, size=0):
		return False
		if self.contains(tid, version):
			return True

		for storage in self.config.storages:
			if storage.push(tid, version, filePath, size):
				print('pushed %s %s - %s' % (tid.upper(), str(version), filePath))
				return True

		return False

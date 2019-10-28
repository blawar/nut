#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import time
import json
import nut
from nut import Title
import operator
from nut import Config
from nut import Print
import threading

global titles
titles = None

global nsuIdMap
nsuIdMap = {}

global regionTitles
regionTitles = {}

def data(region = None, language = None):
	global regionTitles
	global titles

	if region:
		if not region in regionTitles:
			regionTitles[region] = {}

		if not language in regionTitles[region]:
			filePath = 'titledb/%s.%s.json' % (region, language)
			if os.path.isfile(filePath):
				regionTitles[region][language] = loadTitlesJson(filePath)
			else:
				try:
					os.mkdir('titledb')
				except:
					pass

				url = 'https://raw.githubusercontent.com/blawar/titledb/master/%s.%s.json' % (region, language)
				#https://raw.githubusercontent.com/blawar/nut/master/titledb/HK.zh.json
				nut.downloadFile(url, filePath)
				if os.path.isfile(filePath):
					regionTitles[region][language] = loadTitlesJson(filePath)
				else:
					regionTitles[region][language] = {}

		return regionTitles[region][language]

	if titles == None:
		load()
	return titles

def items(region = None, language = None):
	if region:
		return regionTitles[region][language].items()

	return titles.items()

def get(key, region = None, language = None):
	key = key.upper()

	if not key in data(region, language):
		t = Title.Title()
		t.setId(key)
		data(region, language)[key] = t
	return data(region, language)[key]

def getNsuid(id, region, language):
	id = int(id)

	map = data(region, language)

	for t in map:
		if map[t].nsuId == id:
			return map[t]

	title = Title.Title()
	title.setNsuId(id)

	map[str(id)] = title
	return title

def hasNsuid(id, region, language):
	id = int(id)

	map = data(region, language)

	for t in map:
		if map[t].nsuId == id:
			return True

	return False
	
def contains(key, region = None):
	return key in titles

def erase(id):
	id = id.upper()
	del titles[id]
	
def set(key, value):
	titles[key] = value
	
	
def keys(region = None, language = None):
	if region:
		return regionTitles[region][language].keys()

	return titles.keys()
	
def loadTitleFile(path, silent = False):
	timestamp = time.process_time()
	with open(path, encoding="utf-8-sig") as f:
		loadTitleBuffer(f.read(), silent)
	Print.info('loaded ' + path + ' in ' + str(time.process_time() - timestamp) + ' seconds')
	
def loadTitleBuffer(buffer, silent = False):
	global nsuIdMap;
	firstLine = True
	importedRegions = {}
	map = ['id', 'key', 'name']
	for line in buffer.split('\n'):
		line = line.strip()
		if len(line) == 0 or line[0] == '#':
			continue
		if firstLine:
			firstLine = False
			if re.match('[A-Za-z\|\s]+', line, re.I):
				map = line.split('|')
				
				i = 0
				while i < len(map):
					if map[i] == 'RightsID':
						map[i] = 'id'
					if map[i] == 'TitleKey':
						map[i] = 'key'
					if map[i] == 'Name':
						map[i] = 'name'
					i += 1
				continue
		
		t = Title.Title()
		t.loadCsv(line, map)
		
		if not isinstance(t.id, str):
			continue

		if 'nsuId' in map:
			nsuIdMap[t.nsuId] = t.id

		title = get(t.id, None, None)
			
		titleKey = title.key
		title.loadCsv(line, map)

		if not silent and titleKey != titles[t.id].key:
			Print.info('Added new title key for ' + str(titles[t.id].name) + '[' + str(t.id) + ']')


confLock = threading.Lock()

def loadTitlesJson(filePath = 'titledb/titles.json'):
	newTitles = {}
	confLock.acquire()
	try:
		if os.path.isfile(filePath):
			timestamp = time.process_time()
			with open(filePath, encoding="utf-8-sig") as f:
				for i, k in json.loads(f.read()).items():
					newTitles[i] = Title.Title()
					newTitles[i].__dict__ = k
					newTitles[i].setId(i)

			Print.info('loaded ' + filePath + ' in ' + str(time.process_time() - timestamp) + ' seconds')
	except BaseException as e:
		print("load titles json exception: " + str(e))

	confLock.release()
	return newTitles

def load():
	confLock.acquire()
	global titles
	titles = {}

	if os.path.isfile("titledb/titles.json"):
		timestamp = time.process_time()
		with open('titledb/titles.json', encoding="utf-8-sig") as f:
			try:
				items = json.loads(f.read()).items()
			except:
				Print.error('json file is corrupted: titledb/titles.json')
				confLock.release()
				return False
			for i, k in items:
				if i != '0100000000000816':
					titles[i] = Title.Title()
					titles[i].__dict__ = k
					titles[i].setId(i)

		Print.info('loaded titledb/titles.json in ' + str(time.process_time() - timestamp) + ' seconds')

		'''
	if os.path.isfile("titles.txt"):
		loadTitleFile('titles.txt', True)

	try:
		files = [f for f in os.listdir(Config.paths.titleDatabase) if f.endswith('.txt')]
		files.sort()
	
		for file in files:
			loadTitleFile(Config.paths.titleDatabase + '/' + file, False)
	except BaseException as e:
		Print.error('title load error: ' + str(e))
		'''
	confLock.release()
	#loadTxtDatabases()

def parsePersonalKeys(path):
	Print.info('loading personal keys ' + path)
	parsed_keys = {}
	with open(path, encoding='utf8', errors='ignore') as f:
		lines = f.readlines()

		for line in lines:
			if 'Ticket' in line:
				pass
			elif 'Rights ID' in line:
				rid = line.split(': ')[1].strip()
			elif 'Title ID' in line:
				tid = line.split(': ')[1].strip()
			elif 'Titlekey' in line:
				tkey = line.split(': ')[1].strip()

				if not tid.endswith('800'):
					parsed_keys[rid] = tkey

	for rightsId, key in parsed_keys.items():
		rightsId = rightsId.upper()
		key = key.upper()
		titleId = rightsId[0:16]
		title = get(titleId)
		if title.key != key:
			title.setId(rightsId)
			title.setKey(key)
			Print.info('Added new title key for %s[%s]' % (title.name, titleId))
		#print("{}|{}".format(k, v))

def loadTxtDatabases():
	confLock.acquire()

	if os.path.isfile("titles.txt"):
		loadTitleFile('titles.txt', True)

	try:
		files = [f for f in os.listdir(Config.paths.titleDatabase) if f.endswith('.txt')]
		files.sort()
	
		for file in files:
			if file.endswith('personal_keys.txt'):
				parsePersonalKeys(Config.paths.titleDatabase + '/' + file)
			else:
				loadTitleFile(Config.paths.titleDatabase + '/' + file, False)

	except BaseException as e:
		Print.error('title load error: ' + str(e))
	confLock.release()

	
def export(fileName = 'titles.txt', map = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region', 'retailOnly']):
	buffer = ''
	
	buffer += '|'.join(map) + '\n'
	for key in sorted(titles):
		buffer += titles[key].serialize(map) + '\n'
		
	with open(fileName, 'w', encoding='utf-8') as csv:
		csv.write(buffer)

def saveTitlesJson(newTitles, fileName = 'titledb/titles.json'):
	confLock.acquire()
	try:
		j = {}

		for i in sorted(newTitles):
			k = newTitles[i]
			if not k.nsuId:
				continue
			if k.id and not k.rightsId:
				title = get(k.id)
				title.setVersion(title.version)
				if title.rightsId:
					k.setId(title.rightsId)
			j[k.nsuId] = k.exportDict(True)
		with open(fileName, 'w') as outfile:
			json.dump(j, outfile, indent=4)
	except:
		confLock.release()
		raise

	confLock.release()

def save(fileName = 'titledb/titles.json', full = True):
	confLock.acquire()
	try:
		j = {}
		for i in sorted(titles):
			k = titles[i]
			if not k.id or k.id == '0000000000000000':
				continue

			j[k.id] = k.exportDict(full = full)

		with open(fileName, 'w') as outfile:
			json.dump(j, outfile, indent=4)
	except:
		confLock.release()
		raise

	confLock.release()

def saveRegion(region, language):
	saveTitlesJson(data(region, language), 'titledb/%s.%s.json' % (region, language))

def saveAll(fileName = 'titledb/titles.json'):
	for region in cdn.regions():
		for language in cdn.Shogun.countryLanguages(region):
			saveTitlesJson(data(region, language), 'titledb/%s.%s.json' % (region, language))

	save(fileName)

class Queue:
	def __init__(self):
		self.queue = []
		self.lock = threading.Lock()
		self.i = 0

	def add(self, id, skipCheck = False):
		self.lock.acquire()
		id = id.upper()
		if not id in self.queue and (skipCheck or self.isValid(id)):
			self.queue.append(id)
		self.lock.release()

	def shift(self):
		self.lock.acquire()
		if self.i >= len(self.queue):
			self.lock.release()
			return None

		self.i += 1

		r =self.queue[self.i-1]
		self.lock.release()
		return r

	def empty(self):
		return bool(self.size() == 0)

	def get(self, idx = None):
		if idx == None:
			return self.queue
		return self.queue[idx]

	def isValid(self, id):
		return contains(id)

	def load(self):
		try:
			with open('conf/queue.txt', encoding="utf-8-sig") as f:
				for line in f.read().split('\n'):
					self.add(line.strip())
		except BaseException as e:
			pass

	def size(self):
		return len(self.queue) - self.i

	def save(self):
		self.lock.acquire()
		try:
			with open('conf/queue.txt', 'w', encoding='utf-8') as f:
				for id in self.queue:
					f.write(id + '\n')
		except:
			pass
		self.lock.release()

global queue
queue = Queue()

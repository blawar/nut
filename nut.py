#!/usr/bin/python3
# -*- coding: utf-8 -*-
# place this file in your CDNSP directory
# add the following line to the top of your CDNSP.py file:
# from tqdm import tqdm

import os
import re
import pathlib
import urllib3
import json
try:
	import CDNSP
	hasCDNSP = True
except:
	hasCDNSP = False

nsps = []
titleWhitelist = []
titleBlacklist = []

class Title:
	def __init__(self):
		self.id = None
		self.rightsId = None
		self.isDLC = None
		self.idExt = None
		self.updateId = None
		self.path = None
		self.version = None
		
	def loadCsv(self, line):
		split = line.split('|')
		self.setId(split[0].strip())
		self.setName(split[2].strip())
		self.setKey(split[1].strip())

		
	def setId(self, id):
		if not id or self.id:
			return
			
		id = id.upper();
		
		try:
			i = int(id, 16)
		except:
			return
		
		if len(id) == 32:
			self.id = id[:16]
			self.rightsId = id
		elif len(id) == 16:
			self.id = id[:16]
		else:
			return
		
		titleIdNum = int(self.id, 16)
		
		if self.id:
			self.baseId = '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		else:
			self.baseId = None
		
		self.isDLC = (titleIdNum & 0xFFFFFFFFFFFFE000) != (titleIdNum & 0xFFFFFFFFFFFFF000)
		#self.isBase = self.id == titleIdNum & 0xFFFFFFFFFFFFE000
		self.idExt = titleIdNum & 0x0000000000000FFF
		
		if self.isDLC:
			# dlc
			pass
		elif self.idExt == 0:
			# base
			self.updateId = '%s800' % self.id[:-3]
		else:
			# update
			pass
			
	def setName(self, name):
		self.name = name
		
		if re.match('.*\sDemo\s*$', self.name, re.I) or re.match('.*\sDemo\s+.*$', self.name, re.I):
			self.isDemo = True
		else:
			self.isDemo = False
			
	def setKey(self, key):
		if not hasattr(self, 'key'):
			self.key = None
			
		key = key.upper()
		
		if len(key) != 32:
			return
			
		try:
			i = int(key, 16)
			
			if i <= 0:
				return
		except:
			return
			
		self.key = key
		
	def setVersion(self, version):
		if version:
			self.version = version
		
	def lastestVersion(self):
		if not self.version:
			self.version = Title.getVersions(self.id)[-1]
		return self.version
		
	@staticmethod
	def getVersions(id):
		if not hasCDNSP:
			return ['0']
		
		r = CDNSP.get_versions(id)
		
		if len(r) == 0 or r[0] == 'none':
			return ['0']

		return r
			
	@staticmethod
	def getBaseId(id):
		titleIdNum = int(id, 16)
		return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)

class Titles:
	def __init__(self):
		self.data = {}
	
	def __getitem__(self, key):
		return self.data[key]
		
	def __setitem__(self, key, value):
		self.data[key] = value
		
	def __iter__(self):
		self.it = 0
		return self
		
	def __next__(self):
		try:
			r = self.data[list(self.data)[self.it]]
		except IndexError:
			raise StopIteration()
		self.it += 1
		return r
		
	def keys(self):
		return self.data.keys()
		
	def load(self):
		if not os.path.isfile("titles.json"):
			return
			
		with open("titles.json", "r") as f:
			j = json.load(f)
			for id, t in j.items():
				self[id] = Title()
				
				if t['rightsId']:
					self[id].setId(t['rightsId'])
				else:
					self[id].setId(id)
					
				self[id].setName(t['name'])
				self[id].setKey(t['key'])
				self[id].setVersion(t['version'])
		
	def save(self):
		j = {}
		for t in self:
			if not t.id in j.keys():
				j[t.id] = {}
			
			j[t.id]['name'] = t.name
			
			j[t.id]['key'] = t.key
			
			j[t.id]['rightsId'] = t.rightsId
				
			j[t.id]['version'] = t.version
				
		with open("titles.json", "w+") as f:
			f.write(json.dumps(j))
	
	
titles = Titles()
titles.load()
	
class Nsp:
	def __init__(self, path):
		self.path = path
		self.version = '0'
		
		z = re.match('.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0].upper()
			
			if self.titleId:
				if self.titleId in titles.keys():
					titles[self.titleId].path = path
					self.title = titles[self.titleId]
		else:
			print('could not get title id from filename, name needs to contain [titleId] : ' + self.path)
			self.titleId = None

		z = re.match('.*\[v([0-9]+)\].*', path, re.I)
		if z:
			self.version = z.groups()[0]
					
	def move(self):
		if not self.fileName():
			#print('could not get filename for ' + self.path)
			return False
			
		if os.path.abspath(self.fileName()) == os.path.abspath(self.path):
			return False
			
		if os.path.isfile(self.fileName()) and os.path.abspath(self.path) == os.path.abspath(self.fileName()):
			print('duplicate title: ')
			print(os.path.abspath(self.path))
			print(os.path.abspath(self.fileName()))
			return False
			
		os.makedirs(os.path.dirname(self.fileName()), exist_ok=True)
		os.rename(self.path, self.fileName())
		#print(self.path + ' -> ' + self.fileName())
		
		if self.titleId in titles.keys():
			titles[self.titleId].path = self.fileName()
		return True
		
	def cleanFilename(self, s):
		s = re.sub('\s+\Demo\s*', ' ', s, re.I)
		s = re.sub('\s*\[DLC\]\s*', '', s, re.I)
		s = re.sub('[\/\\\:\*\?\"\<\>\|\.\s™©®()]+', ' ', s)
		return s.strip()
		
	def fileName(self):
		bt = None
		if not self.titleId in titles.keys():
			if not Title.getBaseId(self.titleId) in titles.keys():
				print('could not find title key for ' + self.titleId + ' or ' + Title.getBaseId(self.titleId))
				return None
			bt = titles[Title.getBaseId(self.titleId)]
			t = Title()
			t.loadCsv(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
		else:
			t = titles[self.titleId]
		
			if not t.baseId in titles.keys():
				print('could not find baseId for ' + self.path)
				return None
			bt = titles[t.baseId]
		
		if t.isDLC:
			format = config.titleDLCPath
		elif t.isDemo:
			if t.idExt != 0:
				format = config.titleDemoUpdatePath
			else:
				format = config.titleDemoPath
		elif t.idExt != 0:
			format = config.titleUpdatePath
		else:
			format = config.titleBasePath
			
		format = format.replace('{id}', self.cleanFilename(t.id))
		format = format.replace('{name}', self.cleanFilename(t.name))
		format = format.replace('{version}', str(self.version))
		format = format.replace('{baseId}', self.cleanFilename(bt.id))
		format = format.replace('{baseName}', self.cleanFilename(bt.name))
		return format
		
		
def scanForNsp(base):
	for root, dirs, files in os.walk(base, topdown=False):
		for name in dirs:
			scanForNsp(base + '/' + name)
			
		for name in files:
			if pathlib.Path(name).suffix == '.nsp':
				nsps.append(Nsp(root + '/' + name))

def removeEmptyDir(path, removeRoot=True):
	if not os.path.isdir(path):
		return

	# remove empty subfolders
	files = os.listdir(path)
	if len(files):
		for f in files:
			if not f.startswith('.'):
				fullpath = os.path.join(path, f)
				if os.path.isdir(fullpath):
					removeEmptyDir(fullpath)

	# if folder empty, delete it
	files = os.listdir(path)
	if len(files) == 0 and removeRoot:
		print("Removing empty folder:" + path)
		os.rmdir(path)

def loadTitles():
	with open('titlekeys.txt', encoding="utf8") as f:
		for line in f.readlines():
			t = Title()
			t.loadCsv(line)
			
			if not t.id in titles.keys():
				titles[t.id] = Title()
				
			titles[t.id].loadCsv(line)
				
def loadTitleWhitelist():
    global titleWhitelist
    titleWhitelist = []
    with open('whitelist.txt', encoding="utf8") as f:
        for line in f.readlines():
            titleWhitelist.append(line.strip().upper())
			
def loadTitleBlacklist():
    global titleBlacklist
    titleBlacklist = []
    with open('blacklist.txt', encoding="utf8") as f:
        for line in f.readlines():
            titleBlacklist.append(line.strip().upper())
			
def logMissingTitles():
	f = open("missing.txt","w+b")
	
	for t in titles:
		if not t.path:
			f.write((t.name + "\r\n").encode("utf-8"))
		
	f.close()

class Config:
	def __init__(self):
		with open('nut.json', encoding="utf8") as f:
			j = json.load(f)
			self.titleBasePath = j['paths']['titleBase']
			self.titleDLCPath = j['paths']['titleDLC']
			self.titleUpdatePath = j['paths']['titleUpdate']
			self.titleDemoPath = j['paths']['titleDemo']
			self.titleDemoUpdatePath = j['paths']['titleDemoUpdate']
			self.scanPath = j['paths']['scan']
			
			self.downloadBase = j['download']['base']
			self.downloadDemo = j['download']['demo']
			self.downloadDLC = j['download']['dlc']
			self.downloadUpdate = j['download']['update']
	

config = Config()
	

urllib3.disable_warnings()

if hasCDNSP:
	CDNSP.tqdmProgBar = False
	CDNSP.configPath = os.path.join(os.path.dirname(__file__), 'CDNSPconfig.json')
	CDNSP.hactoolPath, CDNSP.keysPath, CDNSP.NXclientPath, CDNSP.ShopNPath, CDNSP.reg, CDNSP.fw, CDNSP.did, CDNSP.env, CDNSP.dbURL, CDNSP.nspout, CDNSP.autoUpdatedb = CDNSP.load_config(CDNSP.configPath)

	if CDNSP.keysPath != '':
		CDNSP.keysArg = ' -k "%s"' % CDNSP.keysPath
	else:
		CDNSP.keysArg = ''

loadTitleWhitelist()
loadTitleBlacklist()
loadTitles()
scanForNsp(config.scanPath)

for f in nsps:
	f.move()
	
logMissingTitles()
removeEmptyDir('.', False)

#setup_download(listTid, get_versions(listTid)[-1], listTkey, True)
if hasCDNSP:
	for t in titles:
		if not t.path and (not t.isDLC or config.downloadDLC) and (not t.isDemo or config.downloadDemo) and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
			print('Downloading ' + t.name + ', ' + t.key.lower())
			CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key.lower(), True, '', True)

titles.save()
#for t in titles:
#	print(t.id + ': ' + t.name + ", " + str(t.path))
#print(Title.getVersions('010034500641b02c'))
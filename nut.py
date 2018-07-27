#!/usr/bin/python3
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
titles = {}
titleWhitelist = []
titleBlacklist = []

class Title:
	def __init__(self, line):
		split = line.split('|')
		self.id = split[0][:16]
		self.unknown = split[0][-16:]
		self.key = split[1]
		self.name = split[2].strip()
		
		titleIdNum = int(self.id, 16)
		
		if self.id:
			self.baseId = '{:02x}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		else:
			self.baseId = None
		
		self.isDLC = (titleIdNum & 0xFFFFFFFFFFFFE000) != (titleIdNum & 0xFFFFFFFFFFFFF000)
		#self.isBase = self.id == titleIdNum & 0xFFFFFFFFFFFFE000
		self.idExt = titleIdNum & 0x0000000000000FFF
		
		if self.isDLC:
			#dlc
			self.versions = Title.getVersions(self.id)
		elif self.idExt == 0:
			#base
			self.versions = Title.getVersions(self.id)
			self.updateId = '%s800' % self.id[:-3]
			self.updateVersions = Title.getVersions(self.updateId)
		else:
			#update
			self.versions = Title.getVersions(self.id)
		#self.versions = Title.getVersions(self.id)
		self.path = None
		
	def lastestVersion(self):
		return self.versions[-1]
		
	@staticmethod
	def getVersions(id):
		if not hasCDNSP:
			return ['0']
		
		cacheFile = '_cache/versions/' + id + '.json'
		
		if os.path.isfile(cacheFile):
			with open(cacheFile, "r") as f:
				r = json.loads(f.read())
		else:
			r = CDNSP.get_versions(id)
		
			os.makedirs(os.path.dirname(cacheFile), exist_ok=True)
			
			with open(cacheFile, "w+") as f:
				f.write(json.dumps(r))
		
		if len(r) == 0 or r[0] == 'none':
			return ['0']

		return r
			
	@staticmethod
	def getBaseId(id):
		titleIdNum = int(id, 16)
		return '{:02x}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		
class Nsp:
	def __init__(self, path):
		self.path = path
		self.version = '0'
		
		z = re.match('.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0]
			
			if self.titleId:
				if self.titleId in titles.keys():
					titles[self.titleId].path = path
					self.title = titles[self.titleId]
					
		z = re.match('.*\[v([0-9]+)\].*', path, re.I)
		if z:
			self.version = z.groups()[0]
					
	def move(self):
		if not self.fileName():
			#print('could not get filename for ' + self.path)
			return False
			
		if os.path.abspath(self.fileName()) == os.path.abspath(self.path):
			return False
			
		if os.path.isfile(self.fileName()):
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
		return re.sub('[\/\\\:\*\?\"\<\>\|\.\s]+', ' ', s).strip()
		
	def fileName(self):
		bt = None
		if not self.titleId in titles.keys():
			if not Title.getBaseId(self.titleId) in titles.keys():
				print('could not find title key for ' + self.titleId + ' or ' + Title.getBaseId(self.titleId))
				return None
			bt = titles[Title.getBaseId(self.titleId)]
			t = Title(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
		else:
			t = titles[self.titleId]
		
			if not t.baseId in titles.keys():
				print('could not find baseId for ' + self.path)
				return None
			bt = titles[t.baseId]
		
		if t.isDLC:
			format = config.titleDLCPath
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
            t = Title(line)
            titles[t.id] = t
				
def loadTitleWhitelist():
    global titleWhitelist
    titleWhitelist = []
    with open('whitelist.txt', encoding="utf8") as f:
        for line in f.readlines():
            titleWhitelist.append(line.strip())
			
def loadTitleBlacklist():
    global titleBlacklist
    titleBlacklist = []
    with open('blacklist.txt', encoding="utf8") as f:
        for line in f.readlines():
            titleBlacklist.append(line.strip())
			
def logMissingTitles():
	f = open("missing.txt","w+b")
	
	for id, t in titles.items():
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
			self.scanPath = j['paths']['scan']
			
			self.downloadBase = j['download']['base']
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
#scanNsp('_NSPOUT')
scanForNsp(config.scanPath)
for f in nsps:
	f.move()
	
logMissingTitles()
removeEmptyDir('.', False)

#setup_download(listTid, get_versions(listTid)[-1], listTkey, True)
if hasCDNSP:
	for id, t in titles.items():
		if not t.path and (not t.isDLC or config.downloadDLC)  and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
			print('Downloading ' + t.name + ', ' + t.key.lower())
			CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key.lower(), True, '', True)

#print(Title.getVersions('0100111004461002'))
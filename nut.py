#!/usr/bin/python3
# place this file in your CDNSP directory
# add the following line to the top of your CDNSP.py file:
# from tqdm import tqdm

import os
import re
import pathlib
import urllib3
import CDNSP

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
		self.version = titleIdNum & 0x0000000000000FFF
		self.path = None
		
	@staticmethod
	def getBaseId(id):
		titleIdNum = int(id, 16)
		return '{:02x}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		
class Nsp:
	def __init__(self, path):
		self.path = path
		
		z = re.match('.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0]
			
			if self.titleId:
				if self.titleId in titles.keys():
					titles[self.titleId].path = path
					self.title = titles[self.titleId]
					
	def move(self):
		if not self.fileName():
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
		#print(self.path)
		
		if self.titleId in titles.keys():
			titles[self.titleId].path = self.fileName()
		return True
		
	def fileName(self):
		bt = None
		if not self.titleId in titles.keys():
			if not Title.getBaseId(self.titleId) in titles.keys():
				return None
			bt = titles[Title.getBaseId(self.titleId)]
			t = Title(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
		else:
			t = titles[self.titleId]
		
			if not t.baseId in titles.keys():
				return None
			bt = titles[t.baseId]
		
		basePath = 'titles/' + re.sub('[\/\\\:\*\?\"\<\>\|\.]+', ' ', bt.name).strip() + '/'
		
		if t.isDLC:
			basePath += 'DLC/'
		elif t.version != 0:
			basePath += 'updates/'
		
		return basePath + re.sub('[\/\\\:\*\?\"\<\>\|\.]+', ' ', t.name).strip() + '[' + t.id + '].nsp'
		
		
def scanForNsp(base):
	for root, dirs, files in os.walk(base, topdown=False):
		for name in dirs:
			scanForNsp(base + '/' + name)
			
		for name in files:
			if pathlib.Path(name).suffix == '.nsp':
				nsps.append(Nsp(root + '/' + name))


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

urllib3.disable_warnings()
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
scanForNsp('.')
for f in nsps:
	f.move()
	
logMissingTitles()

#setup_download(listTid, get_versions(listTid)[-1], listTkey, True)

for id, t in titles.items():
	if not t.path and not t.isDLC and t.version == 0 and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
		print('Downloading ' + t.name + ', ' + t.key.lower())
		CDNSP.download_game(t.id.lower(), 0, t.key.lower(), True, '', True)

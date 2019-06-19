#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import json
from nut import Titles
from nut import Print

from bs4 import BeautifulSoup
import requests
import time
import datetime
import calendar
import threading
from nut import Nsps
import urllib.request
from nut import Config

try:
	from PIL import Image
except ImportError:
	import Image

global grabUrlInit
global urlCache
global urlLock
global fileLUT

fileLUT = {}

grabUrlInit = False
urlCache = {}
urlLock = threading.Lock()	

if os.path.isfile('titledb/redirectCache.json'):
	with open('titledb/redirectCache.json', encoding="utf-8-sig") as f:
		urlCache = json.loads(f.read())

def grabCachedRedirectUrl(url, cookies = None):
	global grabUrlInit
	global urlCache
	global urlLock

	try:
		if url in urlCache:
			if not urlCache[url]:
				return None
			result = requests.get(urlCache[url], cookies=cookies)
			#result.url = urlCache[url]
			return result

		urlLock.acquire()
		# we need to slow this down so we dont get banned
		#Print.info('hitting ' + url)
		#time.sleep(0.1)
		result = requests.get(url, cookies=cookies)
		if result.status_code == 404:
			urlCache[url] = None
		elif result.status_code == 200:
			urlCache[url] = result.url
		else:
			#not sure but dont cache it
			return result

		with open('titledb/redirectCache.json', 'w') as outfile:
			json.dump(urlCache, outfile)
		urlLock.release()
		return result
	except:
		urlLock.release()
		raise

def getBaseId(id):
	if not id:
		return None
	titleIdNum = int(id, 16)
	return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)

class Title:
	def __init__(self):
		self.id = None
		self.rightsId = None
		self.name = None
		self.isDLC = False
		self.isUpdate = False
		self.idExt = None
		self.updateId = None
		self.version = None
		self.key = None
		self.isDemo = None
		self.region = None
		self.regions = None

		self.baseId = None
		self.releaseDate = None
		self.nsuId = None
		self.category = None
		self.ratingContent = None
		self.numberOfPlayers = None
		self.rating = None
		self.developer = None
		self.publisher = None
		self.frontBoxArt = None
		self.iconUrl = None
		self.screenshots = None
		self.bannerUrl = None
		self.intro = None
		self.description = None
		self.languages = None
		self.size = 0
	
	def __lt__(self, other):
		if not self.name:
			return True
		if not other.name:
			return False
		return str(self.name) < str(other.name)

	def exportDict(self, isRegion = False):
		r = {}

		if isRegion:
			blacklist = ('isDLC', 'isUpdate', 'idExt', 'updateId', 'baseId', 'regions')
		else:
			blacklist = ('isDLC', 'isUpdate', 'idExt', 'updateId', 'baseId')

		for i in self.__dict__.keys():
			if i not in blacklist:
				r[i] = self.__dict__[i]
		return r
		
	def loadCsv(self, line, map = ['id', 'key', 'name']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				Print.info('invalid map index: ' + str(i) + ', ' + str(len(map)))
				continue
			
			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())
			
		#self.setId(split[0].strip())
		#self.setName(split[2].strip())
		#self.setKey(split[1].strip())

	def dict(self, map = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']):
		r = {}
		for i in map:	
			methodName = 'get' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda: methodName)
			r[i] = method()
		return r

	def importFrom(self, regionTitle, region, language):
		if not regionTitle.name or not regionTitle.id:
			return
		for k,v in regionTitle.__dict__.items():
			if k in ('id', 'version', 'regions', 'key'):
				continue
			setattr(self, k, v)
			self.setId(self.id)
			self.setVersion(regionTitle.version)
			self.region = region
			self.language = language
		
	def serialize(self, map = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']):
		r = []
		for i in map:
				
			methodName = 'get' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda: methodName)
			r.append(str(method()))
		return '|'.join(r)

	def getFiles(self):
		if self.id in fileLUT:
			return fileLUT[self.id]

		fileLUT[self.id] = []
		for path, f in Nsps.files.items():
			if(f.titleId == self.id):
				fileLUT[self.id].append(f)

		return fileLUT[self.id]

	def getLatestFile(self):
		highest = None

		for nsp in self.getFiles():
			try:
				if not highest or int(nsp.version) > int(highest.version):
					highest = nsp
			except:
				pass

		return highest

	def isUpdateAvailable(self, localOnly = False):
		nsp = self.getLatestFile()
		if not nsp:
			return True

		try:
			latest = self.lastestVersion(localOnly = localOnly)
			if latest is None:
				return False
			if int(nsp.version) < int(latest):
				return True
		except BaseException as e:
			Print.error('isUpdateAvailable exception %s: %s' % (self.id, str(e)))
			pass

		return False

	def getIsDLC(self):
		return self.isDLC*1

	def setIsDLC(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isDLC = True
			elif v == 0:
				self.isDLC = False
		except:
			pass
		
	def getIsUpdate(self):
		return self.isUpdate*1

	def setIsUpdate(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isUpdate = True
			elif v == 0:
				self.isUpdate = False
		except:
			pass
		
	def getIsDemo(self):
		try:
			return self.isDemo*1
		except:
			return 0

	def setIsDemo(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isDemo = True
			elif v == 0:
				self.isDemo = False
		except:
			pass

	def setNsuId(self, nsuId):
		if nsuId:
			self.nsuId = int(nsuId)
			if nsuId:
				self.isDemo = str(nsuId)[0:4] == '7003'

	def setRightsId(self, rightsId):
		if not id:
			self.setId(rightsId)
			
		if rightsId and len(rightsId) == 32 and rightsId != '00000000000000000000000000000000':
			self.rightsId = rightsId.upper()
			
	def getRightsId(self):
		return self.rightsId or '00000000000000000000000000000000'

	def isBase(self):
		if self.baseId == self.id:
			return True
		else:
			return False
			
	def setId(self, id):
		self.isUpdate = False
		self.baseId = None
		if not id:
			return
			
		id = id.upper();
		
		try:
			i = int(id, 16)
		except:
			return
		
		if len(id) == 32:
			self.id = id[:16]
			self.setRightsId(id)
		elif len(id) == 16:
			self.id = id[:16]
		else:
			return
		
		titleIdNum = int(self.id, 16)
		
		if self.id:
			self.baseId = '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		
		self.isDLC = (titleIdNum & 0xFFFFFFFFFFFFE000) != (titleIdNum & 0xFFFFFFFFFFFFF000)
		#self.isBase = self.id == titleIdNum & 0xFFFFFFFFFFFFE000
		self.idExt = titleIdNum & 0x0000000000000FFF
		
		if self.isDLC:
			# dlc
			self.isUpdate = False
		elif self.idExt == 0:
			# base
			self.updateId = '%s800' % self.id[:-3]
		else:
			# update
			self.isUpdate = True
			pass

	@staticmethod
	def baseDlcId(id):
		titleIdNum = int(id, 16)
		
		return (titleIdNum & 0xFFFFFFFFFFFFE000) + 0x1000
		#return hex(dlcId)
			
	def getId(self):
		return self.id or '0000000000000000'

	def getBaseId(self):
		return self.baseId or '0000000000000000'

	def setRegion(self, region):
		if not self.region and re.match('[A-Z]{2}', region):
			self.region = region
		
	def getRegion(self):
		return self.region or ''
			
	def setName(self, name):
		if not name or self.name:
			return
		self.name = name
		
		if self.isDemo == None:
			if re.match('.*\s[\(\[]?Demo[\)\]]?\s*$', self.name, re.I) or re.match('.*\s[\(\[]?Demo[\)\]]?\s+.*$', self.name, re.I):
				self.isDemo = True
			else:
				self.isDemo = False

	def setNameOverride(self, name):
		if not name:
			return
		self.name = name
		
		if self.isDemo == None:
			if re.match('.*\s[\(\[]?Demo[\)\]]?\s*$', self.name, re.I) or re.match('.*\s[\(\[]?Demo[\)\]]?\s+.*$', self.name, re.I):
				self.isDemo = True
			else:
				self.isDemo = False
	
	def getName(self):
		baseId = getBaseId(self.id)
		if hasattr(self, 'isUpdate') and self.isUpdate and Titles.contains(baseId):
			return (Titles.get(baseId).name or '').replace('\n', ' ')
		elif hasattr(self, 'isDLC') and self.isDLC and Titles.contains(baseId):
			if (self.name or '').find(Titles.get(baseId).name) > -1:
				return 'DLC: ' + (self.name or '').replace('\n', ' ')
			else:
				return (((Titles.get(baseId).name or '') + ' DLC: ' + (self.name or '')) or '').replace('\n', ' ')
		return (self.name or '').replace('\n', ' ')

	def getBaseName(self):
		baseId = getBaseId(self.id)
		if Titles.contains(baseId):
			return (Titles.get(baseId).name or '').replace('\n', ' ')
		return ''
			
	def setKey(self, key):
		if not key:
			return
			
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
		
	def getKey(self):
		return self.key or '00000000000000000000000000000000'
		
	def setVersion(self, version, force = False):
		if version != None:
			try:
				n = int(str(version), 10)
			except:
				return
				
			try:
				o = int(str(self.version), 10)
			except:
				o = None
				
			if not o or n > o or force:
				self.version = n
			
	def getVersion(self):
		if self.version is None:
			return ''
		return self.version
		
	def lastestVersion(self, force = False, localOnly = False):
		try:
			if not self.id:
				return None			
	
			return self.version
		except BaseException as e:
			Print.error(str(e))
			return None
		
	def isValid(self):
		if self.id:
			return True
		else:
			return False

	def isActive(self):
		if (self.isDLC or self.isUpdate or Config.download.base) and (not self.isDLC or Config.download.DLC) and (not self.isDemo or Config.download.demo) and (not self.isUpdate or Config.download.update) and (self.key or Config.download.sansTitleKey) and (len(Config.titleWhitelist) == 0 or self.id in Config.titleWhitelist) and self.id not in Config.titleBlacklist:
			return True
		else:
			return False

	def download(self, base, fileName, url):
		path = os.path.join(base, fileName)
		if os.path.isfile(path):
			return path
		os.makedirs(base, exist_ok=True)
		urllib.request.urlretrieve(url, path)
		return path

	def getResizedImage(self, filePath, width = None, height = None):
		if not width and not height:
			return filePath

		base, name = os.path.split(filePath)
		path = os.path.join(base, '.' + str(width) + 'x' + str(height) + '_' + name)

		if not os.path.isfile(path):
			os.makedirs(base, exist_ok=True)
			im = Image.open(filePath)
			ar = im.size[0] / im.size[1]
			if height == None:
				height = int(width / ar)
			elif width == None:
				width = int(height * ar)

			out = im.resize((width, height), Image.ANTIALIAS)
			out.save(path, quality=100)

		return path

	def bannerFile(self, width = None, height = None):
		if not self.bannerUrl or self.bannerUrl.startswith('cocoon:/'):
			return None

		baseName, ext = os.path.splitext(self.bannerUrl)
		return self.getResizedImage(self.download(Config.paths.titleImages + self.id, 'banner' + ext, self.bannerUrl), width, height)

	def frontBoxArtFile(self, width = None, height = None):
		if not self.frontBoxArt or self.frontBoxArt.startswith('cocoon:/'):
			return None

		baseName, ext = os.path.splitext(self.frontBoxArt)
		return self.getResizedImage(self.download(Config.paths.titleImages + self.id, 'frontBoxArt' + ext, self.frontBoxArt), width, height)

	def iconFile(self, width = None, height = None):
		if not 'iconUrl' in self.__dict__:
			self.iconUrl = None

		if not self.iconUrl or self.iconUrl.startswith('cocoon:/'):
			return None

		baseName, ext = os.path.splitext(self.iconUrl)
		return self.getResizedImage(self.download(Config.paths.titleImages + self.id, 'icon' + ext, self.iconUrl), width, height)

	def screenshotFile(self, i, width = None, height = None):
		if not self.screenshots[i] or self.screenshots[i].startswith('cocoon:/'):
			return None

		baseName, ext = os.path.splitext(self.screenshots[i])
		return self.getResizedImage(self.download(Config.paths.titleImages + self.id, 'screenshot' + str(i) + ext, self.screenshots[i]), width, height)

	def screenshotFiles(self):
		if not self.screenshots:
			return []
		r = []
		for i,u in enumerate(self.screenshots):
			r.append(self.screenshotFile(i))
		return r


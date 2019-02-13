#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import platform

class Server:
	def __init__(self):
		self.hostname = '0.0.0.0'
		self.port = 9000

class Cdn:
	def __init__(self):
		self.region = 'US'
		self.firmware = '7.0.0-5.0'
		self.deviceId = '0000000000000000'
		self.environment = 'lp1'
		
class Paths:
	def __init__(self):
		self.titleBase = "titles/{name}[{id}][v{version}].nsp"
		self.titleDLC = "titles/DLC/{name}[{id}][v{version}].nsp"
		self.titleUpdate = "titles/updates/{name}[{id}][v{version}].nsp"
		self.titleDemo = "titles/demos/{name}[{id}][v{version}].nsp"
		self.titleDemoUpdate = "titles/demos/updates/{name}[{id}][v{version}].nsp"

		self.nsxTitleBase = None
		self.nsxTitleDLC = None
		self.nsxTitleUpdate = None
		self.nsxTitleDemo = None
		self.nsxTitleDemoUpdate = None

		self.scan = '.'
		self.titleDatabase = 'titledb'
		self.hactool = 'bin/hactool'
		self.keys = 'keys.txt'
		self.NXclientCert = 'nx_tls_client_cert.pem'
		self.shopNCert = 'ShopN.pem'
		self.nspOut = '_NSPOUT'
		self.titleImages = 'titles/images/'

		self.duplicates = 'duplicates/'
		
		if platform.system() == 'Linux':
			self.hactool = './' + self.hactool + '_linux'

		if platform.system() == 'Darwin':
			self.hactool = './' + self.hactool + '_mac'
			
		self.hactool = os.path.normpath(self.hactool)

	def getTitleBase(self, nsx):
		if nsx:
			f = self.nsxTitleBase or self.titleBase
			f = os.path.splitext(f)[0] + '.nsx'
		else:
			f = self.titleBase
		return f

	def getTitleDLC(self, nsx):
		if nsx:
			f = self.nsxTitleDLC or self.titleDLC
			f = os.path.splitext(f)[0] + '.nsx'
		else:
			f = self.titleDLC
		return f

	def getTitleUpdate(self, nsx):
		if nsx:
			f = self.nsxTitleUpdate or self.titleUpdate
			f = os.path.splitext(f)[0] + '.nsx'
		else:
			f = self.titleUpdate
		return f

	def getTitleDemo(self, nsx):
		if nsx:
			f = self.nsxTitleDemo or self.titleDemo
			f = os.path.splitext(f)[0] + '.nsx'
		else:
			f = self.titleDemo
		return f

	def getTitleDemoUpdate(self, nsx):
		if nsx:
			f = self.nsxTitleDemoUpdate or self.titleDemoUpdate
			f = os.path.splitext(f)[0] + '.nsx'
		else:
			f = self.titleDemoUpdate
		return f
		
class Download:
	def __init(self):
		self.downloadBase = True
		self.demo = False
		self.DLC = True
		self.update = False
		self.sansTitleKey = False

class EdgeToken:
	def __init__(self):
		self.token = None
		self.expires = None

class DAuthToken:
	def __init__(self):
		self.token = None
		self.expires = None

edgeToken = EdgeToken()
dauthToken = DAuthToken()
cdn = Cdn()
paths = Paths()
download = Download()
server = Server()
threads = 4
jsonOutput = False
isRunning = True

titleBlacklist = []
titleWhitelist = []

region = 'US'
language = 'en'

titleUrls = []

def load(confFile):
	global threads
	global jsonOutput
	global titleUrls
	global region
	global language

	with open(confFile, encoding="utf8") as f:
		j = json.load(f)

		try:
			region = j['region']
		except:
			pass

		try:
			language = j['language']
		except:
			pass

		try:
			paths.titleImages = j['paths']['titleImages']
		except:
			pass
	
		try:
			paths.titleBase = j['paths']['titleBase']
		except:
			pass
		
		try:
			paths.titleDLC = j['paths']['titleDLC']
		except:
			pass
		
		try:
			paths.titleUpdate = j['paths']['titleUpdate']
		except:
			pass
		
		try:
			paths.titleDemo = j['paths']['titleDemo']
		except:
			pass
		
		try:
			paths.titleDemoUpdate = j['paths']['titleDemoUpdate']
		except: 
			pass

		try:
			paths.duplicates = j['paths']['duplicates']
		except: 
			pass


		try:
			paths.nsxTitleBase = j['paths']['nsxTitleBase']
		except:
			pass
		
		try:
			paths.nsxTitleDLC = j['paths']['nsxTitleDLC']
		except:
			pass
		
		try:
			paths.nsxTitleUpdate = j['paths']['nsxTitleUpdate']
		except:
			pass
		
		try:
			paths.nsxTitleDemo = j['paths']['nsxTitleDemo']
		except:
			pass
		
		try:
			paths.nsxTitleDemoUpdate = j['paths']['nsxTitleDemoUpdate']
		except: 
			pass


	
		try:
			paths.scan = j['paths']['scan']
		except:
			pass

		try:
			paths.nspOut = j['paths']['nspOut']
		except:
			pass
		
		try:
			paths.titleDatabase = ['paths']['titledb']
		except:
			pass
	
		try:
			download.base = j['download']['base']
		except:
			pass
		
		try:
			download.demo = j['download']['demo']
		except:
			pass
		
		try:
			download.DLC = j['download']['dlc']
		except:
			pass
		
		try:
			download.update = j['download']['update']
		except:
			pass

		try:
			cdn.deviceId = j['cdn']['deviceId']
		except:
			pass

		try:
			cdn.region = j['cdn']['region']
		except:
			pass

		try:
			cdn.environment = j['cdn']['environment']
		except:
			pass

		'''
		try:
			cdn.firmware = j['cdn']['firmware']
		except:
			pass
		'''

		try:
			threads = int(j['download']['threads'])
		except:
			pass

		try:
			server.hostname = j['server']['hostname']
		except:
			pass

		try:
			server.port = int(j['server']['port'])
		except:
			pass
	
		try:
			for url in j['titleUrls']:
				if url not in titleUrls:
					titleUrls.append(url)
		except:
			pass
	
		try:
			download.sansTitleKey = j['download']['sansTitleKey']
		except:
			pass

if os.path.isfile('nut.conf'):
	os.rename('nut.conf', 'conf/nut.conf')


if os.path.isfile('conf/nut.default.conf'):
	load('conf/nut.default.conf')

if os.path.isfile('conf/nut.conf'):
	load('conf/nut.conf')

if os.path.isfile('edge.token'):
	with open('edge.token', encoding="utf8") as f:
		edgeToken.token = f.read().strip()


if os.path.isfile('dauth.token'):
	with open('dauth.token', encoding="utf8") as f:
		dauthToken.token = f.read().strip()



g_regionLanguages = None

def regionLanguages(fileName = 'titledb/languages.json'):
	global g_regionLanguages

	if g_regionLanguages:
		return g_regionLanguages

	g_regionLanguages = []

	try:
		with open(fileName, encoding="utf-8-sig") as f:
				g_regionLanguages = json.loads(f.read())
	except:
		g_regionLanguages = json.loads('{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"],"PE":["en","es"],"KR":["ko"],"HK":["zh"],"NZ":["en"],"AT":["de"],"BE":["fr","nl"],"CZ":["en"],"DK":["en"],"ES":["es"],"FI":["en"],"GR":["en"],"HU":["en"],"NL":["nl"],"NO":["en"],"PL":["en"],"PT":["pt"],"RU":["ru"],"ZA":["en"],"SE":["en"],"MX":["en","es"],"IT":["it"],"CA":["en","fr"],"FR":["fr"],"DE":["de"],"JP":["ja"],"AU":["en"],"GB":["en"],"US":["en","es"]}')

	return g_regionLanguages

def loadTitleWhitelist():
	global titleWhitelist
	titleWhitelist = []
	try:
		with open('conf/whitelist.txt', encoding="utf8") as f:
			for line in f.readlines():
				titleWhitelist.append(line.strip().upper())
	except:
		pass
			
def loadTitleBlacklist():
	global titleBlacklist
	titleBlacklist = []
	try:
		with open('conf/blacklist.txt', encoding="utf8") as f:
			for line in f.readlines():
				id = line.split('|')[0].strip().upper()
				if id:
					titleBlacklist.append(id)

		with open('conf/retailOnly.blacklist', encoding="utf8") as f:
			for line in f.readlines():
				id = line.split('|')[0].strip().upper()
				if id:
					titleBlacklist.append(id)
	except:
		pass

loadTitleWhitelist()
loadTitleBlacklist()
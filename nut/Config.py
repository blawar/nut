#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import platform
import nut.Print
import time
from binascii import hexlify as hx, unhexlify as uhx

threads = 1
jsonOutput = False
isRunning = True
dryRun = False
shardCount = None
shardIndex = None
reverse = False
isScanning = False
autoUpdateTitleDb = True

region = None

autolaunchBrowser = True

titleBlacklist = []
titleWhitelist = []

region = 'US'
language = 'en'

titleUrls = []
pullUrls = []

g_regionLanguages = None

def getGdriveCredentialsFile():
	files = ['credentials.json', 'conf/credentials.json']

	for file in files:
		if os.path.exists(file):
			return file

	return None

class Server:
	def __init__(self):
		self.hostname = '0.0.0.0'
		self.port = 9000

class Compression:
	def __init__(self):
		self.level = 19
		self.auto = False

class Paths:
	def __init__(self):
		self.titleBase = 'titles/{name}[{id}][v{version}].nsp'
		self.titleDLC = 'titles/DLC/{name}[{id}][v{version}].nsp'
		self.titleUpdate = 'titles/updates/{name}[{id}][v{version}].nsp'
		self.titleDemo = 'titles/demos/{name}[{id}][v{version}].nsp'
		self.titleDemoUpdate = 'titles/demos/updates/{name}[{id}][v{version}].nsp'

		self.nsxTitleBase = None
		self.nsxTitleDLC = None
		self.nsxTitleUpdate = None
		self.nsxTitleDemo = None
		self.nsxTitleDemoUpdate = None

		self.nszTitleBase = None
		self.nszTitleDLC = None
		self.nszTitleUpdate = None
		self.nszTitleDemo = None
		self.nszTitleDemoUpdate = None

		self.xciTitleBase = None
		self.xciTitleDLC = None
		self.xciTitleUpdate = None
		self.xciTitleDemo = None
		self.xciTitleDemoUpdate = None


		self.scan = ['.']
		self.titleDatabase = 'titledb'
		self.hactool = 'bin/hactool'
		self.keys = 'keys.txt'
		self.calibration = 'PRODINFO.bin'
		self.shopNCert = 'ShopN.pem'
		self.nspOut = '_NSPOUT'
		self.titleImages = 'titles/images/'

		self.duplicates = 'duplicates/'

		if platform.system() == 'Linux':
			self.hactool = './' + self.hactool + '_linux'

		if platform.system() == 'Darwin':
			self.hactool = './' + self.hactool + '_mac'

		self.hactool = os.path.normpath(self.hactool)

	def mapping(self):
		m = {}

		if getGdriveCredentialsFile() is not None:
			m['gdrive'] = ''

		unknown = 0
		for f in self.scan:
			bits = f.split('#', 2)
			if len(bits) == 1:
				label = os.path.basename(f)
			else:
				label = bits[1]

			if not label or not len(label) or label == '':
				label = 'L' + str(unknown)
				unknown += 1
			m[label] = bits[0]
		return m

	def getTitleBase(self, nsx, name):
		if not name:
			return None

		if nsx and (name.endswith('.nsp') or name.endswith('.nsx')):
			f = self.nsxTitleBase or self.titleBase
			return os.path.splitext(f)[0] + '.nsx'

		ext = name[-4:]
		f = None

		if ext == '.nsp':
			f = self.titleBase
		elif ext == '.nsz':
			f = getPath(self.nszTitleBase, name, self.titleBase)
		elif ext == '.nsx' and nsx:
			f = getPath(self.nsxTitleBase, name, self.titleBase)
		elif ext == '.xci':
			f = getPath(self.xciTitleBase, name, self.titleBase)

		if not f:
			f = self.titleBase
		return f

	def getTitleDLC(self, nsx, name):
		if not name:
			return None

		if nsx and (name.endswith('.nsp') or name.endswith('.nsx')):
			f = self.nsxTitleDLC or self.titleDLC
			return os.path.splitext(f)[0] + '.nsx'

		ext = name[-4:]
		f = None

		if ext == '.nsp':
			f = self.titleDLC
		elif ext == '.nsz':
			f = getPath(self.nszTitleDLC, name, self.titleDLC)
		elif ext == '.nsx' and nsx:
			f = getPath(self.nsxTitleDLC, name, self.titleDLC)
		elif ext == '.xci':
			f = getPath(self.xciTitleDLC, name, self.titleDLC)

		if not f:
			f = self.titleDLC
		return f

	def getTitleUpdate(self, nsx, name):
		if not name:
			return None

		if nsx and (name.endswith('.nsp') or name.endswith('.nsx')):
			f = self.nsxTitleUpdate or self.titleUpdate
			return forceExt(f, '.nsx')

		ext = name[-4:]
		f = None

		if ext == '.nsp':
			f = self.titleUpdate
		elif ext == '.nsz':
			f = getPath(self.nszTitleUpdate, name, self.titleUpdate)
		elif ext == '.nsx' and nsx:
			f = getPath(self.nsxTitleUpdate, name, self.titleUpdate)
		elif ext == '.xci':
			f = getPath(self.xciTitleUpdate, name, self.titleUpdate)

		if not f:
			f = self.titleUpdate
		return forceExt(f, ext)

	def getTitleDemo(self, nsx, name):
		if not name:
			return None

		if nsx and (name.endswith('.nsp') or name.endswith('.nsx')):
			f = self.nsxTitleDemo or self.titleDemo
			return os.path.splitext(f)[0] + '.nsx'

		ext = name[-4:]
		f = None

		if ext == '.nsp':
			f = self.titleDemo
		elif ext == '.nsz':
			f = getPath(self.nszTitleDemo, name, self.titleDemo)
		elif ext == '.nsx' and nsx:
			f = getPath(self.nsxTitleDemo, name, self.titleDemo)
		elif ext == '.xci':
			f = getPath(self.xciTitleDemo, name, self.titleDemo)

		if not f:
			f = self.titleDemo
		return f

	def getTitleDemoUpdate(self, nsx, name):
		if not name:
			return None

		if nsx and (name.endswith('.nsp') or name.endswith('.nsx')):
			f = self.nsxTitleDemoUpdate or self.titleDemoUpdate
			return os.path.splitext(f)[0] + '.nsx'

		ext = name[-4:]
		f = None

		if ext == '.nsp':
			f = self.titleDemoUpdate
		elif ext == '.nsz':
			f = getPath(self.nszTitleDemoUpdate, name, self.titleDemoUpdate)
		elif ext == '.nsx' and nsx:
			f = getPath(self.nsxTitleDemoUpdate, name, self.titleDemoUpdate)
		elif ext == '.xci':
			f = getPath(self.xciTitleDemoUpdate, name, self.titleDemoUpdate)

		return f

def getPath(path, name, default):
	if not path:
		path = os.path.splitext(default)[0] + name[-4:]
		base = os.path.basename(path)
		path = os.path.join(os.path.dirname(path), name[-3:])
		path = os.path.join(path, base)
	return path

def forceExt(path, ext):
	return os.path.splitext(path)[0] + ext

def set(j, paths, value):
	last = paths.pop()
	for path in paths:
		if not path in j:
			j[path] = {}
		j = j[path]
	j[last] = value

def save(confFile = 'conf/nut.conf'):
	os.makedirs(os.path.dirname(confFile), exist_ok = True)
	j = {}
	try:
		with open(confFile, encoding='utf8') as f:
			j = json.load(f)
	except:
		pass

	set(j, ['paths'], paths.__dict__)
	set(j, ['compression'], compression.__dict__)
	set(j, ['pullUrls'], pullUrls)
	set(j, ['threads'], threads)
	set(j, ['download'], download.__dict__)
	set(j, ['server', 'hostname'], server.hostname)
	set(j, ['server', 'port'], server.port)

	set(j, ['autolaunchBrowser'], autolaunchBrowser)
	set(j, ['autoUpdateTitleDb'], autoUpdateTitleDb)

	with open(confFile, 'w', encoding='utf-8') as f:
		json.dump(j, f, indent=4)

def load(confFile):
	global threads
	global jsonOutput
	global titleUrls
	global pullUrls
	global region
	global language
	global compression
	global autolaunchBrowser

	with open(confFile, encoding='utf8') as f:
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
			autolaunchBrowser = j['autolaunchBrowser']
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
			paths.nszTitleBase = j['paths']['nszTitleBase']
		except:
			pass

		try:
			paths.nszTitleDLC = j['paths']['nszTitleDLC']
		except:
			pass

		try:
			paths.nszTitleUpdate = j['paths']['nszTitleUpdate']
		except:
			pass

		try:
			paths.nszTitleDemo = j['paths']['nszTitleDemo']
		except:
			pass

		try:
			paths.nszTitleDemoUpdate = j['paths']['nszTitleDemoUpdate']
		except:
			pass

		try:
			paths.xciTitleBase = j['paths']['xciTitleBase']
		except:
			pass

		try:
			paths.xciTitleDLC = j['paths']['xciTitleDLC']
		except:
			pass

		try:
			paths.xciTitleUpdate = j['paths']['xciTitleUpdate']
		except:
			pass

		try:
			paths.xciTitleDemo = j['paths']['xciTitleDemo']
		except:
			pass

		try:
			paths.xciTitleDemoUpdate = j['paths']['xciTitleDemoUpdate']
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
			paths.titleDatabase = j['paths']['titledb']
		except:
			pass


		try:
			compression.level = int(j['compression']['level'])
		except:
			pass

		try:
			compression.auto = True if int(j['compression']['auto']) != 0 else False
		except:
			pass

		try:
			download.rankMin = j['download']['rankMin']
		except:
			pass

		try:
			download.rankMax = j['download']['rankMax']
		except:
			pass

		try:
			download.ratingMin = j['download']['ratingMin']
		except:
			pass

		try:
			download.ratingMax = j['download']['ratingMax']
		except:
			pass

		try:
			download.fileSizeMin = j['download']['fileSizeMin']
		except:
			pass

		try:
			download.fileSizeMax = j['download']['fileSizeMax']
		except:
			pass

		try:
			download.releaseDateMin = j['download']['releaseDateMin']
		except:
			pass

		try:
			download.releaseDateMax = j['download']['releaseDateMax']
		except:
			pass

		try:
			download.base = j['download']['base']
		except:
			pass

		try:
			download.regions = j['download']['regions']
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
			download.deltas = j['download']['deltas']
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

		try:
			cdn.firmware = j['cdn']['firmware']
		except:
			pass

		try:
			cdn.clientIds = j['cdn']['clientIds']
		except:
			pass

		try:
			dauth.keyGeneration = j['cdn']['dAuth']['keyGeneration']
			dauth.challenge = 'key_generation=' + str(dauth.keyGeneration)
		except:
			pass

		try:
			dauth.userAgent = j['cdn']['dAuth']['userAgent']
		except:
			pass

		try:
			dauth.sysDigest = j['cdn']['dAuth']['sysDigest']
		except:
			pass

		try:
			threads = int(j['threads'])
		except:
			pass

		try:
			download.sansTitleKey = j['download']['sansTitleKey']
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
			autoUpdateTitleDb = j['autoUpdateTitleDb']
		except:
			pass

		try:
			for url in j['titleUrls']:
				if url not in titleUrls:
					titleUrls.append(url)
		except:
			pass

		try:
			for url in j['pullUrls']:
				if url not in pullUrls:
					pullUrls.append(url)
		except:
			pass


def update_main_path(newPath, nsp_files):
    """Function updateMainPath is intended to update a new main path (first element
    with 0 index in the config file).
    NSPs will be cleared (in memory) if path has been changed.
    Args:
        newPath (string): a new main path (first element with 0 index in the config file)
    Returns:
        None
    """
    global paths

    pathChanged = False
    oldPath = paths.scan[0]

    if newPath != oldPath:
        pathChanged = True

    if not pathChanged:
        return

    paths.scan[0] = newPath
    save()

    if pathChanged:
        nsp_files.clear()


def regionLanguages(fileName = 'titledb/languages.json'):
	global g_regionLanguages

	if g_regionLanguages:
		return g_regionLanguages

	g_regionLanguages = []

	try:
		with open(fileName, encoding='utf-8-sig') as f:
				g_regionLanguages = json.loads(f.read())
	except:
		g_regionLanguages = json.loads('{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"],"PE":["en","es"],"KR":["ko"],"HK":["zh"],"CN":["zh"],"NZ":["en"],"AT":["de"],"BE":["fr","nl"],"CZ":["en"],"DK":["en"],"ES":["es"],"FI":["en"],"GR":["en"],"HU":["en"],"NL":["nl"],"NO":["en"],"PL":["en"],"PT":["pt"],"RU":["ru"],"ZA":["en"],"SE":["en"],"MX":["en","es"],"IT":["it"],"CA":["en","fr"],"FR":["fr"],"DE":["de"],"JP":["ja"],"AU":["en"],"GB":["en"],"US":["es", "en"]}')

	return g_regionLanguages

def loadTitleWhitelist():
	global titleWhitelist
	titleWhitelist = []
	try:
		with open('conf/whitelist.txt', encoding='utf8') as f:
			for line in f.readlines():
				titleWhitelist.append(line.strip().upper())
	except:
		pass

def loadTitleBlacklist():
	global titleBlacklist
	titleBlacklist = []

	confDir = 'conf'

	try:
		files = os.listdir(confDir)
	except FileNotFoundError:
		return

	for file in files:
		path = os.path.abspath(os.path.join(confDir, file))

		if 'blacklist' not in path:
			continue

		print('loading blacklist %s' % path)

		try:
			with open(path, encoding='utf8') as f:
				for line in f.readlines():
					id = line.split('|')[0].strip().upper()
					if id:
						titleBlacklist.append(id)
		except:
			pass

compression = Compression()
paths = Paths()
server = Server()

class Download:
	def __init__(self):
		self.downloadBase = True
		self.demo = False
		self.DLC = True
		self.update = False
		self.sansTitleKey = False
		self.deltas = False
		self.regions = []
		self.rankMin = None
		self.rankMax = None
		self.fileSizeMax = None
		self.fileSizeMin = None
		self.ratingMin = None
		self.ratingMax = None
		self.releaseDateMin = None
		self.releaseDateMax = None

	def addRegion(self, region):
		region = region.upper()
		if region not in self.regions:
			self.regions.append(region)

	def removeRegion(self, region):
		region = region.upper()
		if region not in self.regions:
			return

		self.regions.remove(region)

	def hasRegion(self, regions, default = True):
		if not self.regions or len(self.regions) == 0 or regions is None:
			return default

		for a in self.regions:
			for b in regions:
				if a == b:
					return True

		return False


class DAuthToken:
	def __init__(self, clientId):
		self.token = None
		self.expires = None
		self.clientId = clientId

	def fileName(self):
		return 'dauth.%s.token' % self.clientId

	def get(self):
		if not self.token:
			try:
				with open(self.fileName(), encoding='utf8') as f:
					self.token = f.read().strip()
					self.expires = os.path.getmtime(self.fileName()) + (60 * 60)
			except BaseException as e:
				Print.error(str(e))
				pass


		if not self.token or not self.expires or time.time() > self.expires:
			import cdn.Auth
			self.token = cdn.Auth.getDauthToken(self.clientId)
			self.expires = os.path.getmtime(self.fileName()) + (60 * 60)

		if not self.token:
			raise IOError('No dauth token')


		return self.token

class Proxies:
	def __init__(self):
		self.http = None # 'socks5://192.169.156.211:45578'
		self.https = None # 'socks5://192.169.156.211:45578'

	def get(self):
		m = {}
		if self.http:
			m['http'] = self.http

		if self.https:
			m['https'] = self.https

		if len(m) == 0:
			return None

		return m

class Cdn:
	def __init__(self):
		self.region = None
		self.firmware = None
		self.deviceId = None
		self.environment = None
		self.clientIds = None

	def getDeviceId(self):
		if not self.deviceId:
			raise IOError('device id not set')

		bytes = uhx(self.deviceId)

		if len(bytes) < 7:
			raise IOError('device id too small')

		if len(bytes) > 8:
			raise IOError('device id too large')

		if int.from_bytes(bytes, byteorder='big') < 0x100000000000:
			raise IOError('device id incorrect')

		return self.deviceId.lower()

class EdgeToken:
	def __init__(self, clientId):
		self.token = None
		self.expires = None
		self.clientId = clientId

	def fileName(self):
		return 'edge.%s.token' % self.clientId

	def get(self):
		if not self.token:
			try:
				with open(self.fileName(), encoding='utf8') as f:
					self.token = f.read().strip()
					self.expires = os.path.getmtime(self.fileName()) + (60 * 60)
			except BaseException as e:
				Print.error(str(e))
				pass


		if not self.token or not self.expires or time.time() > self.expires:
			import cdn.Auth
			self.token = cdn.Auth.getEdgeToken(self.clientId)
			self.expires = os.path.getmtime(self.fileName()) + (60 * 60)

		if not self.token:
			raise IOError('No edge token')

		return self.token

class DAuth:
	def __init__(self):
		self.keyGeneration = None
		self.userAgent = None
		self.challenge = None
		self.sysDigest = None
		self.baseURL = 'https://dauth-lp1.ndas.srv.nintendo.net/v6/'

cdn = Cdn()
download = Download()
proxies = Proxies()
dauth = DAuth()

if os.path.isfile('conf/nut.default.conf'):
	load('conf/nut.default.conf')

if os.path.isfile('conf/nut.conf'):
	load('conf/nut.conf')

loadTitleWhitelist()
loadTitleBlacklist()

try:
	edgeToken = EdgeToken(cdn.clientIds['tagaya'])
	c1EdgeToken = EdgeToken(cdn.clientIds['atumC1'])
	dauthToken = DAuthToken(cdn.clientIds['eShop'])
	dauthTigersToken = DAuthToken(cdn.clientIds['tigers'])
	eShopEdgeToken = EdgeToken(cdn.clientIds['eShop'])
except:
	pass

try:
	os.mkdir(Config.paths.nspOut)
except:
	pass


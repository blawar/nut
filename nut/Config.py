#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import time
from binascii import unhexlify as uhx

from nut import Print

from nut.config_impl.download import Download

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

class Server:  # pylint: disable=too-few-public-methods
	"""Server-related settings
	"""

	def __init__(self):
		self.hostname = '0.0.0.0'
		self.port = 9000
		self.enableLocalDriveAccess = 1

class Compression:  # pylint: disable=too-few-public-methods
	"""Compression-related settings
	"""

	def __init__(self):
		self.level = 19
		self.auto = False

class Paths:  # pylint: disable=too-many-instance-attributes
	"""Paths-related settings
	"""

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
		self.keys = 'keys.txt'
		self.calibration = 'PRODINFO.bin'
		self.shopNCert = 'ShopN.pem'
		self.nspOut = '_NSPOUT'
		self.titleImages = 'titles/images/'

		self.duplicates = 'duplicates/'

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

			if not label or len(label) == 0 or label == '':
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

		if not f:
			f = self.titleDemoUpdate
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

def set(json_, paths_, value):  # pylint: disable=redefined-builtin
	last = paths_.pop()
	for path in paths_:
		if path not in json_:
			json_[path] = {}
		json_ = json_[path]
	json_[last] = value

def save(confFile='conf/nut.conf'):
	Print.debug("saving config")
	os.makedirs(os.path.dirname(confFile), exist_ok=True)
	j = {}
	try:
		with open(confFile, encoding='utf8') as f:
			j = json.load(f)
	except BaseException:  # pylint: disable=broad-except
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
		Print.debug("writing config to filesystem")
		json.dump(j, f, indent=4)

def load(confFile):  # pylint: disable=too-many-branches,too-many-statements
	global threads  # pylint: disable=global-statement
	global jsonOutput  # pylint: disable=global-statement
	global titleUrls  # pylint: disable=global-statement
	global pullUrls  # pylint: disable=global-statement
	global region  # pylint: disable=global-statement
	global language  # pylint: disable=global-statement
	global compression  # pylint: disable=global-statement
	global autolaunchBrowser  # pylint: disable=global-statement
	global autoUpdateTitleDb  # pylint: disable=global-statement

	with open(confFile, encoding='utf8') as f:
		try:
			j = json.load(f)
		except BaseException: # pylint: disable=broad-except
			print('Failed to load config file: %s' % confFile) # use normal print because of initialization order of Status / Print
			raise

		try:
			region = j['region']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			language = j['language']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			autolaunchBrowser = j['autolaunchBrowser']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleImages = j['paths']['titleImages']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleBase = j['paths']['titleBase']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleDLC = j['paths']['titleDLC']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleUpdate = j['paths']['titleUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleDemo = j['paths']['titleDemo']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleDemoUpdate = j['paths']['titleDemoUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.duplicates = j['paths']['duplicates']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nsxTitleBase = j['paths']['nsxTitleBase']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nsxTitleDLC = j['paths']['nsxTitleDLC']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nsxTitleUpdate = j['paths']['nsxTitleUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nsxTitleDemo = j['paths']['nsxTitleDemo']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nsxTitleDemoUpdate = j['paths']['nsxTitleDemoUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nszTitleBase = j['paths']['nszTitleBase']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nszTitleDLC = j['paths']['nszTitleDLC']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nszTitleUpdate = j['paths']['nszTitleUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nszTitleDemo = j['paths']['nszTitleDemo']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nszTitleDemoUpdate = j['paths']['nszTitleDemoUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.xciTitleBase = j['paths']['xciTitleBase']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.xciTitleDLC = j['paths']['xciTitleDLC']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.xciTitleUpdate = j['paths']['xciTitleUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.xciTitleDemo = j['paths']['xciTitleDemo']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.xciTitleDemoUpdate = j['paths']['xciTitleDemoUpdate']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.scan = j['paths']['scan']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.nspOut = j['paths']['nspOut']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			paths.titleDatabase = j['paths']['titledb']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			compression.level = int(j['compression']['level'])
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			compression.auto = int(j['compression']['auto']) != 0
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.rankMin = j['download']['rankMin']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.rankMax = j['download']['rankMax']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.ratingMin = j['download']['ratingMin']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.ratingMax = j['download']['ratingMax']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.fileSizeMin = j['download']['fileSizeMin']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.fileSizeMax = j['download']['fileSizeMax']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.releaseDateMin = j['download']['releaseDateMin']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.releaseDateMax = j['download']['releaseDateMax']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.base = j['download']['downloadBase']  # pylint: disable=attribute-defined-outside-init
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.base = j['download']['base']  # pylint: disable=attribute-defined-outside-init
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.regions = j['download']['regions']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.demo = j['download']['demo']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.DLC = j['download']['dlc']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.update = j['download']['update']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.deltas = j['download']['deltas']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			cdn.deviceId = j['cdn']['deviceId']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			cdn.region = j['cdn']['region']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			cdn.environment = j['cdn']['environment']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			cdn.firmware = j['cdn']['firmware']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			cdn.clientIds = j['cdn']['clientIds']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			dauth.keyGeneration = j['cdn']['dAuth']['keyGeneration']
			dauth.challenge = 'key_generation=' + str(dauth.keyGeneration)
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			dauth.userAgent = j['cdn']['dAuth']['userAgent']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			dauth.sysDigest = j['cdn']['dAuth']['sysDigest']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			threads = int(j['threads'])
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			download.sansTitleKey = j['download']['sansTitleKey']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			server.hostname = j['server']['hostname']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			server.port = int(j['server']['port'])
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			server.enableLocalDriveAccess = int(j['server']['enableLocalDriveAccess'])
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			autoUpdateTitleDb = j['autoUpdateTitleDb']
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			for url in j['titleUrls']:
				if url not in titleUrls:
					titleUrls.append(url)
		except BaseException:  # pylint: disable=broad-except
			pass

		try:
			for url in j['pullUrls']:
				if url not in pullUrls:
					pullUrls.append(url)
		except BaseException:  # pylint: disable=broad-except
			pass

def update_scan_paths(new_scan_paths, nsp_files):
	"""Function update_paths is intended to update paths in the configuration file.
	NSPs will be cleared (in memory) if corresponding paths have been changed.

	Args:
					new_scan_paths (list of strings): list of strings (paths) to scan titles in
					nsp_files (map of strings): map of available (scanned) titles
	Returns:
					None
	"""
	path_changed = False

	new_scan_paths_ = new_scan_paths
	if not isinstance(new_scan_paths_, list):
		new_scan_paths_ = [new_scan_paths]

	old_paths = paths.scan

	if new_scan_paths_ != old_paths:
		path_changed = True

	if not path_changed:
		return

	paths.scan = new_scan_paths_
	save()

	if path_changed:
		nsp_files.clear()


def regionLanguages(fileName='titledb/languages.json'):
	global g_regionLanguages  # pylint: disable=global-statement

	if g_regionLanguages is not None:
		return g_regionLanguages

	g_regionLanguages = []

	try:
		with open(fileName, encoding='utf-8-sig') as f:
			g_regionLanguages = json.loads(f.read())
	except BaseException:  # pylint: disable=broad-except
		g_regionLanguages = json.loads('{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"],\
			"PE":["en","es"],"KR":["ko"],"HK":["zh"],"CN":["zh"],"NZ":["en"],"AT":["de"],\
			"BE":["fr","nl"],"CZ":["en"],"DK":["en"],"ES":["es"],"FI":["en"],"GR":["en"],\
			"HU":["en"],"NL":["nl"],"NO":["en"],"PL":["en"],"PT":["pt"],"RU":["ru"],"ZA":["en"],\
			"SE":["en"],"MX":["en","es"],"IT":["it"],"CA":["en","fr"],"FR":["fr"],"DE":["de"],\
			"JP":["ja"],"AU":["en"],"GB":["en"],"US":["es", "en"]}')

	return g_regionLanguages

def loadTitleWhitelist():
	global titleWhitelist  # pylint: disable=global-statement
	titleWhitelist = []
	try:
		with open('conf/whitelist.txt', encoding='utf8') as f:
			for line in f.readlines():
				titleWhitelist.append(line.strip().upper())
	except BaseException:  # pylint: disable=broad-except
		pass

def loadTitleBlacklist():
	global titleBlacklist  # pylint: disable=global-statement
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
					id_ = line.split('|')[0].strip().upper()
					if id_:
						titleBlacklist.append(id_)
		except BaseException:  # pylint: disable=broad-except
			pass


compression = Compression()
paths = Paths()
server = Server()


class DAuthToken:
	"""DAuthToken
	"""

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
			except BaseException as e:  # pylint: disable=broad-except
				Print.error(str(e))  # pylint: disable=undefined-variable

		if not self.token or not self.expires or time.time() > self.expires:
			import cdn.Auth  # pylint: disable=import-outside-toplevel,redefined-outer-name,import-error
			self.token = cdn.Auth.getDauthToken(self.clientId)
			self.expires = os.path.getmtime(self.fileName()) + (60 * 60)

		if not self.token:
			raise IOError('No dauth token')

		return self.token

class Proxies:  # pylint: disable=too-few-public-methods
	"""Proxies-related settings
	"""

	def __init__(self):
		self.http = None  # 'socks5://192.169.156.211:45578'
		self.https = None  # 'socks5://192.169.156.211:45578'

	def get(self):
		m = {}
		if self.http:
			m['http'] = self.http

		if self.https:
			m['https'] = self.https

		if len(m) == 0:
			return None

		return m

class Cdn:  # pylint: disable=too-few-public-methods
	"""Cdn
	"""

	def __init__(self):
		self.region = 'US'
		self.firmware = '12.0.2-1.0'
		self.deviceId = None
		self.environment = 'lp1'
		self.clientIds = { "eShop": "93af0acb26258de9", "atumC1": "3117b250cab38f45", "tigers": "d5b6cac2c1514c56", "tagaya": "41f4a6491028e3c4"}

	def getDeviceId(self):
		if not self.deviceId:
			raise IOError('device id not set')

		bytes_ = uhx(self.deviceId)

		if len(bytes_) < 7:
			raise IOError('device id too small')

		if len(bytes_) > 8:
			raise IOError('device id too large')

		if int.from_bytes(bytes_, byteorder='big') < 0x100000000000:
			raise IOError('device id incorrect')

		return self.deviceId.lower()

class EdgeToken:
	"""EdgeToken
	"""

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
			except BaseException as e:  # pylint: disable=broad-except
				Print.error(str(e))  # pylint: disable=undefined-variable

		if not self.token or not self.expires or time.time() > self.expires:
			import cdn.Auth  # pylint: disable=redefined-outer-name,import-outside-toplevel,import-error
			self.token = cdn.Auth.getEdgeToken(self.clientId)
			self.expires = os.path.getmtime(self.fileName()) + (60 * 60)

		if not self.token:
			raise IOError('No edge token')

		return self.token

class DAuth:  # pylint: disable=too-few-public-methods
	"""DAuth
	"""

	def __init__(self):
		self.keyGeneration = 11
		self.userAgent = "libcurl (nnDauth; 16f4553f-9eee-4e39-9b61-59bc7c99b7c8; SDK 12.3.0.0)"
		self.challenge = 'key_generation=' + str(self.keyGeneration)
		self.sysDigest = "CusHY#000c0002#6tB3UVnmvT_nsNBMPSD-K1oe0IA1cYvYDyqDCjy2W_I="
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
except BaseException:  # pylint: disable=broad-except
	pass

try:
	os.mkdir(paths.nspOut)
except BaseException:  # pylint: disable=broad-except
	pass

try:
	os.mkdir(paths.titleImages)
except BaseException:  # pylint: disable=broad-except
	pass

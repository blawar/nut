#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import platform


class Cdn:
	def __init__(self):
		self.region = 'US'
		self.firmware = '5.1.0-0'
		self.deviceId = '0000000000000000'
		self.environment = 'lp1'
		
class Paths:
	def __init__(self):
		self.titleBase = "titles/{name}[{id}][v{version}].nsp"
		self.titleDLC = "titles/DLC/{name}[{id}][v{version}].nsp"
		self.titleUpdate = "titles/updates/{name}[{id}][v{version}].nsp"
		self.titleDemo = "titles/demos/{name}[{id}][v{version}].nsp"
		self.titleDemoUpdate = "titles/demos/updates/{name}[{id}][v{version}].nsp"
		self.scan = '.'
		self.titleDatabase = 'titledb'
		self.hactool = 'bin/hactool'
		self.keys = 'keys.txt'
		self.NXclientCert = 'nx_tls_client_cert.pem'
		self.shopNCert = 'ShopN.pem'
		self.nspOut = '_NSPOUT'
		
		if platform.system() == 'Linux':
			self.hactool = './' + self.hactool + '_linux'

		if platform.system() == 'Darwin':
			self.hactool = './' + self.hactool + '_mac'
			
		self.hactool = os.path.normpath(self.hactool)
		
class Download:
	def __init(self):
		self.downloadBase = True
		self.demo = False
		self.DLC = True
		self.update = False
		self.sansTitleKey = False
		
cdn = Cdn()
paths = Paths()
download = Download()

titleUrls = []

with open('nut.json', encoding="utf8") as f:
	j = json.load(f)
	
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
		paths.scan = j['paths']['scan']
	except:
		pass

	try:
		paths.archive = j['paths']['archive']
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

	try:
		cdn.firmware = j['cdn']['firmware']
	except:
		pass
	
	try:
		for url in j['titleUrls']:
			if url not in titleUrls:
				titleUrls.append(url)
	except:
		titleUrls = []
	
	try:
		download.sansTitleKey = j['download']['sansTitleKey']
	except:
		pass

if os.path.isfile('CDNSPconfig.json'):	
		with open('CDNSPconfig.json', encoding="utf8") as f:
			j = json.load(f)
			try:
				if j['Values']['TitleKeysURL'] not in titleUrls:
					titleUrls.append(j['Values']['TitleKeysURL'])
			except:
				pass
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os


downloadBase = True
downloadDemo = False
downloadDLC = True
downloadUpdate = False
downloadSansTitleKey = False
titleDatabasePath = None

titleUrls = []

with open('nut.json', encoding="utf8") as f:
	j = json.load(f)
	
	try:
		titleBasePath = j['paths']['titleBase']
	except:
		titleBasePath = "titles/{name}[{id}][v{version}].nsp"
		
	try:
		titleDLCPath = j['paths']['titleDLC']
	except:
		titleDLCPath = "titles/DLC/{name}[{id}][v{version}].nsp"
		
	try:
		titleUpdatePath = j['paths']['titleUpdate']
	except:
		titleUpdatePath = "titles/updates/{name}[{id}][v{version}].nsp"
		
	try:
		titleDemoPath = j['paths']['titleDemo']
	except:
		titleDemoPath = "titles/demos/{name}[{id}][v{version}].nsp"
		
	try:
		titleDemoUpdatePath = j['paths']['titleDemoUpdate']
	except: 
		titleDemoUpdatePath = "titles/demos/updates/{name}[{id}][v{version}].nsp"
	
	try:
		scanPath = j['paths']['scan']
	except:
		scanPath = '.'
		
	try:
		titleDatabasePath = ['paths']['titledb']
	except:
		titleDatabasePath = "titledb"
	
	try:
		downloadBase = j['download']['base']
	except:
		downloadBase = True
		
	try:
		downloadDemo = j['download']['demo']
	except:
		downloadDemo = False
		
	try:
		downloadDLC = j['download']['dlc']
	except:
		downloadDLC = True
		
	try:
		downloadUpdate = j['download']['update']
	except:
		downloadUpdate = False
	
	try:
		for url in j['titleUrls']:
			if url not in titleUrls:
				titleUrls.append(url)
	except:
		titleUrls = []
	
	try:
		downloadSansTitleKey = j['download']['sansTitleKey']
	except:
		downloadSansTitleKey = False

if os.path.isfile('CDNSPconfig.json'):	
		with open('CDNSPconfig.json', encoding="utf8") as f:
			j = json.load(f)
			try:
				if j['Values']['TitleKeysURL'] not in titleUrls:
					titleUrls.append(j['Values']['TitleKeysURL'])
			except:
				pass
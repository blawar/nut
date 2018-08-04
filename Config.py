#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os


downloadBase = True
downloadDemo = False
downloadDLC = True
downloadUpdate = False
downloadSansTitleKey = False

titleUrls = []

with open('nut.json', encoding="utf8") as f:
	j = json.load(f)
	titleBasePath = j['paths']['titleBase']
	titleDLCPath = j['paths']['titleDLC']
	titleUpdatePath = j['paths']['titleUpdate']
	titleDemoPath = j['paths']['titleDemo']
	titleDemoUpdatePath = j['paths']['titleDemoUpdate']
	scanPath = j['paths']['scan']
	
	downloadBase = j['download']['base']
	downloadDemo = j['download']['demo']
	downloadDLC = j['download']['dlc']
	downloadUpdate = j['download']['update']
	
	for url in j['titleUrls']:
		if url not in titleUrls:
			titleUrls.append(url)
	
	if 'sansTitleKey' in j['download']:
		downloadSansTitleKey = j['download']['sansTitleKey']

if os.path.isfile('CDNSPconfig.json'):	
		with open('CDNSPconfig.json', encoding="utf8") as f:
			j = json.load(f)
			try:
				if j['Values']['TitleKeysURL'] not in titleUrls:
					titleUrls.append(j['Values']['TitleKeysURL'])
			except:
				pass
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json


downloadBase = True
downloadDemo = False
downloadDLC = True
downloadUpdate = False
downloadSansTitleKey = False

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
	
	if 'sansTitleKey' in j['download']:
		downloadSansTitleKey = j['download']['sansTitleKey']
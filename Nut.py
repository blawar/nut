#!/usr/bin/python3
# -*- coding: utf-8 -*-
# place this file in your CDNSP directory
# add the following line to the top of your CDNSP.py file:
# from tqdm import tqdm

import os
import re
import pathlib
import urllib3
import json
from Title import Title
import Titles
import Nsp
import Nsps
import CDNSP
import Config
#import blockchain

				
def loadTitleWhitelist():
	global titleWhitelist
	titleWhitelist = []
	with open('whitelist.txt', encoding="utf8") as f:
		for line in f.readlines():
			titleWhitelist.append(line.strip().upper())
			
def loadTitleBlacklist():
	global titleBlacklist
	titleBlacklist = []
	with open('blacklist.txt', encoding="utf8") as f:
		for line in f.readlines():
			titleBlacklist.append(line.strip().upper())
			
def logMissingTitles():
	f = open("missing.txt","w+b")
	
	for k,t in Titles.items():
		if not t.path:
			f.write((t.name + "\r\n").encode("utf-8"))
		
	f.close()
	

if __name__ == '__main__':
	titleWhitelist = []
	titleBlacklist = []

	Titles.load()
		

	urllib3.disable_warnings()


	CDNSP.tqdmProgBar = False
	CDNSP.configPath = os.path.join(os.path.dirname(__file__), 'CDNSPConfig.json')

	if os.path.isfile(CDNSP.configPath):
		CDNSP.hactoolPath, CDNSP.keysPath, CDNSP.NXclientPath, CDNSP.ShopNPath, CDNSP.reg, CDNSP.fw, CDNSP.deviceId, CDNSP.env, CDNSP.dbURL, CDNSP.nspout = CDNSP.load_config(CDNSP.configPath)
	else:
		Config.downloadBase = False
		Config.downloadDLC = False
		Config.downloadDemo = False
		Config.downloadSansTitleKey = False
		Config.downloadUpdate = False

	if CDNSP.keysPath != '':
		CDNSP.keysArg = ' -k "%s"' % CDNSP.keysPath
	else:
		CDNSP.keysArg = ''

	loadTitleWhitelist()
	loadTitleBlacklist()
	Nsps.scan(Config.scanPath)

	for f in Nsps.files:
		f.move()
		
	logMissingTitles()
	Nsps.removeEmptyDir('.', False)

	#setup_download(listTid, get_versions(listTid)[-1], listTkey, True)
	for k,t in Titles.items():
		if not t.path and (not t.isDLC or Config.downloadDLC) and (not t.isDemo or Config.downloadDemo) and (t.key or Config.downloadSansTitleKey) and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
			if not t.id:
				print('no valid id? ' + str(t.path))
				continue
				
			if not t.lastestVersion():
				print('Could not get version for ' + t.name)
				continue
				
			print('Downloading ' + t.name + ', ' + str(t.version).lower())
			CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key, True, '', True)

	Titles.save()
	#for t in titles:
	#	print(t.id + ': ' + t.name + ", " + str(t.path))
	#print(Title.getVersions('010034500641b02c'))
	
	#print(str(Title.getVersion('010034500641a000')))
	#print(str(Title.getVersion('0100e67008d84000')))
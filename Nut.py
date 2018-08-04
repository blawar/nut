#!/usr/bin/python3
# -*- coding: utf-8 -*-
# place this file in your CDNSP directory
# add the following line to the top of your CDNSP.py file:
# from tqdm import tqdm

import argparse
import sys
import os
import re
import pathlib
import urllib3
import json

sys.path.insert(0, 'lib')

from Title import Title
import Titles
import Nsp
import Nsps
import CDNSP
import Nca
import Config
import requests
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
	
def updateDb(url):
	print("Downloading new title database " + url)
	try:
		if url == '' or not url:
			return
		if "http://" not in url and "https://" not in url:
			try:
				url = base64.b64decode(url)
			except Exception as e:
				print("\nError decoding url: ", e)
				return

		r = requests.get(url)
		r.encoding = 'utf-8'

		if r.status_code == 200:
			Titles.loadTitleBuffer(r.text, False)
		else:
			print('Error updating database: ', repr(r))
			
	except Exception as e:
		print('Error downloading:', e)
	
def downloadAll():
	for k,t in Titles.items():
		if not t.path and (not t.isDLC or Config.download.DLC) and (not t.isDemo or Config.download.demo) and (t.key or Config.download.sansTitleKey) and (len(titleWhitelist) == 0 or t.id in titleWhitelist) and t.id not in titleBlacklist:
			if not t.id:
				print('no valid id? ' + str(t.path))
				continue
				
			if not t.lastestVersion():
				print('Could not get version for ' + t.name)
				continue
				
			print('Downloading ' + t.name + ', ' + str(t.version).lower())
			CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key, True, '', True)
			
def export(file):
	Titles.save(file, ['id', 'rightsId', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region'])
	
def scan():
	Nsps.scan(Config.paths.scan)
	Titles.save()
	
def organize():
	scan()
	for f in Nsps.files:
		#print('')
		f.move()
	print('removing empty directories')
	Nsps.removeEmptyDir('.', False)
		
def refresh():
	for f in Nsps.files:
		try:
			f.readMeta()
		except:
			raise
			pass
	Titles.save()
	
def updateVersions(force = True):
	i = 0
	for k,t in Titles.items():
		if force or t.version == None:
			v = t.lastestVersion(True)
			print("%s[%s] v = %s" % (str(t.name), str(t.id), str(v)) )
			
			i = i + 1
			if i % 20 == 0:
				Titles.save()
			
	for t in list(Titles.data().values()):
		if not t.isUpdate and not t.isDLC and t.updateId and t.updateId and not Titles.contains(t.updateId):
			u = Title()
			u.setId(t.updateId)
			
			if u.lastestVersion():
				Titles.set(t.updateId, u)
				
				print("%s[%s] FOUND" % (str(t.name), str(u.id)) )
				
				i = i + 1
				if i % 20 == 0:
					Titles.save()
					
	Titles.save()
			
if __name__ == '__main__':
	titleWhitelist = []
	titleBlacklist = []

	Titles.load()
		

	urllib3.disable_warnings()


	CDNSP.tqdmProgBar = False


	CDNSP.hactoolPath = Config.paths.hactool
	CDNSP.keysPath = Config.paths.keys
	CDNSP.NXclientPath = Config.paths.NXclientCert
	CDNSP.ShopNPath = Config.paths.shopNCert
	CDNSP.reg = Config.cdn.region
	CDNSP.fw = Config.cdn.firmware
	CDNSP.deviceId = Config.cdn.deviceId
	CDNSP.env = Config.cdn.environment
	CDNSP.dbURL = 'titles.txt'
	CDNSP.nspout = Config.paths.nspOut


	if CDNSP.keysPath != '':
		CDNSP.keysArg = ' -k "%s"' % CDNSP.keysPath
	else:
		CDNSP.keysArg = ''

	loadTitleWhitelist()
	loadTitleBlacklist()

	parser = argparse.ArgumentParser()
	parser.add_argument('--base', type=bool, choices=[0, 1], default=Config.download.base*1, help='download base titles')
	parser.add_argument('--demo', type=bool, choices=[0, 1], default=Config.download.demo*1, help='download demo titles')
	parser.add_argument('--update', type=bool, choices=[0, 1], default=Config.download.update*1, help='download title updates')
	parser.add_argument('--dlc', type=bool, choices=[0, 1], default=Config.download.DLC*1, help='download DLC titles')
	parser.add_argument('--nsx', type=bool, choices=[0, 1], default=Config.download.sansTitleKey*1, help='download titles without the title key')
	parser.add_argument('-D', '--download-all', action="store_true", help='download ALL title(s)')
	parser.add_argument('-d', '--download', help='download title(s)')
	parser.add_argument('-i', '--info', help='show info about title or file')
	parser.add_argument('-s', '--scan', action="store_true", help='scan for new NSP files')
	parser.add_argument('-Z', action="store_true", help='update ALL title versions from nintendo')
	parser.add_argument('-z', action="store_true", help='update newest title versions from nintendo')
	parser.add_argument('-o', '--organize', action="store_true", help='rename and move all NSP files')
	parser.add_argument('-U', '--update-titles', action="store_true", help='update titles db from urls')
	parser.add_argument('-r', '--refresh', action="store_true", help='reads all meta from NSP files and queries CDN for latest version information')
	parser.add_argument('-x', '--export', help='export title database in csv format')
	parser.add_argument('-M', '--missing', help='export title database of titles you have not downloaded in csv format')
	
	args = parser.parse_args()
	

	Config.download.base = args.base
	Config.download.DLC = args.dlc
	Config.download.demo = args.demo
	Config.download.sansTitleKey = args.nsx
	Config.download.update = args.update
	
	if args.update_titles:
		for url in Config.titleUrls:
			updateDb(url)
		Titles.save()
		
	if args.download:
		id = args.download.upper()
		if len(id) != 16:
			raise IOError('Invalid title id format')

		if Titles.contains(id):
			title = Titles.get(id)
			CDNSP.download_game(title.id.lower(), title.lastestVersion(), title.key, True, '', True)
		else:
			CDNSP.download_game(id.lower(), Title.getCdnVersion(id.lower()), None, True, '', True)
	
	if args.scan:
		scan()
		
	if args.refresh:
		refresh()
	
	if args.organize:
		organize()
		
	if args.info:
		if args.info.endswith('.xci'):
			f = Nca.Xci(args.info)
		elif args.info.endswith('.nsp'):
			f = Nsp(args.info)
		elif args.info.endswith('.nca'):
			f = Nca.Nca(args.info)
		else:
			f = File(args.info)
		f.printInfo()
			
	
	if args.Z:
		updateVersions(True)
		
	if args.z:
		updateVersions(False)
		
	if args.download_all:
		downloadAll()
		
	if args.export:
		export(args.export)
		
	if len(sys.argv)==1:
		scan()
		organize()
		downloadAll()
	
	#scan()
		
	#logMissingTitles()

	#downloadAll()

	#Titles.save()

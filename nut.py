#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import re
import pathlib
import urllib3
import json

if not getattr(sys, 'frozen', False):
	os.chdir(os.path.dirname(os.path.abspath(__file__)))

#sys.path.insert(0, 'nut')

from nut import Title
from nut import Titles
from nut import Nsps
import Fs
from nut import Config
import requests
from nut import Hex
from nut import Print
import threading
import signal
from nut import Status
import time
import colorama
import Server
import pprint
import random
import queue
import nut

try:
	from nut import blockchain
except:
	raise

			
def logMissingTitles(file):
	nut.initTitles()
	nut.initFiles()

	f = open(file,"w", encoding="utf-8-sig")
	
	for k,t in Titles.items():
		if t.isUpdateAvailable() and (t.isDLC or t.isUpdate or Config.download.base) and (not t.isDLC or Config.download.DLC) and (not t.isDemo or Config.download.demo) and (not t.isUpdate or Config.download.update) and (t.key or Config.download.sansTitleKey) and (len(Config.titleWhitelist) == 0 or t.id in Config.titleWhitelist) and t.id not in Config.titleBlacklist:
			if not t.id or t.id == '0' * 16 or (t.isUpdate and t.lastestVersion() in [None, '0']):
				continue
			f.write((t.id or ('0'*16)) + '|' + (t.key or ('0'*32)) + '|' + (t.name or '') + "\r\n")
		
	f.close()

def logNcaDeltas(file):
	nut.initTitles()
	nut.initFiles()

	x = open(file,"w", encoding="utf-8-sig")
	
	for k,f in Nsps.files.items():
		try:
			t = f.title()
			if (t.isDLC or t.isUpdate or Config.download.base) and (not t.isDLC or Config.download.DLC) and (not t.isDemo or Config.download.demo) and (not t.isUpdate or Config.download.update) and (t.key or Config.download.sansTitleKey) and (len(Config.titleWhitelist) == 0 or t.id in Config.titleWhitelist) and t.id not in Config.titleBlacklist:
				f.open(f.path)
				if f.hasDeltas():
					Print.info(f.path)
					x.write(f.path + "\r\n")
				f.close()
		except KeyboardInterrupt:
			raise
		except BaseException as e:
			Print.info('error: ' + str(e))
		
	x.close()



def getRandomTitleId():
	n = random.randint(0, 0x10000000)
	id = 0x100000000000000
	id += (n & 0xFFFF) << 12
	id += (n & 0xFFF0000) << 20

	return format(id, 'X').zfill(16)

		
def refresh(titleRightsOnly = False):
	nut.initTitles()
	nut.initFiles()
	i = 0
	for k, f in Nsps.files.items():
		try:
			if titleRightsOnly:
				title = Titles.get(f.titleId)
				if title and title.rightsId and (title.key or f.path.endswith('.nsx')):
					continue
			i = i + 1
			print(f.path)
			f.open()
			f.readMeta()
			f.close()

			if i > 20:
				i = 0
				Titles.save()
		except BaseException as e:
			print('exception: ' + str(e))
			pass
	Titles.save()


def unlockAll():
	nut.initTitles()
	nut.initFiles()

	for k,f in Nsps.files.items():
		if f.isUnlockable():
			try:
				if not blockchain.verifyKey(f.titleId, f.title().key):
					raise IOError('Could not verify title key! %s / %s - %s' % (f.titleId, f.title().key, f.title().name))
					continue
				Print.info('unlocking ' + f.path)
				f.open(f.path, 'r+b')
				f.unlock()
				f.close()
			except BaseException as e:
				Print.info('error unlocking: ' + str(e))

def exportVerifiedKeys(fileName):
	nut.initTitles()
	with open(fileName, 'w') as f:
		f.write('id|key|version\n')
		for tid,key in blockchain.blockchain.export().items():
			title = Titles.get(tid)
			if title and title.rightsId:
				f.write(str(title.rightsId) + '|' + str(key) + '|' + str(title.version) + '\n')
				
def exportKeys(fileName):
	nut.initTitles()
	with open(fileName, 'w') as f:
		f.write('id|key|version\n')
		for tid,title in Titles.items():
			if title and title.rightsId and title.key and title.isActive():
				f.write(str(title.rightsId) + '|' + str(title.key) + '|' + str(title.version) + '\n')

def submitKeys():
	for id, t in Titles.items():
		if t.key and len(t.getFiles()) > 0:
			try:
				#blockchain.blockchain.suggest(t.id, t.key)
				if not blockchain.verifyKey(t.id, t.key):
					Print.error('Key verification failed for %s / %s' % (str(t.id), str(t.key)))
					for f in t.getFiles():
						f.hasValidTicket = False
						f.move()
			except LookupError as e:
				Print.info(str(e))
			except OSError as e:
				Print.info(str(e))
			except BaseException as e:
				Print.info(str(e))
				raise


def genTinfoilTitles():
	nut.initTitles()
	nut.initFiles()

	for region, languages in Config.regionLanguages().items():			
		for language in languages:
			nut.importRegion(region, language)
			Titles.save('titledb/titles.%s.%s.json' % (region, language), False)
			#Print.info('%s - %s' % (region, language))
	nut.scanLatestTitleUpdates()
	nut.export('titledb/versions.txt', ['id','rightsId', 'version'])


def matchDemos():
	nut.initTitles()
	nut.initFiles()
	orphans = {}

	Titles.loadTxtDatabases()

	for nsuId, titleId in Titles.nsuIdMap.items():
		for region, languages in Config.regionLanguages().items():			
			for language in languages:
				if nsuId:
					title = Titles.get(str(nsuId), region, language)
					title.id = titleId

	for region, languages in Config.regionLanguages().items():			
		for language in languages:
			for nsuId, rt in Titles.data(region, language).items():
				if rt.id:
					continue
				orphans[nsuId] = rt.name

			Titles.saveRegion(region, language)

	for nsuId, name in orphans.items():
		print(str(nsuId) + '|' + str(name))


def organizeNcas(dir):
	files = [f for f in os.listdir(dir) if f.endswith('.nca')]
	
	for file in files:
		try:
			path = os.path.join(dir, file)
			f = Fs.Nca()
			f.open(path, 'r+b')
			f.close()
			titleId = f.header.titleId
			header = f.header
			os.makedirs(os.path.join(dir, f.header.titleId), exist_ok=True)

			dest = os.path.join(dir, f.header.titleId, file)
			os.rename(path, dest)
			Print.info(dest)
		except BaseException as e:
			Print.info(str(e))

def exportNcaMap(path):
	nut.initTitles()
	nut.initFiles()

	map = {}

	i = 0

	for id, title in Titles.items():
		print(id)
		try:
			nsp = title.getLatestFile()

			if not nsp:
				continue

			nsp.open(args.info, 'r+b')

			map[id] = {}
			map[id]['version'] = int(title.version)
			map[id]['files'] = []
			for f in nsp:
				if isinstance(f, Fs.Nca):
					map[id]['files'].append(f._path)

			i += 1

			if i > 100:
				i = 0
				with open(path, 'w') as outfile:
					json.dump(map, outfile, indent=4)

		except BaseException as e:
			Print.error(str(e))

	with open(path, 'w') as outfile:
		json.dump(map, outfile, indent=4)
			
if __name__ == '__main__':
	try:
		urllib3.disable_warnings()


		parser = argparse.ArgumentParser()
		parser.add_argument('file',nargs='*')
		parser.add_argument('--base', type=int, choices=[0, 1], default=Config.download.base*1, help='download base titles')
		parser.add_argument('--demo', type=int, choices=[0, 1], default=Config.download.demo*1, help='download demo titles')
		parser.add_argument('--update', type=int, choices=[0, 1], default=Config.download.update*1, help='download title updates')
		parser.add_argument('--dlc', type=int, choices=[0, 1], default=Config.download.DLC*1, help='download DLC titles')
		parser.add_argument('--nsx', type=int, choices=[0, 1], default=Config.download.sansTitleKey*1, help='download titles without the title key')
		parser.add_argument('-i', '--info', help='show info about title or file')
		parser.add_argument('--depth', type=int, default=1, help='max depth for file info and extraction')
		parser.add_argument('-I', '--verify', nargs=2, help='verify title key TID TKEY')
		parser.add_argument('-u', '--unlock', help='install available title key into NSX / NSP')
		parser.add_argument('--unlock-all', action="store_true", help='install available title keys into all NSX files')
		parser.add_argument('--set-masterkey1', help='Changes the master key encryption for NSP.')
		parser.add_argument('--set-masterkey2', help='Changes the master key encryption for NSP.')
		parser.add_argument('--set-masterkey3', help='Changes the master key encryption for NSP.')
		parser.add_argument('--set-masterkey4', help='Changes the master key encryption for NSP.')
		parser.add_argument('--set-masterkey5', help='Changes the master key encryption for NSP.')
		parser.add_argument('--remove-title-rights', nargs='+', help='Removes title rights encryption from all NCA\'s in the NSP.')
		parser.add_argument('-s', '--scan', action="store_true", help='scan for new NSP files')
		parser.add_argument('-o', '--organize', action="store_true", help='rename and move all NSP files')
		parser.add_argument('-U', '--update-titles', action="store_true", help='update titles db from urls')
		parser.add_argument('--update-check', action="store_true", help='check for existing titles needing updates')
		parser.add_argument('-r', '--refresh', action="store_true", help='reads all meta from NSP files and queries CDN for latest version information')
		parser.add_argument('-R', '--read-rightsids', action="store_true", help='reads all title rights ids from nsps')
		parser.add_argument('-x', '--extract', nargs='+', help='extract / unpack a NSP')
		parser.add_argument('-c', '--create', help='create / pack a NSP')
		parser.add_argument('-e', '--seteshop', help='Set NSP NCA''s as eshop')
		parser.add_argument('--export', help='export title database in csv format')
		parser.add_argument('--export-versions', help='export title version database in csv format')
		parser.add_argument('-M', '--missing', help='export title database of titles you have not downloaded in csv format')
		parser.add_argument('--nca-deltas', help='export list of NSPs containing delta updates')
		parser.add_argument('--silent', action="store_true", help='Suppress stdout/stderr output')
		parser.add_argument('--json', action="store_true", help='JSON output')
		parser.add_argument('--usb', action="store_true", help='Run usb daemon')
		parser.add_argument('-S', '--server', action="store_true", help='Run server daemon')
		parser.add_argument('-m', '--hostname', help='Set server hostname')
		parser.add_argument('-p', '--port', type=int, help='Set server port')
		parser.add_argument('-b', '--blockchain', action="store_true", help='run blockchain server')
		parser.add_argument('-k', '--submit-keys', action="store_true", help='Submit all title keys to blockchain')
		parser.add_argument('-K', '--export-verified-keys', help='Exports verified title keys from blockchain')
		parser.add_argument('--export-keys', help='Exports title keys from blockchain')


		parser.add_argument('--refresh-regions', action="store_true", help='Refreshes the region and language mappings in Nut\'s DB')
		parser.add_argument('--import-region', help='Localizes Nut\'s DB to the specified region')
		parser.add_argument('--language', help='Specify language to be used with region')

		parser.add_argument('--scan-base', nargs='*', help='Scan for new base Title ID\'s')
		parser.add_argument('--scan-dlc', nargs='*', help='Scan for new DLC Title ID\'s')

		parser.add_argument('--match-demos', action="store_true", help='Try to fuzzy match demo tids to nsuIds')

		parser.add_argument('--gen-tinfoil-titles', action="store_true", help='Outputs language files for Tinfoil')
		parser.add_argument('-O', '--organize-ncas', help='Organize unsorted NCA\'s')
		parser.add_argument('--export-nca-map', help='Export JSON map of titleid to NCA mapping')

		
		args = parser.parse_args()

		Config.download.base = bool(args.base)
		Config.download.DLC = bool(args.dlc)
		Config.download.demo = bool(args.demo)
		Config.download.sansTitleKey = bool(args.nsx)
		Config.download.update = bool(args.update)

		if args.hostname:
			args.server = True
			Config.server.hostname = args.hostname

		if args.port:
			args.server = True
			Config.server.port = int(args.port)

		if args.silent:
			Print.silent = True

		if args.json:
			Config.jsonOutput = True

		Status.start()


		Print.info('                        ,;:;;,')
		Print.info('                       ;;;;;')
		Print.info('               .=\',    ;:;;:,')
		Print.info('              /_\', "=. \';:;:;')
		Print.info('              @=:__,  \,;:;:\'')
		Print.info('                _(\.=  ;:;;\'')
		Print.info('               `"_(  _/="`')
		Print.info('                `"\'')

		if args.extract:
			nut.initTitles()
			for filePath in args.extract:
				#f = Fs.Nsp(filePath, 'rb')
				f = Fs.factory(filePath)
				f.open(filePath, 'rb')
				dir = os.path.splitext(os.path.basename(filePath))[0]
				f.unpack(dir)
				f.close()

		if args.create:
			Print.info('creating ' + args.create)
			nsp = Fs.Nsp(None, None)
			nsp.path = args.create
			nsp.pack(args.file)
			#for filePath in args.file:
			#	Print.info(filePath)

		if args.update_titles:
			nut.initTitles()
			for url in Config.titleUrls:
				nut.updateDb(url)
			Titles.loadTxtDatabases()
			Titles.save()

		if args.update_check:
			nut.initTitles()
			nut.initFiles()
			for _,game in Nsps.files.items():
				title = game.title()
				if title.isUpdate or title.isDLC:
					if game.isUpdateAvailable():
						Print.info(title.getName())
						Print.info(game.isUpdateAvailable())
			exit(0)

		if args.submit_keys:
			nut.initTitles()
			nut.initFiles()
			submitKeys()

		if args.seteshop:
			#nut.initTitles()
			#nut.initFiles()
			f = Fs.factory(args.seteshop)
			f.open(args.seteshop, 'r+b')
			f.setGameCard(False)
			f.close()

		if args.refresh_regions:
			nut.refreshRegions()
			exit(0)

		if args.import_region:
			region = args.import_region.upper()
			if not args.language:
				args.language = Config.language

			args.language = args.language.lower()

			nut.importRegion(region, args.language)
			exit(0)

		if args.usb:
			try:
				from nut import Usb
			except BaseException as e:
				Print.error('pip3 install pyusb, required for USB coms: ' + str(e))
			nut.scan()
			Usb.daemon()

		'''
		if args.download:
			nut.initTitles()
			nut.initFiles()
			for d in args.download:
				download(d)
		'''
	
		if args.scan:
			nut.initTitles()
			nut.initFiles()
			nut.scan()
		
		if args.refresh:
			nut.initTitles()
			nut.initFiles()
			refresh(False)
			
		if args.read_rightsids:
			nut.initTitles()
			nut.initFiles()
			refresh(True)
	
		if args.organize:
			nut.initTitles()
			nut.initFiles()
			nut.organize()

		if args.set_masterkey1:
			nut.initTitles()
			nut.initFiles()
			f = Fs.Nsp(args.set_masterkey1, 'r+b')
			f.setMasterKeyRev(0)
			f.flush()
			f.close()
			pass

		if args.set_masterkey2:
			nut.initTitles()
			nut.initFiles()
			f = Fs.Nsp(args.set_masterkey2, 'r+b')
			f.setMasterKeyRev(2)
			f.flush()
			f.close()
			pass

		if args.set_masterkey3:
			nut.initTitles()
			nut.initFiles()
			f = Fs.Nsp(args.set_masterkey3, 'r+b')
			f.setMasterKeyRev(3)
			f.flush()
			f.close()
			pass

		if args.set_masterkey4:
			nut.initTitles()
			nut.initFiles()
			f = Fs.Nsp(args.set_masterkey4, 'r+b')
			f.setMasterKeyRev(4)
			f.flush()
			f.close()
			pass

		if args.set_masterkey5:
			nut.initTitles()
			nut.initFiles()
			f = Fs.Nsp(args.set_masterkey5, 'r+b')
			f.setMasterKeyRev(5)
			f.flush()
			f.close()
			pass

		if args.remove_title_rights:
			nut.initTitles()
			nut.initFiles()
			for fileName in args.remove_title_rights:
				try:
					f = Fs.Nsp(fileName, 'r+b')
					f.removeTitleRights()
					f.flush()
					f.close()
				except BaseException as e:
					Print.error('Exception: ' + str(e))

		'''
		if args.nca_deltas:
			logNcaDeltas(args.nca_deltas)
		'''

		if args.verify:
			if blockchain.verifyKey(args.verify[0], args.verify[1]):
				Print.info('Title key is valid')
			else:
				Print.info('Title key is INVALID %s - %s' % (args.verify[0], args.verify[1]))

		if args.info:
			nut.initTitles()
			nut.initFiles()

			print('reading')
			f = Fs.factory(args.info)
			f.open(args.info, 'r+b')
			f.printInfo(args.depth+1)


		if args.gen_tinfoil_titles:
			genTinfoilTitles()

		'''
		if args.scrape_title:
			nut.initTitles()
			nut.initFiles()

			if not Titles.contains(args.scrape_title):
				Print.error('Could not find title ' + args.scrape_title)
			else:
				Titles.get(args.scrape_title).scrape(False)
				Titles.save()
				#Print.info(repr(Titles.get(args.scrape_title).__dict__))
				pprint.pprint(Titles.get(args.scrape_title).__dict__)
		'''

		'''
		if args.scrape or args.scrape_delta:
			nut.initTitles()
			nut.initFiles()

			threads = []
			for i in range(nut.scrapeThreads):
				t = threading.Thread(target=nut.scrapeThread, args=[i, args.scrape_delta])
				t.start()
				threads.append(t)

			for t in threads:
				t.join()
		
			Titles.save()
		'''
			

		'''
		if args.Z:
			nut.updateVersions(True)
		
		if args.z:
			nut.updateVersions(False)
		
		if args.V:
			nut.scanLatestTitleUpdates()
		'''

		if args.unlock_all:
			unlockAll()
			pass

		if args.unlock:
			nut.initTitles()
			nut.initFiles()
			Print.info('opening ' + args.unlock)
			f = Fs.Nsp(args.unlock, 'r+b')
			f.unlock()

		if args.export_nca_map:
			exportNcaMap(args.export_nca_map)

		'''
		if args.download_all:
			nut.downloadAll()
			Titles.save()
		'''
		
		if args.export:
			nut.initTitles()
			nut.initFiles()
			nut.export(args.export)

		if args.export_versions:
			nut.initTitles()
			nut.initFiles()
			nut.export(args.export_versions, ['id', 'rightsId', 'version'])
		
		if args.missing:
			logMissingTitles(args.missing)

		if args.match_demos:
			matchDemos()

		if args.blockchain:
			nut.initTitles()
			nut.initFiles()
			try:
				import blockchain
			except:
				pass
			blockchain.run()
		
		if len(sys.argv)==1:
			nut.scan()
			nut.organize()
			nut.downloadAll()
			nut.scanLatestTitleUpdates()
			nut.export('titledb/versions.txt', ['id', 'rightsId', 'version'])

		if args.scan_dlc != None:
			raise RuntimeError('--scan-dlc no longer supported, skipping')

			nut.initTitles()
			nut.initFiles()
			queue = Titles.Queue()
			if len(args.scan_dlc) > 0:
				for id in args.scan_dlc:
					queue.add(id)
			else:
				for i,k in Titles.items():
					if not k.isDLC and not k.isUpdate and k.id:
						queue.add(k.id)
			# startDlcScan(queue)

		if args.scan_base != None:
			raise RuntimeError('--scan-base no longer supported, skipping')
			nut.initTitles()
			nut.initFiles()
			# startBaseScan()

		if args.export_verified_keys:
			exportVerifiedKeys(args.export_verified_keys)
			
		if args.export_keys:
			exportKeys(args.export_keys)

		if args.organize_ncas:
			organizeNcas(args.organize_ncas)

		# server should be last, because this doesn't daemonize
		if args.server:
			# nut.startDownloadThreads()
			nut.initTitles()
			nut.initFiles()
			Server.run()

		Status.close()
	

	except KeyboardInterrupt:
		Config.isRunning = False
		Status.close()
	except BaseException as e:
		Config.isRunning = False
		Status.close()
		raise

	Print.info('fin')


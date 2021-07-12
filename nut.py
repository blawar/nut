#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import re
import pathlib
import urllib3
import json
from filelock import Timeout, FileLock

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
from nut import NszDecompressor
from nut import Hook
import threading
import signal
from nut import Status
import time
import colorama
import Server
import pprint
import random
import shutil
from Fs.Nsp import Nsp
import traceback
import queue
import nut
import Fs.Type

try:
	import cdn
	hasCdn = True
except BaseException:
	hasCdn = False

try:
	from nut import blockchain
except BaseException:
	raise

def logMissingTitles(file):
	nut.initTitles()
	nut.initFiles()

	f = open(file, "w", encoding="utf-8-sig")

	for k, t in Titles.items():
		if t.isUpdateAvailable() and (
			t.isDLC or t.isUpdate or Config.download.base) and (
			not t.isDLC or Config.download.DLC) and (
			not t.isDemo or Config.download.demo) and (
				not t.isUpdate or Config.download.update) and (
					t.key or Config.download.sansTitleKey) and (
						len(
							Config.titleWhitelist) == 0 or t.id in Config.titleWhitelist) and t.id not in Config.titleBlacklist:
			if not t.id or t.id == '0' * 16 or (t.isUpdate and t.lastestVersion() in [None, '0']):
				continue
			f.write((t.id or ('0'*16)) + '|' + (t.key or ('0'*32)) + '|' + (t.name or '') + "\r\n")

	f.close()

def expandFiles(paths):
	files = []
	for path in paths:
		path = pathlib.Path(path).resolve()

		if path.is_file():
			files.append(path)
		else:
			for f_str in os.listdir(path):
				f = pathlib.Path(f_str)
				f = path.joinpath(f)
				files.append(str(f))
	return files

def refresh(titleRightsOnly=False):
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

def getUnlockPath(path, copy):
	if not copy:
		return path

	destination = os.path.join(Config.paths.nspOut, os.path.basename(path))

	if not os.path.exists(destination):
		Print.info('copying "%s" -> "%s"' % (path, destination))
		shutil.copyfile(path, destination)
	return destination


def unlockAll(copy=False):
	nut.initTitles()
	nut.initFiles()

	files = []
	for k, f in Nsps.files.items():
		files.append(f)

	for f in files:
		try:
			if f.isUnlockable() and f.title().isActive():
				if f.title().getLatestNsp() is not None or f.title().getLatestNsz() is not None:
					Print.info('unlocked file arleady exists, skipping ' + str(f.path))
				f.open(getUnlockPath(f.path, copy), 'r+b')
				if not f.verifyKey(f.titleId, f.title().key):
					raise IOError('Could not verify title key! %s / %s - %s' % (f.titleId, f.title().key, f.title().name))
					continue
				Print.info('unlocking ' + str(f.path))

				f.unlock()
				f.close()

		except BaseException as e:
			Print.info('error unlocking: ' + str(e))
			traceback.print_exc(file=sys.stdout)

def exportVerifiedKeys(fileName):
	nut.initTitles()
	with open(fileName, 'w') as f:
		f.write('id|key|version\n')
		for tid, key in blockchain.blockchain.export().items():
			title = Titles.get(tid)
			if title and title.rightsId:
				f.write(str(title.rightsId) + '|' + str(key) + '|' + str(title.version) + '\n')

def exportKeys(fileName):
	nut.initTitles()
	with open(fileName, 'w') as f:
		f.write('id|key|version\n')
		for tid, title in Titles.items():
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
	nut.initTitles(verify=False)
	nut.initFiles(verify=False)

	nut.refreshRegions(False)

	for region, languages in Config.regionLanguages().items():
		for language in languages:
			nut.importRegion(region, language, save=False)
			Titles.save('titledb/titles.%s.%s.json' % (region, language), False)
			#Print.info('%s - %s' % (region, language))
	nut.importRegion()
	exit(0)

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

			if f.header.contentType == Fs.Type.Content.META:
				dest = os.path.join(dir, f.header.titleId, file.split('.')[0] + '.cnmt.nca')
			else:
				dest = os.path.join(dir, f.header.titleId, file.split('.')[0] + '.nca')
			os.rename(path, dest)
			Print.info(dest)
		except BaseException as e:
			Print.info(str(e))

def cleanCsv(s):
	if not s:
		return None

	if ',' in s or '\n' in s or '\r' in s:
		return '"%s"' % s.replace('"', '\'')
	return s

def compressionStats():
	nut.initTitles()
	nut.initFiles()

	results = {}
	i = 0
	sum = 0

	for k, t in Titles.items():
		try:
			if not t.isActive(skipKeyCheck=True):
				continue

			lastestNsz = t.getLatestNsz()

			if not lastestNsz:
				continue

			lastestNsp = t.getLatestNsp(lastestNsz.version)

			if not lastestNsp:
				continue

			nspSize = lastestNsp.getFileSize()
			nszSize = lastestNsz.getFileSize()

			if nspSize > 0 and nszSize > 0:
				cr = nszSize / nspSize
				if t.isDLC:
					type = 'DLC'
				elif t.isUpdate:
					type = 'UPD'
				else:
					type = 'BASE'

				results[k] = {'id': k, 'name': cleanCsv(t.name), 'publisher': cleanCsv(t.publisher), 'type': type, 'nsp': nspSize, 'nsz': nszSize, 'cr': cr}

				i += 1
				sum += cr
		except BaseException as e:
			Print.info(str(e))

	if i == 0:
		Print.info('No data found')
		return

	Print.info('files: %d  average compression ratio: %.2f' % (i, sum / i))
	path = 'compression.stats.csv'
	with open(path, 'w', encoding='utf8') as f:
		f.write('title id,name,publisher,type,nsp,nsz,cr\n')
		for id, data in results.items():
			f.write('%s,%s,%s,%s,%d,%d,%.2f\n' % (data['id'], data['name'], data['publisher'], data['type'], data['nsp'], data['nsz'], data['cr']))

	Print.info('saved compression stats to %s' % path)

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

def download(id):
	bits = id.split(',')

	version = None
	key = None

	if len(bits) == 1:
		id = bits[0].upper()
	elif len(bits) == 2:
		id = bits[0].upper()
		key = bits[1].strip()
	elif len(bits) == 3:
		id = bits[0].upper()
		key = bits[1].strip()
		version = bits[2].strip()
	else:
		Print.info('invalid args: ' + download)
		return False

	if key == '':
		key = None

	if version == '':
		version = None

	if len(id) != 16:
		raise IOError('Invalid title id format')

	if Titles.contains(id):
		title = Titles.get(id)
		cdn.downloadTitle(title.id.lower(), version, key or title.key)
	else:
		cdn.downloadTitle(id.lower(), version, key)
	return True


if __name__ == '__main__':
	try:
		with FileLock("nut.lock") as lock:
			urllib3.disable_warnings()

			#signal.signal(signal.SIGINT, handler)

			parser = argparse.ArgumentParser()
			parser.add_argument('file', nargs='*')
			parser.add_argument('-g', '--ganymede', help='ganymede config file')
			parser.add_argument('-i', '--info', help='show info about title or file')
			parser.add_argument('--depth', type=int, default=1, help='max depth for file info and extraction')
			parser.add_argument('-I', '--verify-title-key', nargs=2, help='verify title key TID TKEY')
			parser.add_argument('--verify-all-signatures', action="store_true", help='verify nca signatures')
			parser.add_argument('--restore', action="store_true", help='attempt to restore a NSP to original valid form')
			parser.add_argument('-N', '--verify-ncas', help='Verify NCAs in container')
			parser.add_argument('-u', '--unlock', action="store_true", help='install available title key into NSX / NSP')
			parser.add_argument('--unlock-all', action="store_true", help='install available title keys into all NSX files')
			parser.add_argument('--copy', action="store_true", help='Copies NSX to local directory before unlocking')
			parser.add_argument('--move', action="store_true", help='Rename and move files to their correct location')
			parser.add_argument('-s', '--scan', action="store_true", help='scan for new NSP files')
			parser.add_argument('-o', '--organize', action="store_true", help='rename and move all NSP files')
			parser.add_argument('-U', '--update-titles', action="store_true", help='update titles db from urls')
			parser.add_argument('--update-check', action="store_true", help='check for existing titles needing updates')
			parser.add_argument('-r', '--refresh', action="store_true", help='reads all meta from NSP files and queries CDN for latest version information')
			parser.add_argument('-R', '--read-rightsids', action="store_true", help='reads all title rights ids from nsps')
			parser.add_argument('-x', '--extract', nargs='+', help='extract / unpack a NSP')
			parser.add_argument('-c', '--create', help='create / pack a NSP')
			parser.add_argument('--rights-id', help='generate ticket for new NSP and sets rights id')
			parser.add_argument('--key', help='generate ticket for new NSP and set title key')
			parser.add_argument('--xci-to-nsp', action="store_true", help='Repack XCI to NSP')
			parser.add_argument('--export', help='export title database in csv format')
			parser.add_argument('--export-versions', help='export title version database in csv format')
			parser.add_argument('-M', '--missing', help='export title database of titles you have not downloaded in csv format')
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
			parser.add_argument('-P', '--pull', action="store_true", help='Sync files from remote locations')
			parser.add_argument('--refresh-regions', action="store_true", help='Refreshes the region and language mappings in Nut\'s DB')
			parser.add_argument('--import-region', help='Localizes Nut\'s DB to the specified region')
			parser.add_argument('--language', help='Specify language to be used with region')
			parser.add_argument('--match-demos', action="store_true", help='Try to fuzzy match demo tids to nsuIds')
			parser.add_argument('--gen-tinfoil-titles', action="store_true", help='Outputs language files for Tinfoil')
			parser.add_argument('-O', '--organize-ncas', help='Organize unsorted NCA\'s')
			parser.add_argument('--export-nca-map', help='Export JSON map of titleid to NCA mapping')
			parser.add_argument('--extract-nca-meta', nargs='+', help='Extract nca metadata from NSPs')
			parser.add_argument('-C', action="store_true", help='Compress NSP')
			parser.add_argument('-l', '--level', type=int, default=19, help='Compression Level')
			parser.add_argument('--output', help='Directory to save the output files')
			parser.add_argument('--compress-all', action="store_true", help='Compress your library to NSZ')
			parser.add_argument('--decompress', action="store_true", help='Decompress NSZ file')
			parser.add_argument('--decompress-all', action="store_true", help='Decompress all NSZ files')
			parser.add_argument('--threads', '-t', type=int, help='Number of threads to use')
			parser.add_argument('--shard', type=int, help='Shard index to use for distributed processing')
			parser.add_argument('--shards', type=int, help='Shard count to use for distributed processing')
			parser.add_argument('--reverse', action="store_true", help='Reverse processing order of some commands')
			parser.add_argument('--compression-stats', action="store_true", help='Compression statistics')
			parser.add_argument('--file-size-max', type=int, help='Maximum file size to compress')
			parser.add_argument('--file-size-min', type=int, help='Minimum file size to compress')
			parser.add_argument('--region', help='Region filter')
			parser.add_argument('--rating-min', type=int, help='Rating minimum')
			parser.add_argument('--rating-max', type=int, help='Rating maximum')
			parser.add_argument('--rank-min', type=int, help='Rank minimum')
			parser.add_argument('--rank-max', type=int, help='Rank maximum')
			parser.add_argument('--mtime-min', type=int, help='mtime minimum')
			parser.add_argument('--mtime-max', type=int, help='mtime maximum')
			parser.add_argument('--base', type=int, choices=[0, 1], default=Config.download.base*1, help='download base titles')
			parser.add_argument('--demo', type=int, choices=[0, 1], default=Config.download.demo*1, help='download demo titles')
			parser.add_argument('--update', type=int, choices=[0, 1], default=Config.download.update*1, help='download title updates')
			parser.add_argument('--dlc', type=int, choices=[0, 1], default=Config.download.DLC*1, help='download DLC titles')
			parser.add_argument('--nsx', type=int, choices=[0, 1], default=Config.download.sansTitleKey*1, help='download titles without the title key')
			parser.add_argument('--dry', action="store_true", help='Dry run, do not download/rename anything')

			if hasCdn:
				parser.add_argument('-D', '--download-all', action="store_true", help='download ALL title(s)')
				parser.add_argument('-d', '--download', nargs='+', help='download title(s)')
				parser.add_argument('--system-update', action="store_true", help='Download latest system update')
				parser.add_argument('-Z', action="store_true", help='update ALL title versions from nintendo')
				parser.add_argument('-z', action="store_true", help='update newest title versions from nintendo')
				parser.add_argument('-V', action="store_true", help='scan latest title updates from nintendo')
				parser.add_argument('--scrape', action="store_true", help='Scrape ALL titles from Nintendo servers')
				parser.add_argument('--scrape-delta', action="store_true", help='Scrape ALL titles from Nintendo servers that have not been scraped yet')
				parser.add_argument('--scrape-title', help='Scrape title from Nintendo servers')
				parser.add_argument('--scrape-nsuid', help='Scrape eshop title by nsuid')
				parser.add_argument('--scrape-shogun', nargs='*', help='Scrape ALL titles from shogun')
				parser.add_argument('--scrape-shogun-missed', nargs='*', help='Scrape titles that are not advertised by shogun but in our database')
				parser.add_argument('--scrape-shogun-delta', nargs='*', help='Scrape new titles from shogun')
				parser.add_argument('-E', '--get-edge-token', action="store_true", help='Get edge token')
				parser.add_argument('--get-dauth-token', action="store_true", help='Get dauth token')
				parser.add_argument('--eshop-latest', action="store_true", help='List newest eshop titles')
				parser.add_argument('--cetk', help='Pull ticket by rightsID')

			args = parser.parse_args()

			if args.hostname:
				args.server = True
				Config.server.hostname = args.hostname

			if args.port:
				args.server = True
				Config.server.port = int(args.port)

			if args.silent:
				Print.silent = True

			if args.file_size_max:
				Config.download.fileSizeMax = args.file_size_max

			if args.file_size_min:
				Config.download.fileSizeMin = args.file_size_min

			if args.region:
				Config.download.addRegion(args.region)

			if args.rating_min:
				Config.download.ratingMin = args.rating_min

			if args.rating_max:
				Config.download.ratingMax = args.rating_max

			if args.rank_min:
				Config.download.rankMin = args.rank_min

			if args.rank_max:
				Config.download.rankMax = args.rank_max

			if args.mtime_min:
				Config.download.mtime_min = args.mtime_min

			if args.mtime_max:
				Config.download.mtime_max = args.mtime_max

			if args.reverse:
				Config.reverse = True
			else:
				Config.reverse = False

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

			if args.scan:
				Config.isScanning = True

			if args.dry:
				Config.dryRun = True

			Config.download.base = bool(args.base)
			Config.download.DLC = bool(args.dlc)
			Config.download.demo = bool(args.demo)
			Config.download.sansTitleKey = bool(args.nsx)
			Config.download.update = bool(args.update)

			Hook.init()

			if args.threads:
				Config.threads = args.threads

			if args.shard is not None:
				Config.shardIndex = args.shard

			if args.shards is not None:
				Config.shardCount = args.shards

			if args.rights_id and args.key:
				nut.initTitles()
				title = Titles.get(args.rights_id[0:16].upper())
				title.key = args.key

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
				nsp.pack(expandFiles(args.file), args.rights_id, args.key)

			if args.xci_to_nsp:
				for input in args.file:
					if not input.endswith('.xci'):
						continue

					f = Fs.factory(input)
					f.open(input, 'rb')
					f.repack()
					f.close()

			if args.C:
				for filePath in args.file:
					try:
						nut.compress(filePath, 21 if args.level is None else args.level, args.output)

					except BaseException as e:
						Print.error(str(e))
						raise

			if args.decompress:
				for f in expandFiles(args.file):
					path = nut.NszDecompressor.decompress(str(f), Config.paths.nspOut)
					if path:
						i = Nsp(path)
						i.move()

			if args.update_titles:
				nut.initTitles()
				for url in Config.titleUrls:
					nut.updateDb(url)
				Titles.loadTxtDatabases()
				Titles.save()

			if args.update_check:
				nut.initTitles()
				nut.initFiles()
				for _, game in Nsps.files.items():
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

			if args.refresh_regions:
				nut.refreshRegions()

			if args.import_region:
				region = args.import_region.upper()
				if not args.language:
					args.language = Config.language

				args.language = args.language.lower()

				nut.importRegion(region, args.language)
				exit(0)

			if hasCdn:
				if args.cetk:
					cdn.Tigers.cetk(args.cetk)

				if args.eshop_latest:
					print(cdn.Shogun.getLatest(args.file[0], args.file[1], args.file[2]))

				if args.scrape_nsuid:
					nut.initTitles()
					print(json.dumps(cdn.Shogun.scrapeTitle(int(args.scrape_nsuid), force=True).__dict__))

			if args.usb:
				try:
					from nut import Usb
				except BaseException as e:
					Print.error('pip3 install pyusb, required for USB coms: ' + str(e))
				nut.scan()
				Usb.daemon()

			if args.scan:
				nut.initTitles()
				nut.initFiles()
				nut.scan()
				
			if args.pull:
				nut.pull()

			if args.refresh:
				nut.initTitles()
				nut.initFiles()
				refresh(False)

			if args.read_rightsids:
				nut.initTitles()
				nut.initFiles()
				refresh(True)

			if args.verify_all_signatures:
				nut.initTitles()
				nut.initFiles()

				filesToScan = {}

				for path, nsp in Nsps.files.items():
					try:
						f = nsp

						if f.verified:
							continue

						if f.titleId and not f.title().isActive():
							continue

						if Config.download.mtime_min and f.getFileModified() < Config.download.mtime_min:
							continue

						if Config.download.mtime_max and f.getFileModified() > Config.download.mtime_max:
							continue

						filesToScan[path] = nsp
					except:
						pass

				with open('file.verification.txt', 'w+', encoding="utf-8") as bf:
					s = Status.create(len(filesToScan), desc='Verifying files...', unit='B')
					for path, nsp in filesToScan.items():
						try:
							f = nsp

							f.open(str(path), 'r+b')							

							if not f.verifyNcaHeaders():
								nsp.verified = False
								raise IOError('bad file')

							nsp.verified = True

							Print.info('good file: ' + str(path))
							bf.write('good file: %s\n' % str(path))
							f.close()
						except:
							f.close()
							Print.error('bad file: ' + str(path))
							bf.write('bad file: %s\n' % str(path))

						s.add()
					s.close()
				Nsps.save()


			if args.verify_title_key:
				nut.initTitles()
				nut.initFiles()
				if blockchain.verifyKey(args.verify[0], args.verify[1]):
					Print.info('Title key is valid')
				else:
					Print.info('Title key is INVALID %s - %s' % (args.verify[0], args.verify[1]))

			if args.restore:
				nut.initTitles()
				nut.initFiles()

				for path in expandFiles(args.file):
					try:
						f = Fs.factory(str(path))
						f.setPath(str(path))
						if f and f.titleId and Nsps.getByTitleId(f.titleId):
							f.moveDupe()
							continue

						f.open(str(path), 'r+b')
						f.restore()
						f.close()
						Print.info('restored %s' % f._path)

						if args.output:
							newPath = os.path.join(args.output, os.path.basename(f._path))
							Print.info('moving %s -> %s' % (path, newPath))
							shutil.move(f._path, newPath)
					except BaseException as e:
						f.close()
						if str(e) == 'junk file':
							os. remove(f._path)
						else:
							print('Failed to restore: %s, %s' % (str(e), path))
							# traceback.print_exc(file=sys.stdout)

			if args.info:
				nut.initTitles()
				nut.initFiles()
				if re.search(r'^[A-Fa-f0-9]+$', args.info.strip(), re.I | re.M | re.S):
					Print.info('%s version = %s' % (args.info.upper(), cdn.version(args.info.lower())))
				else:
					print('reading')
					f = Fs.factory(args.info)
					f.open(args.info, 'rb')

					f.printInfo(args.depth+1)

			if args.verify_ncas:
				nut.initTitles()
				nut.initFiles()
				f = Fs.factory(args.verify_ncas)
				f.open(args.verify_ncas, 'r+b')
				if not f.verify():
					Print.error('Archive is INVALID: %s' % args.verify_ncas)
				else:
					Print.error('Archive is VALID: %s' % args.verify_ncas)
				f.close()

			if hasCdn:
				if args.download:
					nut.initTitles()
					nut.initFiles()
					for d in args.download:
						download(d)
					
				if args.system_update:
					cdn.downloadSystemUpdate()

				if args.scrape_shogun is not None:
					if len(args.scrape_shogun) == 0:
						nut.scrapeShogunThreaded(True)
					else:
						nut.initTitles()
						nut.initFiles()
						for i in args.scrape_shogun:
							if len(i) == 16:
								l = cdn.Shogun.ids(i, force=True)
								if not l or len(l) == 0 or len(l['id_pairs']) == 0:
									print('no nsuId\'s found')
								else:
									print(l)
									for t in l['id_pairs']:
										print('nsuId: ' + str(t['id']))
										print(json.dumps(cdn.Shogun.scrapeTitle(t['id']).__dict__))
										Titles.saveRegion('US', 'en')
							elif len(i) == 2:
								cdn.Shogun.scrapeTitles(i, force=True)
							else:
								print('bleh')

				if args.scrape_shogun_missed != None:
					nut.initTitles()
					nut.initFiles()
					nut.scrapeShogunThreaded(False, refresh = True)

				if args.scrape_shogun_delta is not None:
					nut.scrapeShogunThreaded(False)

				if args.get_edge_token:
					Config.edgeToken.get()

				if args.get_dauth_token:
					Config.dauthToken.get()

				if args.scrape or args.scrape_delta:
					nut.scrape(args.scrape_delta)

				if args.Z:
					nut.updateVersions(True)

				if args.z:
					nut.updateVersions(False)

				if args.V:
					nut.scanLatestTitleUpdates()
					nut.export('titledb/versions.txt', ['id', 'rightsId', 'version'])

				if args.scrape_title:
					nut.initTitles()
					nut.initFiles()

					if not Titles.contains(args.scrape_title):
						Print.error('Could not find title ' + args.scrape_title)
					else:
						Titles.get(args.scrape_title).scrape(False)
						Titles.save()
						# Print.info(repr(Titles.get(args.scrape_title).__dict__))
						pprint.pprint(Titles.get(args.scrape_title).__dict__)

				if args.download_all:
					nut.downloadAll()
					Titles.save()

			if args.gen_tinfoil_titles:
				genTinfoilTitles()

			if args.compression_stats:
				compressionStats()

			if args.unlock_all:
				unlockAll(args.copy)
				pass

			if args.unlock:
				nut.initTitles()
				nut.initFiles()

				for path in expandFiles(args.file):
					path = str(path)
					Print.info('opening ' + path)
					try:
						f = Fs.Nsp(getUnlockPath(path, args.copy), 'r+b')
						if f.isUnlockable(True):
							if not f.verifyKey(f.titleId, Titles.get(f.titleId).key):
								raise IOError('Could not verify title key! %s / %s - %s' % (f.titleId, f.title().key, f.title().name))
							f.unlock()
					except BaseException as e:
						Print.info('error unlocking: ' + str(e))
						traceback.print_exc(file=sys.stdout)
						raise

			if args.move:
				nut.initTitles()
				nut.initFiles()
				for path in expandFiles(args.file):
					try:
						f = Fs.Nsp()
						f.setPath(str(path))
						f.move()
					except BaseException as e:
						Print.info('error moving: ' + str(e))
						traceback.print_exc(file=sys.stdout)
						raise
				Nsps.save()

			if args.export_nca_map:
				exportNcaMap(args.export_nca_map)

			if args.compress_all:
				nut.initTitles()
				nut.initFiles()
				nut.compressAll(19 if args.level is None else args.level)

			if args.decompress_all:
				nut.decompressAll()

			if args.extract_nca_meta:
				nut.extractNcaMeta(args.extract_nca_meta)

			if args.organize:
				nut.initTitles()
				nut.initFiles()
				nut.organize()

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

			if args.server:
				nut.initTitles()
				nut.initFiles()
				Server.run()

			if args.blockchain:
				nut.initTitles()
				nut.initFiles()
				try:
					import blockchain
				except BaseException:
					pass
				blockchain.run()

			if len(sys.argv) == 1:
				nut.initTitles()
				nut.initFiles()
				nut.scan()
				nut.organize()
				nut.downloadAll()
				nut.scanLatestTitleUpdates()
				nut.export('titledb/versions.txt', ['id', 'rightsId', 'version'])

			if args.export_verified_keys:
				exportVerifiedKeys(args.export_verified_keys)

			if args.export_keys:
				exportKeys(args.export_keys)

			if args.organize_ncas:
				organizeNcas(args.organize_ncas)

			if args.ganymede:
				nut.ganymede(args.ganymede)

			Status.close()

	except KeyboardInterrupt:
		Print.info('Keyboard exception')
		Config.isRunning = False
		Status.close()
	except BaseException as e:
		Print.info('nut exception: ' + str(e))
		Config.isRunning = False
		Status.close()
		raise

	Print.info('fin')

Hook.call("exit")

import base64
import datetime
import html
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
from binascii import hexlify as hx
from binascii import unhexlify as uhx
from contextlib import closing

import shutil
import colorama
import requests
import zstandard
from tqdm import tqdm

import Fs
import Fs.Type
from Fs import Cnmt, Nca, Nsp, Pfs0, Rom, BaseFs
from Fs.Pfs0 import Pfs0Stream
from nut import (Config, Keys, Nsps, NszDecompressor, Print, Status, Title,
                 Titles, aes128)

try:
	import cdn
	import cdn.Shogun
	hasCdn = True
except BaseException:
	hasCdn = False

from ganymede import Ganymede

isInitTitles = False
isInitFiles = False
hasScanned = False
status = None
scrapeThreads = 4
scrapeQueue = None
versionHistory = {}
activeDownloads = []
downloadThreadsStarted = False
ncaData = {}
cnmtData = {}

ncaHeaderSize = 0x4000

class RegionLanguage:
	def __init__(self, region, language, preferredRegion, preferredLanguage):
		self.region = region
		self.language = language
		self.preferredRegion = preferredRegion
		self.preferredLanguage = preferredLanguage

		if language == preferredLanguage:
			self.score = 1000
		else:
			self.score = 0

		if region == preferredRegion:
			self.score += 100

		if language == 'en' and region == 'US':
			self.score += 50

		if language == 'fr' and region == 'FR':
			self.score += 50

		if language == 'ja' and region == 'JP':
			self.score += 50

		if language == 'es' and region == 'ES':
			self.score += 50

		if region == 'GB':
			self.score += 40

		if language == 'en':
			self.score += 40

		if language == 'fr':
			self.score += 30

		if language == 'es':
			self.score += 10

		if language == 'de':
			self.score += 10

	def __lt__(self, other):
		return self.score < other.score

	def print(self):
		print('%s - %s' % (self.region, self.language))

class NcaFile:
	def __init__(self, obj=None):
		self.contentType = None
		self.isGameCard = None
		self.cryptoType = None
		self.keyIndex = None
		self.size = None
		self.titleId = None
		self.contentIndex = None
		self.sdkVersion = None
		self.cryptoType2 = None
		self.rightsId = None

		if obj is not None:
			for key, data in obj.items():
				self.__dict__[key] = data

class CnmtFile:
	def __init__(self, titleId=None, version=None, obj=None):
		self.titleId = titleId
		self.version = version
		self.titleType = None

		self.contentEntries = []
		self.metaEntries = []

		if obj is not None:
			for key, data in obj.items():
				self.__dict__[key] = data

	def content(self):
		return self.contentEntries

def sortedFs(nca):
	fs = []
	for i in nca.sections:
		fs.append(i)
	fs.sort(key=lambda x: x.offset)
	return fs

def compress(filePath, compressionLevel=19, outputDir=None, copy = False):
	filePath = os.path.abspath(filePath)
	copy = True

	if copy == True:
		tmpFilePath = os.path.abspath(os.path.join(outputDir, os.path.basename(filePath)))

		if filePath == tmpFilePath:
			copy = False
		else:
			Print.info('copying %s -> %s' % (filePath, tmpFilePath))
			shutil.copyfile(filePath, tmpFilePath)
			filePath = tmpFilePath

	CHUNK_SZ = 0x1000000

	if outputDir is None:
		nszPath = filePath[0:-1] + 'z'
	else:
		nszPath = os.path.join(outputDir, os.path.basename(filePath[0:-1] + 'z'))

	nszPath = os.path.abspath(nszPath)

	Print.info('compressing (level %d) %s -> %s' % (compressionLevel, filePath, nszPath))

	if Config.dryRun:
		return None

	container = Fs.factory(filePath)

	container.open(filePath, 'rb')

	newNsp = Pfs0Stream(nszPath)

	for nspf in container:
		if isinstance(nspf, Fs.Nca) and ((nspf.header.contentType == Fs.Type.Content.PROGRAM or nspf.header.contentType == Fs.Type.Content.PUBLICDATA) or int(nspf.header.titleId, 16) <= 0x0100000000001000):
			if nspf.size > ncaHeaderSize * 2:
				cctx = zstandard.ZstdCompressor(level=compressionLevel)

				newFileName = nspf._path[0:-1] + 'z'

				f = newNsp.add(newFileName, nspf.size)

				start = f.tell()

				nspf.seek(0)
				h = nspf.read(ncaHeaderSize)
				#crypto = aes128.AESXTS(uhx(Keys.get('header_key')))
				#d = crypto.decrypt(h)

				# if d[0x200:0x204] == b'NCA3':
				#	d = d[0:0x200] + b'NCZ3' + d[0x204:]
				#	h = crypto.encrypt(d)
				# else:
				#	raise IOError('unknown NCA magic')

				# self.partition(0x0, 0xC00, self.header, Fs.Type.Crypto.XTS, uhx(Keys.get('header_key')))
				f.write(h)
				written = ncaHeaderSize

				compressor = cctx.stream_writer(f)

				sections = []
				sectionsTmp = []
				for fs in sortedFs(nspf):
					sectionsTmp += fs.getEncryptionSections()

				currentOffset = ncaHeaderSize
				for fs in sectionsTmp:
					if fs.offset < ncaHeaderSize:
						if fs.offset + fs.size < ncaHeaderSize:
							currentOffset = fs.offset + fs.size
							continue
						else:
							fs.size -= ncaHeaderSize - fs.offset
							fs.offset = ncaHeaderSize
					elif fs.offset > currentOffset:
						sections.append(BaseFs.EncryptedSection(currentOffset, fs.offset - currentOffset, Fs.Type.Crypto.NONE, None, None))
					elif fs.offset < currentOffset:
						raise IOError("misaligned nca partitions")

					sections.append(fs)
					currentOffset = fs.offset + fs.size

				header = b'NCZSECTN'
				header += len(sections).to_bytes(8, 'little')

				i = 0
				for fs in sections:
					i += 1
					header += fs.offset.to_bytes(8, 'little')
					header += fs.size.to_bytes(8, 'little')
					header += fs.cryptoType.to_bytes(8, 'little')
					header += b'\x00' * 8
					header += fs.cryptoKey
					header += fs.cryptoCounter

				f.write(header)
				written += len(header)

				bar = Status.create(nspf.size, desc=os.path.basename(nszPath), unit='B')

				decompressedBytes = ncaHeaderSize
				bar.add(ncaHeaderSize)

				for section in sections:
					#print('offset: %x\t\tsize: %x\t\ttype: %d\t\tiv%s' % (section.offset, section.size, section.cryptoType, str(hx(section.cryptoCounter))))
					o = nspf.partition(offset=section.offset, size=section.size, n=None, cryptoType=section.cryptoType,
									   cryptoKey=section.cryptoKey, cryptoCounter=bytearray(section.cryptoCounter), autoOpen=True)

					while not o.eof():
						buffer = o.read(CHUNK_SZ)

						if len(buffer) == 0:
							raise IOError('read failed')

						written += compressor.write(buffer)

						decompressedBytes += len(buffer)
						bar.add(len(buffer))

					o.close()

				compressor.flush(zstandard.FLUSH_FRAME)
				bar.close()

				Print.info('%d written vs %d tell' % (written, f.tell() - start))
				written = f.tell() - start
				Print.info('compressed %d%% %d -> %d  - %s' % (int(written * 100 / nspf.size), decompressedBytes, written, nspf._path))
				newNsp.resize(newFileName, written)

				continue

		f = newNsp.add(nspf._path, nspf.size)
		nspf.seek(0)
		while not nspf.eof():
			buffer = nspf.read(CHUNK_SZ)
			f.write(buffer)

	newNsp.close()
	container.close()

	if copy:
		os.unlink(tmpFilePath)

	return nszPath

def compressWorker(q, level, output, totalStatus):
	while not q.empty():
		try:
			path = q.get(block=False)
			totalStatus.add(1)

			nszFile = compress(path, level, output)

			if nszFile:
				nsp = Fs.Nsp(nszFile, None)
				nsp.hasValidTicket = True
				nsp.move(forceNsp=True)
				Nsps.files[nsp.path] = nsp
				Nsps.save()
		except queue.Empty as e:
			return
		except BaseException as e:
			Print.info('COMPRESS WORKER EXCEPTION: ' + str(e))
			traceback.print_exc(file=sys.stdout)

def ganymede(config):
	initTitles()
	initFiles()

	with Ganymede(config) as g:
		for k, t in Titles.items():
			try:
				if not t.isActive(skipKeyCheck=True):
					continue

				lastestNsz = t.getLatestNsz()

				if lastestNsz is None:
					continue

				g.push(t.id, lastestNsz.version, lastestNsz.path, lastestNsz.size)

			except BaseException:
				raise

def compressAll(level=19, copy = False):
	initTitles()
	initFiles()

	global activeDownloads
	global status

	i = 0
	Print.info('Compressing All')

	if Config.reverse:
		q = queue.LifoQueue()
	else:
		q = queue.Queue()

	for k, t in Titles.items():
		try:
			i = i + 1
			if not t.isActive(skipKeyCheck=True):
				continue

			lastestNsp = t.getLatestNsp()

			if not lastestNsp:
				continue

			if lastestNsp.titleId.endswith('000') and lastestNsp.version and int(lastestNsp.version) > 0:
				Print.info('Cannot compress sparse file: ' + str(lastestNsp.path))
				continue

			lastestNsz = t.getLatestNsz()

			if lastestNsz is not None and int(lastestNsz.version) >= int(lastestNsp.version):
				continue

			if Config.download.fileSizeMax is not None and lastestNsp.getFileSize() > Config.download.fileSizeMax:
				continue

			if Config.download.fileSizeMin is not None and lastestNsp.getFileSize() < Config.download.fileSizeMin:
				continue

			if Config.limit:
				Config.limitCount += 1

				if Config.limitCount > Config.limit:
					continue

			q.put(lastestNsp.path)

		except BaseException as e:
			Print.info('COMPRESS ALL EXCEPTION: ' + str(e))

	numThreads = Config.threads
	threads = []

	s = Status.create(q.qsize(), desc="NSPs", unit='B')

	if numThreads > 0:
		Print.info('creating compression threads ' + str(q.qsize()))

		for i in range(numThreads):
			t = threading.Thread(target=compressWorker, args=[q, level, Config.paths.nspOut, s])
			t.daemon = True
			t.start()
			threads.append(t)

		for t in threads:
			t.join()
	else:
		compressWorker(q, level, Config.paths.nspOut, s)

	s.close()

def decompressWorker(q, output, totalStatus):
	while not q.empty():
		try:
			path = q.get(block=False)
			totalStatus.add(1)

			path = NszDecompressor.decompress(path, output)
			if path:
				i = Nsp(path)
				i.move()

		except queue.Empty as e:
			return
		except BaseException as e:
			Print.info('DECOMPRESS WORKER EXCEPTION: ' + str(e))
			traceback.print_exc(file=sys.stdout)

def getVer(o):
	if not o:
		return 0xFFFFFFFFFFFFFFFF
	return int(o.version)

def decompressAll():
	initTitles()
	initFiles()

	global activeDownloads
	global status

	i = 0
	Print.info('De-compressing All')

	if Config.reverse:
		q = queue.LifoQueue()
	else:
		q = queue.Queue()

	for k, t in Titles.items():
		try:
			i = i + 1
			if not t.isActive(skipKeyCheck=True):
				continue

			lastestNsz = t.getLatestNsz()

			if not lastestNsz:
				continue

			lastestNsp = t.getLatestNsp()

			if lastestNsp is not None and int(lastestNsp.version) >= int(lastestNsz.version):
				continue

			if Config.dryRun:
				Print.info('nsp ver = %x, nsz ver = %x, %s' % (getVer(lastestNsp), getVer(lastestNsz), t.getName()))

			if Config.download.fileSizeMax is not None and lastestNsz.getFileSize() > Config.download.fileSizeMax:
				continue

			if Config.download.fileSizeMin is not None and lastestNsz.getFileSize() < Config.download.fileSizeMin:
				continue

			if Config.limit:
				Config.limitCount += 1

				if Config.limitCount > Config.limit:
					continue

			q.put(lastestNsz.path)

		except BaseException as e:
			Print.info('DECOMPRESS ALL EXCEPTION: ' + str(e))

	numThreads = Config.threads
	threads = []

	s = Status.create(q.qsize(), desc="NSPs", unit='B')

	if numThreads > 0:
		Print.info('creating decompression threads ' + str(q.qsize()))

		for i in range(numThreads):
			t = threading.Thread(target=decompressWorker, args=[q, Config.paths.nspOut, s])
			t.daemon = True
			t.start()
			threads.append(t)

		for t in threads:
			t.join()
	else:
		decompressWorker(q, Config.paths.nspOut, s)

	s.close()

def refreshRegions(save=True):
	for region in Config.regionLanguages():
		for language in Config.regionLanguages()[region]:
			for i in Titles.data(region, language):
				regionTitle = Titles.data(region, language)[i]

				if regionTitle.id:
					title = Titles.get(regionTitle.id, None, None)

					if not hasattr(title, 'regions') or not title.regions:
						title.regions = []

					if not hasattr(title, 'languages') or not title.languages:
						title.languages = []

					if region not in title.regions:
						title.regions.append(region)

					if language not in title.languages:
						title.languages.append(language)
	if save:
		Titles.save()

def importRegion(region='US', language='en', save=True):
	if region not in Config.regionLanguages() or language not in Config.regionLanguages()[region]:
		Print.info('Could not locate %s/%s !' % (region, language))
		return False

	Hook.call("import.pre", region, language)
	regionLanguages = []

	for region2 in Config.regionLanguages():
		for language2 in Config.regionLanguages()[region2]:
			regionLanguages.append(RegionLanguage(region2, language2, region, language))

	for rl in sorted(regionLanguages):
		data = Titles.data(rl.region, rl.language)
		for nsuId in sorted(data.keys(), reverse=True):
			regionTitle = data[nsuId]
			if not regionTitle.id:
				continue

			try:
				for tid in regionTitle.ids:
					title = Titles.get(tid, None, None)
					title.importFrom(regionTitle, rl.region, rl.language, preferredRegion=region, preferredLanguage=language)
			except:
				title = Titles.get(regionTitle.id, None, None)
				title.importFrom(regionTitle, rl.region, rl.language, preferredRegion=region, preferredLanguage=language)

	Titles.loadTxtDatabases()
	Hook.call("import.post", region, language)
	if save:
		Titles.save()

def isTitleDbStale():
	try:
		age = time.time() - os.path.getmtime('titledb/titles.json')

		if age < 0 or age > 48 * 60 * 60:
			return True
		return False
	except BaseException:
		return True

def downloadRepoFile(path):
	baseUrl = 'https://github.com/blawar/titledb/raw/master/'
	finalFile = os.path.join('titledb', path)
	tmpFile = finalFile + '.tmp'
	try:
		with open(tmpFile, 'wb') as f:
			bytes = download(baseUrl + path, f, checkSize=False)
			if bytes == 0:
				raise IOError('downloaded empty file')
		try:
			os.remove(finalFile)
		except BaseException:
			pass
		os.rename(tmpFile, finalFile)
		return True
	except BaseException as e:
		Print.error(str(e))

	try:
		os.remove(tmpFile)
	except BaseException:
		pass

def decompressZstd(src, dest):
	with open(src, 'rb') as rf:
		with open(dest, 'wb') as f:
			dctx = zstandard.ZstdDecompressor()
			reader = dctx.stream_reader(rf)

			while True:
				chunk = reader.read(8 * 1000 * 1000)
				if not chunk:
					break

				f.write(chunk)

def updateTitleDb(force=False):
	if not Config.autoUpdateTitleDb and not force:
		return

	try:
		os.mkdir('titledb')
	except BaseException:
		pass

	Print.info('downloading titledb files')

	try:
		with open('titledb/db.bin', 'wb') as f:
			bytes = download('http://tinfoil.media/repo/db/db.bin', f, checkSize=False)

		decompressZstd('titledb/db.bin', 'titledb/db.nza')
		container = Fs.Nsp('titledb/db.nza')

		container.open('titledb/db.nza', 'rb')
		for nspf in container:
			with open(os.path.join('titledb', nspf._path), 'wb') as f:
				while not nspf.eof():
					f.write(nspf.read(8 * 1000 * 1000))

		container.close()

		try:
			os.remove('titledb/db.nza')
		except BaseException:
			pass

		refreshRegions(save=False)
		importRegion(Config.region, Config.language)
		return

	except BaseException as e:
		Print.error('error getting tinfoil.io titledb: ' + str(e))

	fileList = []

	for region, languages in Config.regionLanguages().items():
		for language in languages:
			fileList.append('%s.%s.json' % (region.upper(), language.lower()))

	for path in fileList:
		downloadRepoFile(path)

	refreshRegions(save=False)
	importRegion(Config.region, Config.language)

def initTitles(verify=True):
	global isInitTitles
	if isInitTitles:
		return

	isInitTitles = True

	if Config.autoUpdateTitleDb and isTitleDbStale():
		updateTitleDb()

	Titles.load()

	initFiles(verify=verify)
	Titles.queue.load()

def initFiles(verify=True):
	global isInitFiles
	if isInitFiles:
		return

	isInitFiles = True

	Nsps.load(verify=verify)

def scan():
	global hasScanned

	# if hasScanned:
	#	return
	hasScanned = True
	initTitles()
	initFiles()

	for path in Config.paths.scan:
		Nsps.scan(path)

class Progress:
	def __init__(self, response, f):
		self.response = response
		self.f = f
		self.status = Status.create(1, 'Downloading ' + os.path.basename(f.url))

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def close(self):
		if self.status is not None:
			self.status.close()
			self.status = None

	def write(self, chunk):
		self.response.write(chunk)
		self.status.add(len(chunk))


def serveFile(response, path, filename=None):
	with Fs.driver.openFile(path) as f:
		try:
			with Progress(response=response, f=f) as progress:
				f.chunk(progress.write, offset=None, size=None)
		except BaseException as e:
			Print.error('File download exception: ' + str(e))

def pullWorker(q, s):

	while True:
		if q.empty():
			break

		nsp = q.get()

		if not nsp:
			break

		try:
			hasValidTicket = nsp.hasValidTicket

			tmpFile = getName(nsp.titleId, nsp.version, path=nsp.path)
			Print.info('Downloading ' + nsp.path)

			if Config.dryRun:
				continue

			if Config.download.fileSizeMax is not None and nsp.getFileSize() > Config.download.fileSizeMax:
				continue

			if Config.download.fileSizeMin is not None and nsp.getFileSize() < Config.download.fileSizeMin:
				continue

			with open(tmpFile, 'wb') as f:
				serveFile(f, nsp.downloadPath, os.path.basename(nsp.path))

			nsp = Fs.factory(tmpFile, tmpFile, None)
			nsp.hasValidTicket = hasValidTicket
			nsp.move(forceNsp=hasValidTicket)
			Nsps.files[nsp.path] = nsp
			Nsps.save()
		except BaseException as e:
			Print.error('FTP SYNC EXCEPTION: ' + str(e))
			traceback.print_exc(file=sys.stdout)
			# raise #TODO
		s.add()
	Print.info('thread exiting')

def _ftpsync(url):
	if Config.reverse:
		q = queue.LifoQueue()
	else:
		q = queue.Queue()

	fileList = []

	for f in Fs.driver.openDir(url).ls():
		if f.isFile():
			fileList.append(f.url)

	for path in fileList:
		try:
			if path.split('.')[-1].lower() not in ('nsx', 'nsz', 'nsp', 'xci'):
				continue

			unq = urllib.parse.unquote(path)
			nsp = Fs.factory(unq, unq, None)
			nsp.downloadPath = path

			if not nsp.titleId:
				continue

			title = Titles.get(nsp.titleId)

			if not title.isActive(skipKeyCheck=True):
				continue

			files = title.getFiles(path[-3:])
			files = [x for x in files if int(x.version) >= int(nsp.version)]

			if not len(files):
				if path[-3:] == 'nsx':
					if len(Titles.get(nsp.titleId).getFiles('nsp')) or len(Titles.get(nsp.titleId).getFiles('nsz')):
						continue

				if Config.limit:
					Config.limitCount += 1

					if Config.limitCount > Config.limit:
						continue

				q.put(nsp)
		except BaseException as e:
			Print.error(str(e))
			# raise #TODO

	numThreads = Config.threads
	threads = []

	s = Status.create(q.qsize(), 'Total File Pulls')
	if numThreads > 0:
		Print.info('creating pull threads, items: ' + str(q.qsize()))

		for i in range(numThreads):
			t = threading.Thread(target=pullWorker, args=[q, s])
			t.daemon = True
			t.start()
			threads.append(t)

		for t in threads:
			t.join()
	else:
		pullWorker(q, s)
	s.close()

def pull():
	initTitles()
	initFiles()
	for url in Config.pullUrls:
		_ftpsync(url)

def makeRequest(method, url, certificate='', hdArgs={}):
	reqHd = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
		'Accept': '*/*',
		'Connection': 'keep-alive'
	}
	reqHd.update(hdArgs)

	r = requests.request(method, url, headers=reqHd, verify=False, stream=True, proxies=Config.proxies.get())

	if r.status_code == 403:
		raise IOError('Request rejected by server!')

	return r

def download(url, f, titleId=None, name=None, checkSize=True):
	bytes = 0
	r = makeRequest('GET', url)

	if r.status_code == 404:
		Print.error('could not download: ' + str(url))
		return 0
	size = int(r.headers.get('Content-Length'))

	chunkSize = 0x100000

	if size >= 10000:
		s = Status.create(size, desc=name, unit='B')
		if titleId is not None:
			s.id = titleId.upper()

		for chunk in r.iter_content(chunkSize):
			f.write(chunk)
			s.add(len(chunk))
			bytes += len(chunk)

			if not Config.isRunning:
				break
		s.close()
	else:
		f.write(r.content)
		bytes += len(r.content)

	if checkSize and size != 0 and bytes != size:
		raise ValueError('Downloaded data is not as big as expected (%s/%s)!' % (bytes, size))

	return bytes

def organize():
	initTitles()
	initFiles()

	# scan()
	Print.info('organizing')
	# for k, f in Nsps.files.items():
	#print('moving ' + f.path)
	#Print.info(str(f.hasValidTicket) +' = ' + f.path)
	#	f.move()

	for id, t in Titles.data().items():
		if not t.isActive(True):
			continue

		files = {}
		for f in t.getFiles():
			ext = f.path[-4:]
			if ext not in files:
				files[ext] = []

			files[ext].append(f)

		hasNsp = False

		if '.nsp' in files and len(files['.nsp']) > 0:
			latest = t.getLatestNsp()

			if latest:
				for f in files['.nsp']:
					if f.path != latest.path:
						f.moveDupe()

				hasNsp = True
				latest.move()

		if '.nsz' in files and len(files['.nsz']) > 0:
			latest = t.getLatestNsz()

			if latest:
				for f in files['.nsz']:
					if f.path != latest.path:
						f.moveDupe()

				hasNsp = True
				latest.move()

		if '.nsx' in files and len(files['.nsx']) > 0:
			latest = t.getLatestNsx()

			if latest:
				for f in files['.nsx']:
					if f.path != latest.path:
						f.moveDupe()

				if hasNsp:
					latest.moveDupe()
				else:
					latest.move()

		if '.xci' in files and len(files['.xci']) > 0:
			latest = t.getLatestXci()

			if latest:
				for f in files['.xci']:
					if f.path != latest.path:
						f.moveDupe()

				latest.move()

	Print.info('removing empty directories')
	Nsps.removeEmptyDir('.', False)
	Nsps.save()

def export(file, cols=['id', 'rightsId', 'isUpdate', 'isDLC', 'isDemo', 'baseName', 'name', 'version', 'region']):
	# def export(file, cols = ['rightsId', 'key', 'name']):
	initTitles()
	Titles.export(file, cols)

def updateVersions(force=True):
	initTitles()
	initFiles()

	i = 0
	for k, t in tqdm(Titles.items()):
		if force or t.version is None:
			if t.isActive():
				v = t.lastestVersion(True)
				Print.info("%s[%s] v = %s" % (str(t.name), str(t.id), str(v)))

	for t in list(Titles.data().values()):
		if not t.isUpdate and not t.isDLC and t.updateId and t.updateId and not Titles.contains(t.updateId):
			u = Title.Title()
			u.setId(t.updateId)

			if u.lastestVersion():
				Titles.set(t.updateId, u)

				Print.info("%s[%s] FOUND" % (str(t.name), str(u.id)))

	Titles.save()

def scrapeThread(st, delta=True):
	while scrapeQueue.qsize() > 0:
		titleId = scrapeQueue.get()
		try:
			Titles.get(titleId).scrape(delta)
			st.add()
		except BaseException as e:
			Print.error(str(e))
	Print.info('thread exit')

def scrape(delta):
	initTitles()
	initFiles()

	global scrapeQueue

	if Config.reverse:
		scrapeQueue = queue.LifoQueue()
	else:
		scrapeQueue = queue.Queue()

	for titleId in Titles.titles.keys():
		scrapeQueue.put(titleId)

	st = Status.create(scrapeQueue.qsize(), 'eShop meta scrape')
	threads = []
	for i in range(scrapeThreads):
		t = threading.Thread(target=scrapeThread, args=[st, delta])
		t.start()
		threads.append(t)

	for t in threads:
		t.join()

	Titles.save()
	st.close()

def setVersionHistory(titleId, ver, date):
	global versionHistory

	if ver == '' or ver is None or ver == 'none':
		return

	ver = int(ver)
	titleId = str(titleId).lower()

	if ver == 0:
		return

	if len(titleId) > 16:
		titleId = titleId[0:16]

	if titleId not in versionHistory:
		versionHistory[titleId] = {}

	if ver not in versionHistory[titleId]:
		versionHistory[titleId][ver] = date
	else:
		if date < versionHistory[titleId][ver]:
			versionHistory[titleId][ver] = date

def updateDb(url, c=0):
	initTitles()

	c += 1

	if c > 3:
		return False

	Print.info("Downloading new title database " + url)
	try:
		if url == '' or not url:
			return
		if "http://" not in url and "https://" not in url:
			try:
				url = base64.b64decode(url)
			except Exception as e:
				Print.info("\nError decoding url: %s" % e)
				return

		r = requests.get(url)
		r.encoding = 'utf-8-sig'

		if r.status_code == 200:
			try:
				m = re.search(r'<a href="([^"]*)">Proceed</a>', r.text)
				if m:
					return updateDb(m.group(1), c)
			except BaseException:
				pass
			Titles.loadTitleBuffer(r.text, False)
		else:
			Print.info('Error updating database: %s' % repr(r))

	except Exception as e:
		Print.info('Error downloading:' + str(e))

def downloadFile(url, fPath):
	fName = os.path.basename(fPath).split()[0]

	if os.path.exists(fPath):
		dlded = os.path.getsize(fPath)
		r = makeRequest('GET', url, hdArgs={'Range': 'bytes=%s-' % dlded})

		if r.headers.get('Server') != 'openresty/1.9.7.4':
			Print.info('Download is already complete, skipping!')
			return fPath
		elif r.headers.get('Content-Range') is None:  # CDN doesn't return a range if request >= filesize
			fSize = int(r.headers.get('Content-Length'))
		else:
			fSize = dlded + int(r.headers.get('Content-Length'))

		if dlded == fSize:
			Print.info('Download is already complete, skipping!')
			return fPath
		elif dlded < fSize:
			Print.info('Resuming download...')
			f = open(fPath, 'ab')
		else:
			Print.error('Existing file is bigger than expected (%s/%s), restarting download...' % (dlded, fSize))
			dlded = 0
			f = open(fPath, "wb")
	else:
		dlded = 0
		r = makeRequest('GET', url)
		fSize = int(r.headers.get('Content-Length'))
		f = open(fPath, 'wb')

	chunkSize = 0x100000

	if fSize >= 10000:
		s = Status.create(fSize, desc=fName, unit='B')
		#s.id = titleId.upper()
		s.add(dlded)
		for chunk in r.iter_content(chunkSize):
			f.write(chunk)
			s.add(len(chunk))
			dlded += len(chunk)

			if not Config.isRunning:
				break
		s.close()
	else:
		f.write(r.content)
		dlded += len(r.content)

	# if fSize != 0 and dlded != fSize:
	#	raise ValueError('Downloaded data is not as big as expected (%s/%s)!' % (dlded, fSize))

	f.close()
	Print.debug('\r\nSaved to %s!' % f.name)
	return fPath

def loadNcaData():
	global cnmtData
	global ncaData

	if not os.path.isfile('titledb/cnmts.json'):
		return

	try:
		with open('titledb/cnmts.json', encoding="utf-8-sig") as f:
			tmpData = json.loads(f.read())

			for titleId, j in tmpData.items():
				cnmtData[titleId] = {}
				for version, data in j.items():
					#version = str(version)
					#cnmtData[titleId][version] = CnmtFile(obj = data)
					getCnmt(titleId, version, data)

			#cnmtData = tmpData
	except BaseException:
		raise

	try:
		with open('titledb/ncas.json', encoding="utf-8-sig") as f:
			ncaData = json.loads(f.read())

			for ncaId, data in ncaData.items():
				ncaData[ncaId] = NcaFile(obj=data)
	except BaseException:
		raise

def saveNcaData():
	global cnmtData
	global ncaData

	try:
		out = {}

		for k, j in cnmtData.items():
			out[k] = {}

			for v, row in j.items():
				out[k][v] = row.__dict__

		with open('titledb/cnmts.json', 'w') as f:
			json.dump(out, f, indent=4, sort_keys=True)
	except BaseException:
		raise

	try:
		out = {}

		for k, v in ncaData.items():
			out[k] = v.__dict__

		with open('titledb/ncas.json', 'w') as f:
			json.dump(out, f, indent=4, sort_keys=True)
	except BaseException:
		raise

def getNca(ncaId):
	global ncaData
	ncaId = ncaId.lower()

	if ncaId not in ncaData:
		ncaData[ncaId] = NcaFile()

	return ncaData[ncaId]

def hasBuildId(cnmt):
	for i in cnmt.content():
		if 'buildId' in i:
			return True
	return False


def hasCnmt(titleId=None, version=None):
	titleId = titleId.lower()
	version = str(version)

	if titleId not in cnmtData:
		return False

	if version not in cnmtData[titleId]:
		return False

	if titleId.endswith('000') or titleId.endswith('800'):
		if not hasBuildId(cnmtData[titleId][version]):
			return False

	return True


def getCnmt(titleId=None, version=None, obj=None):
	global cnmtData
	titleId = titleId.lower()
	version = str(version)

	if titleId not in cnmtData:
		cnmtData[titleId] = {}

	if version not in cnmtData[titleId]:
		cnmtData[titleId][version] = CnmtFile(titleId, version, obj)

	return cnmtData[titleId][version]

def extractCnmt(nsp):
	isOpen = nsp.isOpen()
	try:
		if not isOpen:
			nsp.open(nsp.path, 'rb')

		for n in nsp:
			if not isinstance(n, Nca):
				continue

			if int(n.header.contentType) == 1:
				for p in n:
					for m in p:
						if isinstance(m, Cnmt):
							return m
	except BaseException as e:
		Print.info('exception: %s %s' % (nsp.path, str(e)))
	finally:
		if not isOpen:
			nsp.close()
	return None

def extractNcaMeta(files = []):
	initTitles()
	initFiles()

	loadNcaData()

	global ncaData
	q = {}

	if not files or len(files) == 0:
		for path, nsp in Nsps.files.items():
			if not nsp.path.endswith('.nsp'):  # and not nsp.path.endswith('.xci'):
				continue

			if nsp.isBase() and nsp.getVersionNumber() != 0:
				continue

			if nsp.isDLC():
				continue

			try:
				if hasattr(nsp, 'extractedNcaMeta') and (nsp.extractedNcaMeta or nsp.extractedNcaMeta == 1) or '0100000000000816' in path:
					# Print.info('skipping')
					continue

				title = nsp.title()

				if title and not title.isActive(True):
					continue

				if hasCnmt(nsp.titleId, nsp.version):
					continue

				if Config.limit:
					Config.limitCount += 1

					if Config.limitCount > Config.limit:
						continue

				q[path] = nsp
			except BaseException:
				Print.info('exception: %s' % (path))
				raise
	else:
		for path in files:
			try:
				nsp = Nsps.registerFile(path, registerLUT = False)

				if hasCnmt(nsp.titleId, nsp.version):
					continue

				q[path] = nsp
			except BaseException:
				Print.info('exception: %s' % (path))
				raise

	c = 0
	for path, nsp in tqdm(q.items()):
		if not nsp.path.endswith('.nsp'):  # and not nsp.path.endswith('.xci'):
			continue
		try:
			c += 1

			Print.info('processing %s' % nsp.path)

			nsp.open(path, 'rb')

			if nsp.title().key == '':
				nsp.title().key = None

			if not nsp.title().key:
				Print.info('could not find title key for %s' % nsp.path)

			ncaDataMap = {}
			for n in nsp:
				if not isinstance(n, Nca):
					continue

				ncaId = n._path.split('.')[0]
				data = getNca(ncaId)

				data.contentType = int(n.header.contentType)
				data.isGameCard = n.header.isGameCard
				data.cryptoType = n.header.cryptoType
				data.keyIndex = n.header.keyIndex
				data.size = n.header.size
				data.titleId = n.header.titleId
				data.contentIndex = n.header.contentIndex
				data.sdkVersion = n.header.sdkVersion
				data.cryptoType2 = n.header.cryptoType2
				data.rightsId = n.header.rightsId

				data.buildId = n.buildId()

				if data.rightsId == b'00000000000000000000000000000000':
					data.rightsId = None
				else:
					data.rightsId = data.rightsId.decode()

				ncaDataMap[ncaId.upper()] = data

			# print(ncaDataMap)

			for n in nsp:
				try:
					if not isinstance(n, Nca):
						continue

					ncaId = n._path.split('.')[0]
					data = getNca(ncaId)

					data.contentType = int(n.header.contentType)
					data.isGameCard = n.header.isGameCard
					data.cryptoType = n.header.cryptoType
					data.keyIndex = n.header.keyIndex
					data.size = n.header.size
					data.titleId = n.header.titleId
					data.contentIndex = n.header.contentIndex
					data.sdkVersion = n.header.sdkVersion
					data.cryptoType2 = n.header.cryptoType2
					data.rightsId = n.header.rightsId

					if data.rightsId == b'00000000000000000000000000000000':
						data.rightsId = None
					else:
						data.rightsId = data.rightsId.decode()

					if data.contentType == 1:
						for p in n:
							for m in p:
								if not isinstance(m, Cnmt):
									continue

								cnmt = getCnmt(m.titleId, m.version)
								cnmt.contentEntries = []
								cnmt.metaEntries = []
								cnmt.titleType = m.titleType
								for e in m.contentEntries:
									if not e.ncaId.upper() in ncaDataMap:
										Print.info(ncaDataMap)
										Print.info('nca missing: ' + e.ncaId.upper())
										continue
									mapData = ncaDataMap[e.ncaId.upper()]
									if mapData is not None and (mapData.buildId is not None):
										cnmt.contentEntries.append({'ncaId': e.ncaId, 'type': e.type, 'buildId': mapData.buildId})
									else:
										cnmt.contentEntries.append({'ncaId': e.ncaId, 'type': e.type})

								for e in m.metaEntries:
									cnmt.metaEntries.append({'titleId': e.titleId, 'version': e.version, 'type': e.type, 'install': e.install})

								cnmt.requiredSystemVersion = m.requiredSystemVersion
								cnmt.requiredApplicationVersion = m.requiredApplicationVersion
								cnmt.otherApplicationId = m.otherApplicationId

					# print(str(data.__dict__))
				except BaseException as e:
					Print.info('exception: %s %s' % (path, str(e)))
					continue

			nsp.extractedNcaMeta = True
		except BaseException as e:
			Print.info('exception: %s %s' % (path, str(e)))
		finally:
			nsp.close()

	# save remaining files
	saveNcaData()
	# Nsps.save()

def getName(titleId, version, key=None, path=None):
	initTitles()
	initFiles()
	titleId = titleId.upper()
	nsp = Nsp()

	if path:
		nsp.setPath(os.path.basename(path))

	nsp.titleId = titleId
	nsp.version = version
	nsp.hasValidTicket = True

	if path:
		filename, ext = os.path.splitext(path)
	else:
		ext = '.nsp'

	return os.path.join(Config.paths.nspOut, os.path.basename(nsp.fileName() or ('Untitled [%s][v%d]%s' % (titleId, int(version or 0), ext))))

def scrapeShogun(force=False, region=None):
	if not hasCdn:
		return
	initTitles()
	initFiles()

	if region is None:
		for region in cdn.regions():
			cdn.Shogun.scrapeTitles(region, force=force)
	else:
		cdn.Shogun.scrapeTitles(region, force=force)
	Titles.saveAll()

def scrapeShogunWorker(q, bar, force = False, refresh = False, shogunList = True):
	while True:
		region = q.get()

		if region is None:
			break

		try:
			if shogunList == True:
				cdn.Shogun.scrapeTitles(region, force = force, refresh = refresh, save = False)
			else:
				for language in Config.regionLanguages()[region]:
					#if (Titles.regionModified(region, language) > os.path.getmtime('titledb/versions.json')):
					#	continue
					#if ('%s.%s.json' % (region, language) ) in ['AR.en.json', 'AR.es.json', 'AT.de.json', 'BG.en.json', 'BR.en.json', 'BR.pt.json', 'CA.en.json', 'CL.en.json', 'CL.es.json', 'CN.zh.json', 'CO.en.json', 'CO.es.json', 'CY.en.json', 'CZ.en.json', 'DE.de.json', 'DK.en.json', 'EE.en.json', 'ES.es.json', 'FI.en.json', 'GR.en.json', 'HK.zh.json', 'HR.en.json', 'HU.en.json', 'IE.en.json', 'KR.ko.json', 'LT.en.json', 'LV.en.json', 'MT.en.json', 'MX.en.json', 'NL.nl.json', 'NO.en.json', 'NZ.en.json', 'PE.en.json', 'PE.es.json', 'PL.en.json', 'PT.pt.json', 'RO.en.json', 'RU.ru.json']:
					#	continue
					Print.info('searching %s %s' % (region, language))

					keys = []

					for x in Titles.keys():
						if not x.endswith('800'):
							keys.append(x)
					status = Status.create(len(keys), desc='searching %s %s' % (region, language), unit='')
					for id in keys:
						try:
							l = cdn.Shogun.ids(id, region = region, language = language or 'en', force=(force or shogunList == False))
							status.add(1)

							if not l or len(l) == 0 or len(l['id_pairs']) == 0:
								#Print.info('\tno nsuId\'s found')
								pass
							else:
								#print(l)
								for t in l['id_pairs']:
									#print('\tnsuId: ' + str(t['id']))
									#print(json.dumps(cdn.Shogun.scrapeTitle(t['id'], region=region, language=language, force=True).__dict__))
									cdn.Shogun.scrapeTitle(t['id'], region=region, language=language, force=True)

						except BaseException as e:
							Print.info('shogun worker inner exception: ' + str(e))
							traceback.print_exc(file=sys.stdout)
					status.close()
					Titles.saveRegion(region, language)
		except BaseException as e:
			Print.info('shogun worker exception: ' + str(e))
			traceback.print_exc(file=sys.stdout)

		q.task_done()
		bar.add(1)

def scrapeShogunThreaded(force = False, refresh = False, shogunList = True):
	initTitles()
	initFiles()

	scrapeThreads = []
	numThreads = 8

	if Config.reverse:
		q = queue.LifoQueue()
	else:
		q = queue.Queue()

	for region in cdn.regions():
		q.put(region)

	bar = Status.create(q.qsize(), desc="Scanning shogun...", unit='')

	for i in range(numThreads):
		t = threading.Thread(target=scrapeShogunWorker, args=[q, bar, force, refresh, shogunList])
		t.daemon = True
		t.start()
		scrapeThreads.append(t)

	Print.info('joining shogun queue')
	q.join()

	for i in range(numThreads):
		q.put(None)


	i = 0
	for t in scrapeThreads:
		i += 1
		t.join()
		Print.info('joined thread %d of %d' % (i, len(scrapeThreads)))

	bar.close()

	Print.info('saving titles')
	Titles.save()
	Print.info('titles  saved')

def scrapeShogunUnnamed():
	initTitles()
	initFiles()

	result = {}

	for k, t in Titles.data().items():
		if not t.isDLC:
			continue

		if not t.name and t.baseId != '0100069000078000':
			result[t.baseId] = True

	if not Config.dryRun:
		for id,j in tqdm(result.items()):
			try:
				for region, languages in Config.regionLanguages().items():
					for language in languages:
						t = Titles.getTitleId(id, region, language)

						if t:
							s = cdn.Shogun.scrapeTitle(int(t.nsuId), region=region, language=language, force=False)
							#print(json.dumps(s.__dict__))
			except:
				pass

		for region, languages in Config.regionLanguages().items():
			for language in languages:
				Titles.saveRegion(region, language)

		Titles.save()
	else:
		print(result)

def scanLatestTitleUpdates():
	global versionHistory
	initTitles()
	initFiles()

	now = datetime.datetime.now()
	today = now.strftime("%Y-%m-%d")

	try:
		with open('titledb/versions.json', 'r') as f:
			for titleId, vers in json.loads(f.read()).items():
				for ver, date in vers.items():
					setVersionHistory(titleId, ver, date)
	except BaseException:
		pass

	if not hasCdn:
		return

	for k, i in cdn.hacVersionList().items():
		id = str(k).upper()
		version = str(i)

		if not Titles.contains(id):
			if len(id) != 16:
				Print.info('invalid title id: ' + id)
				continue

		t = Titles.get(id)

		if t.isUpdate:
			setVersionHistory(Title.getBaseId(id), version, today)
		else:
			setVersionHistory(id, version, today)

		if str(t.version) != str(version):
			Print.info('new version detected for %s[%s] v%s' % (t.name or '', t.id or ('0' * 16), str(version)))
			t.setVersion(version, True)

	Titles.save()

	try:
		with open('titledb/versions.json', 'w') as outfile:
			json.dump(versionHistory, outfile, indent=4, sort_keys=True)
	except BaseException as e:
		Print.info(str(e))

def downloadThread(i):
	if not hasCdn:
		return
	Print.info('starting thread ' + str(i))
	global status
	while Config.isRunning and not Titles.queue.empty():
		try:
			id = Titles.queue.shift()
			if id and Titles.contains(id):
				activeDownloads[i] = 1
				t = Titles.get(id)
				path = cdn.downloadTitle(t.id.lower(), None, t.key)

				if path and os.path.isfile(path):
					nsp = Fs.Nsp(path, None)
					nsp.move()
					Nsps.save()

				if status is not None:
					status.add()

				activeDownloads[i] = 0
			else:
				time.sleep(1)
		except KeyboardInterrupt:
			pass
		except BaseException as e:
			Print.error('downloadThread exception: ' + str(e))
			traceback.print_exc(file=sys.stdout)
	activeDownloads[i] = 0
	Print.info('ending thread ' + str(i))

def startDownloadThreads():
	global downloadThreadsStarted
	global activeDownloads

	if downloadThreadsStarted:
		return

	downloadThreadsStarted = True

	initTitles()
	initFiles()

	threads = []
	for i in range(Config.threads):
		activeDownloads.append(0)
		t = threading.Thread(target=downloadThread, args=[i])
		t.daemon = True
		t.start()
		threads.append(t)

def downloadAll(wait=True):
	initTitles()
	initFiles()

	global activeDownloads
	global status

	i = 0
	Print.info('Downloading All')
	try:

		for k, t in Titles.items():
			i = i + 1
			if not t.isActive():
				continue

			if t.isUpdateAvailable():
				if not t.id or t.id == '0' * 16:
					Print.warning('no valid id? id: %s  version: %s' % (str(t.id), str(t.lastestVersion())))
					continue

				Titles.queue.add(t.id)
		Print.info("%d titles scanned, downloading %d" % (i, Titles.queue.size()))

		if Titles.queue.size() > 0:
			Titles.save()
			#status = Status.create(Titles.queue.size(), 'Total Download')

			if Config.threads <= 1:
				activeDownloads.append(1)
				downloadThread(0)
			else:
				startDownloadThreads()
				while wait and (not Titles.queue.empty() or sum(activeDownloads) > 0):
					time.sleep(1)
					Print.info('%d downloads, is empty %d' % (sum(activeDownloads), int(Titles.queue.empty())))
	except KeyboardInterrupt:
		pass
	except BaseException as e:
		Print.error(str(e))

	Print.info('Downloads finished')

	# if status:
	#	status.close()

	Print.info('DownloadAll finished')

def writeJson(data, fileName):
	tmpName = fileName + '.tmp'

	try:
		with open(tmpName, mode='w', encoding="utf-8") as outfile:
			json.dump(data, outfile, indent=4, sort_keys=True)
		try:
			os.unlink(fileName)
		except:
			pass
		os.rename(tmpName, fileName)
	except:
		try:
			os.unlink(tmpName)
		except:
			pass
		raise

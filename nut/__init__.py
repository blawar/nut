from nut import Nsps
from nut import Print
import threading
import time
import colorama
import requests
import queue
import os
from nut import Titles

def refreshRegions():
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

					if not region in title.regions:
						title.regions.append(region)

					if not language in title.languages:
						title.languages.append(language)
	Titles.save()
	
def importRegion(region = 'US', language = 'en'):
	if not region in Config.regionLanguages() or language not in Config.regionLanguages()[region]:
		Print.error('Could not locate %s/%s !' % (region, language))
		return False

	for region2 in Config.regionLanguages():
		for language2 in Config.regionLanguages()[region2]:
			for nsuId, regionTitle in Titles.data(region2, language2).items():
				if not regionTitle.id:
					continue
				title = Titles.get(regionTitle.id, None, None)
				title.importFrom(regionTitle, region2, language2)

	for region2 in Config.regionLanguages():
		for language2 in Config.regionLanguages()[region2]:
			if language2 != language:
				continue
			for nsuId, regionTitle in Titles.data(region2, language2).items():
				if not regionTitle.id:
					continue
				title = Titles.get(regionTitle.id, None, None)
				title.importFrom(regionTitle, region2, language2)


	for nsuId, regionTitle in Titles.data(region, language).items():
		if not regionTitle.id:
			continue

		title = Titles.get(regionTitle.id, None, None)
		title.importFrom(regionTitle, region, language)

	Titles.loadTxtDatabases()
	Titles.save()

isInitFiles = False
def initFiles():
	global isInitFiles
	if isInitFiles:
		return

	isInitFiles = True

	Nsps.load()
	
isInitTitles = False

def initTitles():
	global isInitTitles
	if isInitTitles:
		return

	isInitTitles = True

	Titles.load()

	Nsps.load()
	Titles.queue.load()

global hasScanned
hasScanned = False

def scan(scanTitles = False):
	global hasScanned

	hasScanned = True
	
	if scanTitles == True:
		initTitles()

		refreshRegions()
		importRegion(Config.region, Config.language)
		
	initFiles()
	
	r = 0

	for path in Config.paths.scan:
		r += Nsps.scan(path)
	Nsps.save()
	return r
	
global status
status = None

def makeRequest(method, url, certificate='', hdArgs={}):
	reqHd = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
		'Accept-Encoding': 'gzip, deflate',
		'Accept': '*/*',
		'Connection': 'keep-alive'
	}
	reqHd.update(hdArgs)

	r = requests.request(method, url, headers=reqHd, verify=False, stream=True)

	if r.status_code == 403:
		raise IOError('Request rejected by server!')

	return r

def downloadFile(url, fPath):
	fName = os.path.basename(fPath).split()[0]

	if os.path.exists(fPath):
		dlded = os.path.getsize(fPath)
		r = makeRequest('GET', url, hdArgs={'Range': 'bytes=%s-' % dlded})

		if r.headers.get('Server') != 'openresty/1.9.7.4':
			Print.info('Download is already complete, skipping!')
			return fPath
		elif r.headers.get('Content-Range') == None:  # CDN doesn't return a range if request >= filesize
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

	#if fSize != 0 and dlded != fSize:
	#	raise ValueError('Downloaded data is not as big as expected (%s/%s)!' % (dlded, fSize))

	f.close()
	Print.debug('\r\nSaved to %s!' % f.name)
	return fPath


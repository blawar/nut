from nut import Titles
from nut import Title
from nut import Nsps
from nut import Print
import threading
import time
import colorama
import requests
import queue
import os
import Fs

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

isInitTitles = False

def initTitles():
	global isInitTitles
	if isInitTitles:
		return

	isInitTitles = True

	Titles.load()

	Nsps.load()
	Titles.queue.load()

isInitFiles = False
def initFiles():
	global isInitFiles
	if isInitFiles:
		return

	isInitFiles = True

	Nsps.load()

global hasScanned
hasScanned = False

def scan():
	global hasScanned

	#if hasScanned:
	#	return
	hasScanned = True
	initTitles()
	initFiles()

	
	refreshRegions()
	importRegion(Config.region, Config.language)

	r = Nsps.scan(Config.paths.scan)
	Titles.save()
	return r

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

def organize():
	initTitles()
	initFiles()

	#scan()
	Print.info('organizing')
	for k, f in Nsps.files.items():
		#print('moving ' + f.path)
		#Print.info(str(f.hasValidTicket) +' = ' + f.path)
		f.move()

	for id, t in Titles.data().items():
		files = t.getFiles()
		if len(files) > 1:
			#Print.info("%d - %s - %s" % (len(files), t.id, t.name))
			latest = t.getLatestFile()

			if not latest:
				continue

			for f in files:
				if f.path != latest.path:
					f.moveDupe()

	Print.info('removing empty directories')
	Nsps.removeEmptyDir('.', False)
	Nsps.save()

def export(file, cols = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'baseName', 'name', 'version', 'region']):
	initTitles()
	Titles.export(file, cols)

	
global status
status = None

global scrapeThreads
scrapeThreads = 16


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
				Print.info("\nError decoding url: ", e)
				return

		r = requests.get(url)
		r.encoding = 'utf-8-sig'

		if r.status_code == 200:
			try:
				m = re.search(r'<a href="([^"]*)">Proceed</a>', r.text)
				if m:
					return updateDb(m.group(1), c)
			except:
				pass
			Titles.loadTitleBuffer(r.text, False)
		else:
			Print.info('Error updating database: ', repr(r))
			
	except Exception as e:
		Print.info('Error downloading:' + str(e))



from nut import Titles
from nut import Title
from nut import Nsps
from nut import Print
import threading
import time
import colorama
import requests
import queue
import cdn
import os
import Fs
import CDNSP

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

def scrapeShogun():
	initTitles()
	initFiles()

	for region in cdn.regions():				
		cdn.Shogun.scrapeTitles(region)
	Titles.saveAll()


def scrapeShogunWorker(q):
	while True:
		region = q.get()

		if region is None:
			break

		cdn.Shogun.scrapeTitles(region)

		q.task_done()

def scrapeShogunThreaded():
	initTitles()
	initFiles()

	scrapeThreads = []
	numThreads = 8

	q = queue.Queue()

	for region in cdn.regions():
		q.put(region)

	for i in range(numThreads):
		t = threading.Thread(target=scrapeShogunWorker, args=[q])
		t.daemon = True
		t.start()
		scrapeThreads.append(t)

	q.join()

	for i in range(numThreads):
		q.put(None)

	for t in scrapeThreads:
		t.join()
	Titles.saveAll()

def updateVersions(force = True):
	initTitles()
	initFiles()

	i = 0
	for k,t in Titles.items():
		if force or t.version == None:
			if (t.isDLC or t.isUpdate or Config.download.base) and (not t.isDLC or Config.download.DLC) and (not t.isDemo or Config.download.demo) and (not t.isUpdate or Config.download.update) and (t.key or Config.download.sansTitleKey) and (len(Config.titleWhitelist) == 0 or t.id in Config.titleWhitelist) and t.id not in Config.titleBlacklist:
				v = t.lastestVersion(True)
				Print.info("%s[%s] v = %s" % (str(t.name), str(t.id), str(v)) )
			
				i = i + 1
				if i % 20 == 0:
					Titles.save()
			
	for t in list(Titles.data().values()):
		if not t.isUpdate and not t.isDLC and t.updateId and t.updateId and not Titles.contains(t.updateId):
			u = Title()
			u.setId(t.updateId)
			
			if u.lastestVersion():
				Titles.set(t.updateId, u)
				
				Print.info("%s[%s] FOUND" % (str(t.name), str(u.id)) )
				
				i = i + 1
				if i % 20 == 0:
					Titles.save()
					
	Titles.save()
	
global status
status = None

global scrapeThreads
scrapeThreads = 16

def scrapeThread(id, delta = True):
	size = len(Titles.titles) // scrapeThreads
	st = Status.create(size, 'Thread ' + str(id))
	for i,titleId in enumerate(Titles.titles.keys()):
		try:
			if (i - id) % scrapeThreads == 0:
				Titles.get(titleId).scrape(delta)
				st.add()
		except BaseException as e:
			Print.error(str(e))
	st.close()

def scanLatestTitleUpdates():
	initTitles()
	initFiles()

	for k,i in CDNSP.get_versionUpdates().items():
		id = str(k).upper()
		version = str(i)
		
		if not Titles.contains(id):
			if len(id) != 16:
				Print.info('invalid title id: ' + id)
				continue
			continue
			t = Title()
			t.setId(id)
			Titles.set(id, t)
			Print.info('Found new title id: ' + str(id))
			
		t = Titles.get(id)
		if str(t.version) != str(version):
			Print.info('new version detected for %s[%s] v%s' % (t.name or '', t.id or ('0' * 16), str(version)))
			t.setVersion(version, True)
			
	Titles.save()
	
global activeDownloads
activeDownloads = []

def downloadThread(i):
	Print.info('starting thread ' + str(i))
	global status
	while Config.isRunning:
		try:
			id = Titles.queue.shift()
			if id and Titles.contains(id):
				activeDownloads[i] = 1
				t = Titles.get(id)
				path = CDNSP.download_game(t.id.lower(), t.lastestVersion(), t.key, True, '', True)

				if os.path.isfile(path):
					nsp = Fs.Nsp(path, None)
					nsp.move()
					Nsps.files[nsp.path] = nsp
					Nsps.save()
					status.add()
				activeDownloads[i] = 0
			else:
				time.sleep(1)
		except KeyboardInterrupt:
			pass
		except BaseException as e:
			Print.error(str(e))
	activeDownloads[i] = 0
	Print.info('ending thread ' + str(i))
	
global downloadThreadsStarted
downloadThreadsStarted = False

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

def downloadAll(wait = True):
	initTitles()
	initFiles()

	global activeDownloads
	global status

	try:

		for k,t in Titles.items():
			if t.isUpdateAvailable() and (t.isDLC or t.isUpdate or Config.download.base) and (not t.isDLC or Config.download.DLC) and (not t.isDemo or Config.download.demo) and (not t.isUpdate or Config.download.update) and (t.key or Config.download.sansTitleKey) and (len(Config.titleWhitelist) == 0 or t.id in Config.titleWhitelist) and t.id not in Config.titleBlacklist:
				if not t.id or t.id == '0' * 16 or (t.isUpdate and t.lastestVersion() in [None, '0']):
					#Print.warning('no valid id? ' + str(t.path))
					continue
				
				if not t.lastestVersion():
					Print.info('Could not get version for ' + str(t.name) + ' [' + str(t.id) + ']')
					continue

				Titles.queue.add(t.id)
		Titles.save()
		status = Status.create(Titles.queue.size(), 'Total Download')
		startDownloadThreads()
		while wait and (not Titles.queue.empty() or sum(activeDownloads) > 0):
			time.sleep(1)
	except KeyboardInterrupt:
		pass
	except BaseException as e:
		Print.error(str(e))

	if status:
		status.close()

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
		raise

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
import Titles
import json
import Titles
import Status
import Nsps
import Print
import Server
import Config
import Hex
import socket
import struct
import time
import nut
import cdn
import blockchain

try:
	from PIL import Image
except ImportError:
	import Image
import Server
import os

def success(request, response, s):
	response.write(json.dumps({'success': True, 'result': s}))

def error(request, response, s):
	response.write(json.dumps({'success': False, 'result': s}))

def getUser(request, response):
	response.write(json.dumps(request.user.__dict__))

def getSearch(request, response):
	o = []

	region = request.query.get('region')
	publisher = request.query.get('publisher')

	dlc = request.query.get('dlc')
	if dlc:
		dlc = int(dlc[0])

	update = request.query.get('update')
	if update:
		update = int(update[0])

	demo = request.query.get('demo')
	if demo:
		demo = int(demo[0])

	for k, t in Titles.items():
		f = t.getLatestFile()
		if f and f.hasValidTicket and (region == None or t.region in region) and (dlc == None or t.isDLC == dlc) and (update == None or t.isUpdate == update) and (demo == None or t.isDemo == demo) and (publisher == None or t.publisher in publisher):
			o.append({'id': t.id, 'name': t.name, 'version': int(f.version) if f.version else None , 'region': t.region,'size': f.getFileSize(), 'mtime': f.getFileModified() })
	response.write(json.dumps(o))

def getTitles(request, response):
	o = []
	map = ['id', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region', 'baseId']
	for k, t in Titles.items():
		o.append(t.__dict__)
	response.write(json.dumps(o))

def getTitleImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]
	try:
		width = int(request.bits[3])
	except:
		return Server.Response404(request, response)


	if width < 32 or width > 1024:
		return Server.Response404(request, response)

	if not Titles.contains(id):
		return Server.Response404(request, response)

	path = Titles.get(id).iconFile(width) or Titles.get(id).frontBoxArtFile(width)

	if not path:
		return Server.Response404(request, response)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getBannerImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]

	if not Titles.contains(id):
		return Server.Response404(request, response)

	path = Titles.get(id).bannerFile()

	if not path:
		return Server.Response404(request, response)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getFrontArtBoxImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]
	#width = int(request.bits[3])

	#if width < 32 or width > 512:
	#	return Server.Response404(request, response)

	if not Titles.contains(id):
		return Server.Response404(request, response)

	path = Titles.get(id).frontBoxArtFile()

	if not path:
		return Server.Response404(request, response)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getScreenshotImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]

	try:
		i = int(request.bits[3])
	except:
		return Server.Response404(request, response)

	if not Titles.contains(id):
		return Server.Response404(request, response)

	path = Titles.get(id).screenshotFile(i)

	if not path:
		return Server.Response404(request, response)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getPreload(request, response):
	Titles.queue.add(request.bits[2])
	response.write(json.dumps({'success': True}))

def getInstall(request, response):
	nsp = Nsps.getByTitleId(request.bits[2])

	try:
		url = ('%s:%s@%s:%d/api/download/%s/title.nsp' % (request.user.id, request.user.password, Config.server.hostname, Config.server.port, request.bits[2]))
		Print.info('Installing ' + url)
		file_list_payloadBytes = url.encode('ascii')

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		#sock.settimeout(1)
		sock.connect((request.user.switchHost, request.user.switchPort))
		#sock.settimeout(99999)

		sock.sendall(struct.pack('!L', len(file_list_payloadBytes)) + file_list_payloadBytes)
		while len(sock.recv(1)) < 1:
			time.sleep(0.05)
		sock.close()
		response.write(json.dumps({'success': True, 'message': 'install successful'}))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))

def getInfo(request, response):
	try:
		nsp = Nsps.getByTitleId(request.bits[2])
		t = Titles.get(request.bits[2]).__dict__
		t['size'] = nsp.getFileSize();
		t['mtime'] = nsp.getFileModified();
		response.write(json.dumps(t))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))

def getDownload(request, response, start = None, end = None):
	try:
		nsp = Nsps.getByTitleId(request.bits[2])
		response.attachFile(nsp.titleId + '.nsp')

		if len(request.bits) >= 5:
			start = int(request.bits[3])
			end = int(request.bits[4])
	
		chunkSize = 0x400000

		with open(nsp.path, "rb") as f:
			f.seek(0, 2)
			size = f.tell()
			if 'Range' in request.headers:
				start, end = request.headers.get('Range').strip().strip('bytes=').split('-')

				if end == '':
					end = size - 1
				else:
					end = int(end) + 1

				if start == '':
					start = size - end
				else:
					start = int(start)

				if start >= size or end > size or start < 0 or end <= 0:
					return Server.Response400(request, response, 'Invalid range request')

				response.setStatus(206)

			else:
				if start == None:
					start = 0
				if end == None:
					end = size

			if end >= size:
				end = size

				if end <= start:
					response.write(b'')
					return

			print('ranged request for %d - %d' % (start, end))
			f.seek(start, 0)

			response.setMime(nsp.path)
			response.setHeader('Accept-Ranges', 'bytes')
			response.setHeader('Content-Range', 'bytes %s-%s/%s' % (start, end-1, size))
			response.setHeader('Content-Length', str(end - start))
			#Print.info(response.headers['Content-Range'])
			response.sendHeader()

			if not response.head:
				size = end - start

				i = 0

				while i < size:
					chunk = f.read(min(size-i, chunkSize))
					i += len(chunk)

					if chunk:
						pass
						response.write(chunk)
					else:
						break
	except BaseException as e:
		Print.error('NSP download exception: ' + str(e))
	if response.bytesSent == 0:
		response.write(b'')

def getQueue(request, response):
	r = Status.data().copy()
	q = Titles.queue.get().copy()
	i = Titles.queue.i
	while i < len(q):
		r.append({'id': q[i], 'i': 0, 'size': 0, 'elapsed': 0, 'speed': 0 })
		i += 1
	response.write(json.dumps(r))

def getTitleUpdates(request, response):
	r = {}
	for path, nsp in Nsps.files.items():
		data = nsp.isUpdateAvailable()
		if data:
			r[data['id']] = data
	response.write(json.dumps(r))

def getFiles(request, response):
	r = {}
	for path, nsp in Nsps.files.items():
		if Titles.contains(nsp.titleId):
			title = Titles.get(nsp.titleId)
			if not title.baseId in r:
				r[title.baseId] = {'base': [], 'dlc': [], 'update': []}
			if title.isDLC:
				r[title.baseId]['dlc'].append(nsp.dict())
			elif title.isUpdate:
				r[title.baseId]['update'].append(nsp.dict())
			else:
				r[title.baseId]['base'].append(nsp.dict())
	response.write(json.dumps(r))

def getScan(request, response):
	success(request, response, nut.scan())

def getOrganize(request, response):
	nut.organize()
	success(request, response, "fin")

def getUpdateDb(request, response):
	for url in Config.titleUrls:
		nut.updateDb(url)
	Titles.loadTxtDatabases()
	Titles.save()
	return success(request, response, "Fin")

def getCdnDownloadAll(request, response):
	nut.downloadAll()
	return success(request, response, "Fin")

def getCdnDownload(request, response):
	for id in request.bits[2:]:
		nut.download(id)
	return success(request, response, "Fin")

def getExport(request, response):
	if len(request.bits) < 3:
		return Server.Response500(request, response)
	
	if len(request.bits) == 3:
		nut.export(request.bits[2])
	else:
		nut.export(request.bits[2], request.bits[3:])

	return success(request, response, "Fin")

def getImportRegions(request, response):
	nut.importRegion(request.bits[2], request.bits[3])

	return success(request, response, "Fin")

def getRegions(request, response):
	response.write(json.dumps(Config.regionLanguages()))


def getUpdateLatest(request, response):
	nut.scanLatestTitleUpdates()
	return success(request, response, "Fin")

def getUpdateAllVersions(request, response):
	if len(request.bits) >= 3 and int(request.bits[2]) > 0:
		nut.updateVersions(True)
	else:
		nut.updateVersions(False)
	return success(request, response, "Fin")

def scrapeShogun(request, response):
	nut.scrapeShogun()
	return success(request, response, "Fin")

def submitKey(request, response):
	titleId = request.bits[2]
	titleKey = request.bits[3]

	try:
		if blockchain.blockchain.suggest(titleId, titleKey) == True:
			return success(request, response, "Key successfully added")
		else:
			return error(request, response, "Key validation failed")
	except LookupError as e:
		error(request, response, str(e))
	except OSError as e:
		error(request, response, str(e))
	except BaseException as e:
		error(request, response, str(e))
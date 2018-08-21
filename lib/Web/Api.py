import Titles
import json
import Titles
import Status
import Nsps
import Print

try:
	from PIL import Image
except ImportError:
	import Image
import Server
import os

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
	width = int(request.bits[3])

	if width < 32 or width > 1024:
		return Server.Response404(request, response)

	path = Titles.get(id).iconFile(width) or Titles.get(id).frontBoxArtFile(width)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getBannerImage(request, response):
	if len(request.bits) < 2:
		return Server.Response404(request, response)

	id = request.bits[2]

	path = Titles.get(id).bannerFile()

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

	path = Titles.get(id).frontBoxArtFile()

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
	i = int(request.bits[3])


	path = Titles.get(id).screenshotFile(i)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getPreload(request, response):
	Titles.queue.add(request.bits[2])
	response.write(json.dumps({'success': True}))

def getDownload(request, response):
	nsp = Nsps.getByTitleId(request.bits[2])
	Print.info('Downloading ' + nsp.path)
	response.attachFile(os.path.basename(nsp.path))
	
	chunkSize = 0x10000

	with open(nsp.path, "rb") as f:
		while True:
			chunk = f.read(chunkSize)
			if chunk:
				pass
				response.write(chunk)
			else:
				break

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
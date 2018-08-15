import Titles
import json
import Titles
import Status
import Nsps

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

	if width < 32 or width > 512:
		return Server.Response404(request, response)

	path = Titles.get(id).iconFile(width)

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

def getDownload(request, response):
	Titles.queue.add(request.bits[2])
	response.write(json.dumps({'success': True}))

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
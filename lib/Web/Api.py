import Titles
import json
import nut

try:
	from PIL import Image
except ImportError:
	import Image
import Server
import os

def getTitles(request, response):
	o = []
	map = ['id', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']
	for k, t in Titles.items():
		o.append(t.dict())
	response.write(json.dumps(o))

def getTitleImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	width = int(request.bits[3])

	if width < 32 or width > 512:
		return Server.Response404(request, response)

	fileName = 'logo.jpg'
	srcPath = os.path.abspath('public_html/images/titles/' + request.bits[2] + '/logo.jpg')
	if not os.path.isfile(srcPath):
		return Server.Response500(request, response)

	base = os.path.abspath('public_html/images/titles/cache/' + request.bits[2] + '/')
	path = os.path.join(base, fileName)

	if not os.path.isfile(path):
		os.makedirs(base, exist_ok=True)
		im = Image.open(srcPath)
		out = im.resize((width, width), Image.ANTIALIAS)
		out.save(path, quality=100)

	response.setMime(path)
	response.headers['Cache-Control'] = 'max-age=31536000'

	if os.path.isfile(path):
		with open(path, 'rb') as f:
			response.write(f.read())

	return Server.Response500(request, response)

def getQueue(request, response):
	response.write(json.dumps(nut.downloadQueue.get()))
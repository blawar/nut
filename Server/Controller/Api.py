from nut import Titles
import json
from nut import Titles
from nut import Status
from nut import Nsps
from nut import Print
import Server
from nut import Config
from nut import Hex
import socket
import struct
import time
import nut
from nut import blockchain
import urllib.parse
import requests
import sys
from bs4 import BeautifulSoup
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import hashlib
import traceback
import Fs.driver
import Fs.driver.init

try:
	from PIL import Image
except BaseException:
	import Image

import Server
import os

SCOPES = ['https://www.googleapis.com/auth/drive']

def makeRequest(method, url, hdArgs={}, start=None, end=None, accept='*/*'):
	if start is None:
		reqHd = {
			'Accept': accept,
			'Connection': None,
			'Accept-Encoding': None,
		}
	else:
		reqHd = {
			'Accept': accept,
			'Connection': None,
			'Accept-Encoding': None,
			'Range': 'bytes=%d-%d' % (start, end-1),
		}

	reqHd.update(hdArgs)

	r = requests.request(
		method,
		url,
		headers=reqHd,
		verify=False,
		stream=True,
		timeout=15
	)

	Print.debug('%s %s %s' % (method, str(r.status_code), url))
	Print.debug(r.request.headers)

	if r.status_code == 403:
		raise IOError('Forbidden ' + r.text)

	return r

def success(request, response, s):
	response.headers['Content-Type'] = 'application/json'
	response.headers['Access-Control-Allow-Origin'] = '*'
	response.write(json.dumps({'success': True, 'result': s}))

def error(request, response, s):
	response.headers['Content-Type'] = 'application/json'
	response.headers['Access-Control-Allow-Origin'] = '*'
	response.write(json.dumps({'success': False, 'result': s}))

def getSearch(request, response):
	nsp = []
	nsx = []
	nsz = []
	xci = []
	xcz = []

	for _, f in Nsps.files.items():
		name = f.fileName()
		if name is None:
			continue

		if name.endswith('.nsp'):
			nsp.append({
				'id': f.titleId,
				'name': f.baseName(),
				'size': f.getFileSize(),
				'version': int(f.version) if f.version else None
			})
		elif name.endswith('.nsz'):
			nsz.append({
				'id': f.titleId,
				'name': f.baseName(),
				'size': f.getFileSize(),
				'version': int(f.version) if f.version else None
			})
		elif name.endswith('.nsx'):
			nsx.append({
				'id': f.titleId,
				'name': f.baseName(),
				'size': f.getFileSize(),
				'version': int(f.version) if f.version else None
			})
		elif name.endswith('.xci'):
			xci.append({
				'id': f.titleId,
				'name': f.baseName(),
				'size': f.getFileSize(),
				'version': int(f.version) if f.version else None
			})
		elif name.endswith('.xcz'):
			xcz.append({
				'id': f.titleId,
				'name': f.baseName(),
				'size': f.getFileSize(),
				'version': int(f.version) if f.version else None
			})

	o = nsz + nsp + xcz + xci + nsx
	response.headers['Content-Type'] = 'application/json'
	response.write(json.dumps(o))

def getTitles(request, response):
	o = []
	for k, t in Titles.items():
		o.append(t.__dict__)
	response.headers['Content-Type'] = 'application/json'
	response.write(json.dumps(o))

def getTitleImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]
	try:
		width = int(request.bits[3])
	except BaseException:
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
			return

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
			return

	return Server.Response500(request, response)

def getFrontArtBoxImage(request, response):
	return getTitleImage(request, response)

def getScreenshotImage(request, response):
	if len(request.bits) < 3:
		return Server.Response404(request, response)

	id = request.bits[2]

	try:
		i = int(request.bits[3])
	except BaseException:
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
			return

	return Server.Response500(request, response)

def getInfo(request, response):
	try:
		response.headers['Content-Type'] = 'application/json'
		nsp = Nsps.getByTitleId(request.bits[2])
		t = Titles.get(request.bits[2]).__dict__
		t['size'] = nsp.getFileSize()
		t['mtime'] = nsp.getFileModified()
		response.write(json.dumps(t))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))

def getOffsetAndSize(start, end, size=None):
	if start is None and end is None:
		return [None, size]

	if start is not None:
		start = int(start)
	else:
		start = 0

	if end is None:
		return [start, None]

	end = int(end)

	if size is not None:
		if start and end:
			if end is None:
				end = size - 1
			else:
				end = int(end)

			if start is None:
				start = size - end
			else:
				start = int(start)

			if start >= size or start < 0 or end <= 0:
				return [start, None]
		else:
			if start is None:
				start = 0
			if end is None:
				end = size

		if end >= size:
			end = size

	size = end - start
	return [start, size]

class Progress:
	def __init__(self, response, f, size = None):
		self.response = response
		self.f = f
		self.status = Status.create(size or f.size, 'Downloading ' + os.path.basename(f.url))
		self.buffer = b''
		self.chunk_size = 0x100000 * 16

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def flush(self):
		if len(self.buffer) > 0:
			self.response.write(self.buffer)
			self.status.add(len(self.buffer))
			self.buffer = b''


	def close(self):
		self.flush()

		if self.status is not None:
			self.status.close()
			self.status = None

	def write(self, chunk):
		chunk_left = self.chunk_size - len(self.buffer)

		if len(chunk) < chunk_left:
			self.buffer += chunk
		else:
			self.buffer += chunk[0:chunk_left]
			self.flush()

			self.write(chunk[chunk_left:])


def serveFile(response, path, filename=None, start=None, end=None):
	with Fs.driver.openFile(path) as f:
		try:
			start, size = getOffsetAndSize(start, end, f.size)

			response.setMime(path)

			if start and end:
				end = int(end)
				start = int(start)

				response.setStatus(206)
				response.setHeader('Accept-Ranges', 'bytes')
				response.setHeader('Content-Range', 'bytes %s-%s/%s' % (start, end-1, size))

			response.setHeader('Content-Length', str(size))
			response.sendHeader()

			if not response.head:
				with Progress(response=response, f=f, size = size) as progress:
					f.chunk(progress.write, offset=start, size=size)
		except BaseException as e:
			Print.error('File download exception: ' + str(e))

		if response.bytesSent == 0:
			response.write(b'')

def getDownload(request, response, start=None, end=None):
	try:
		nsp = Nsps.getByTitleId(request.bits[2])
		response.attachFile(nsp.titleId + '.nsp')

		if len(request.bits) >= 5:
			start = int(request.bits[-2])
			end = int(request.bits[-1])

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

				if start >= size or start < 0 or end <= 0:
					return Server.Response400(request, response, 'Invalid range request %d - %d' % (start, end))

				response.setStatus(206)

			else:
				if start is None:
					start = 0
				if end is None:
					end = size

			if end >= size:
				end = size

				if end <= start:
					response.write(b'')
					return

			Print.info('ranged request for %d - %d' % (start, end))
			f.seek(start, 0)

			response.setMime(nsp.path)
			response.setHeader('Accept-Ranges', 'bytes')
			response.setHeader('Content-Range', 'bytes %s-%s/%s' % (start, end-1, size))
			response.setHeader('Content-Length', str(end - start))
			response.sendHeader()

			if not response.head:
				size = end - start

				i = 0
				status = Status.create(size, 'Downloading ' + os.path.basename(nsp.path))

				while i < size:
					chunk = f.read(min(size-i, chunkSize))
					i += len(chunk)

					status.add(len(chunk))

					if chunk:
						pass
						response.write(chunk)
					else:
						break
				status.close()
	except BaseException as e:
		Print.error('NSP download exception: ' + str(e))
	if response.bytesSent == 0:
		response.write(b'')


def isWindows():
	if "win" in sys.platform[:3].lower():
		return True
	else:
		return False

def listDrives():
	drives = []
	for label, _ in Config.paths.mapping().items():
		drives.append(label)

	if not Config.server.enableLocalDriveAccess:
		return drives

	if isWindows():
		import string
		import ctypes
		kernel32 = ctypes.windll.kernel32
		bitmask = kernel32.GetLogicalDrives()
		for letter in string.ascii_uppercase:
			if bitmask & 1:
				drives.append(letter)
			bitmask >>= 1
		return drives

	drives.append('root')

	return drives

def isInConfiguredPath(path):
	path = path.lower().replace('\\', '/')

	for label, value in Config.paths.mapping().items():
		value = value.lower().replace('\\', '/')

		if value and (path == value or path.startswith(value.lower())):
			return True

	return False

def isBlockedPath(path):
	if not Config.server.enableLocalDriveAccess:
		if '..' in path:
			return True

		if not isInConfiguredPath(path):
			return True

	return False

def isBlocked(path):
	path = path.lower()

	if isBlockedPath(path):
		return True

	whitelist = [
		'.nro',
		'.xci',
		'.nsp',
		'.nsx',
		'.nsz',
		'.xcz',
		'.conf',
		'.json',
		'.db',
		'.tfl',
		'.jpg',
		'.gif',
		'.png',
		'.bin',
		'.enc',
		'.ini',
		'.ips',
		'.txt',
		'.pdf',
		'.tik',
		'.nca',
		'.ncz',
		'.cert'
	]

	for ext in whitelist:
		if path.endswith(ext):
			return False

	return True

def getDirectoryList(request, response):
	try:
		response.headers['Content-Type'] = 'application/json'

		if len(request.bits) > 2:
			virtualDir = request.bits[2]
			path = request.bits[2] + ':/'
			for i in request.bits[3:]:
				path = Fs.driver.join(path, i)
		else:
			virtualDir = ''
			path = ''

		path = Fs.driver.cleanPath(path)

		r = {'dirs': [], 'files': []}

		if not path:
			for d in listDrives():
				r['dirs'].append({'name': d})
			response.write(json.dumps(r))
			return

		if isBlockedPath(path):
			raise IOError('forbidden')

		for f in Fs.driver.openDir(path).ls():

			if not f.isFile():
				r['dirs'].append({'name': f.baseName()})
			else:
				if not isBlocked(f.url):
					r['files'].append({
						'name': f.baseName(),
						'size': f.size,
						'mtime': f.mtime()
					})

		response.write(json.dumps(r))
	except BaseException as e:
		traceback.print_exc(file=sys.stdout)
		raise IOError('dir list access denied: ' + str(e))


def downloadProxyFile(url, response, start=None, end=None, headers={}):
	bytes = 0

	r = makeRequest('GET', url, start=start, end=end, hdArgs=headers)
	size = int(r.headers.get('Content-Length'))

	chunkSize = 0x100000

	if size >= 10000:

		for chunk in r.iter_content(chunkSize):
			response.write(chunk)
			bytes += len(chunk)

			if not Config.isRunning:
				break
	else:
		response.write(r.content)
		bytes += len(r.content)

	if size != 0 and bytes != size:
		raise ValueError(
			f'Downloaded data is not as big as expected ({bytes}/{size})!'
		)

	return bytes


def getFile(request, response, start=None, end=None):
	try:
		path = ''

		if len(request.bits) > 2:
			virtualDir = request.bits[2]
		else:
			virtualDir = ''

		path = virtualDir + ':/'
		for i in request.bits[3:]:
			path = Fs.driver.join(path, i)
		path = Fs.driver.cleanPath(path)

		if isBlocked(path):
			raise IOError('access denied')

		if 'Range' in request.headers:
			_range = request.headers.get('Range').strip()
			start, end = _range.strip('bytes=').split('-')

			if end != '':
				end = int(end) + 1

			if start != '':
				start = int(start)

		return serveFile(response, path, start=start, end=end)
	except BaseException:
		raise IOError('file read access denied')

def getFileSize(request, response):
	response.headers['Content-Type'] = 'application/json'
	t = {}

	path = ''

	if len(request.bits) > 2:
		virtualDir = request.bits[2]
	else:
		virtualDir = ''

	path = virtualDir + ':/'
	for i in request.bits[3:]:
		path = Fs.driver.join(path, i)
	path = Fs.driver.cleanPath(path)

	try:
		t['size'] = os.path.getsize(path)
		t['mtime'] = os.path.getmtime(path)
		response.write(json.dumps(t))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))

def getQueue(request, response):
	response.headers['Content-Type'] = 'application/json'
	response.write(json.dumps([]))

def getTitleUpdates(request, response):
	r = {}
	for path, nsp in Nsps.files.items():
		data = nsp.isUpdateAvailable()
		if data:
			r[data['id']] = data

	response.headers['Content-Type'] = 'application/json'
	response.write(json.dumps(r))

def getFiles(request, response):
	response.headers['Content-Type'] = 'application/json'
	r = {}
	for path, nsp in Nsps.files.items():
		if Titles.contains(nsp.titleId):
			title = Titles.get(nsp.titleId)
			if title.baseId not in r:
				r[title.baseId] = {'base': [], 'dlc': [], 'update': []}
			if title.isDLC:
				r[title.baseId]['dlc'].append(nsp.dict())
			elif title.isUpdate:
				r[title.baseId]['update'].append(nsp.dict())
			else:
				r[title.baseId]['base'].append(nsp.dict())
	response.write(json.dumps(r))


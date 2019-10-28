import json
from nut import Status
from nut import Nsps
from nut import Print
import Server
from nut import Config
import socket
import struct
import time
import nut
import urllib.parse
import requests
import sys
from bs4 import BeautifulSoup
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io
import hashlib

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.readonly']

try:
	from PIL import Image
except ImportError:
	import Image
import Server
import os

def makeRequest(method, url, hdArgs={}, start = None, end = None, accept = '*/*'):
	if start is None:
		reqHd = {
			'Accept': accept,
			'Connection': None,
			'Accept-Encoding': None,
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
		}
	else:
		reqHd = {
			'Accept': accept,
			'Connection': None,
			'Accept-Encoding': None,
			'Range': 'bytes=%d-%d' % (start, end-1),
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
		}

	reqHd.update(hdArgs)

	r = requests.request(method, url, headers=reqHd, verify=False, stream=True, timeout=15)

	Print.debug('%s %s %s' % (method, str(r.status_code), url))
	Print.debug(r.request.headers)
	#data = dump.dump_all(r)
	#print(data.decode('utf-8'))

	if r.status_code == 403:
		raise IOError('Forbidden ' + r.text)

	return r

def success(request, response, s):
	response.write(json.dumps({'success': True, 'result': s}))

def error(request, response, s):
	response.write(json.dumps({'success': False, 'result': s}))

def getUser(request, response):
	response.write(json.dumps(request.user.__dict__))

def getSearch(request, response):
	nsp = []
	nsx = []
	nsz = []

	for path, f in Nsps.files.items():
		name = f.fileName()
		if name.endswith('.nsp'):
			nsp.append({'id': f.titleId, 'name': f.fileName(), 'version': int(f.version) if f.version else None })
		elif name.endswith('.nsz'):
			nsz.append({'id': f.titleId, 'name': f.fileName(), 'version': int(f.version) if f.version else None })
		elif name.endswith('.nsx'):
			nsx.append({'id': f.titleId, 'name': f.fileName(), 'version': int(f.version) if f.version else None })
		
	o = nsz + nsp + nsx
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
	return getTitleImage(request, response)
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

def getUpdateDb(request, response): # stub for doge
	return success(request, response, "Fin")

def getInfo(request, response):
	try:
		nsp = Nsps.getByTitleId(request.bits[2])
		t = {'id': request.bits[2]}
		t['size'] = nsp.getFileSize();
		t['mtime'] = nsp.getFileModified();
		response.write(json.dumps(t))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))

def serveFile(response, path, filename = None, start = None, end = None):
	try:
		if start is not None:
			start = int(start)

		if end is not None:
			end = int(end)

		if not filename:
			filename = os.path.basename(path)

		response.attachFile(filename)
	
		chunkSize = 0x400000

		with open(path, "rb") as f:
			f.seek(0, 2)
			size = f.tell()
			if start and end:
				if end == None:
					end = size - 1
				else:
					end = int(end)

				if start == None:
					start = size - end
				else:
					start = int(start)

				if start >= size or start < 0 or end <= 0:
					return Server.Response400(request, response, 'Invalid range request %d - %d' % (start, end))

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

			response.setMime(path)
			response.setHeader('Accept-Ranges', 'bytes')
			response.setHeader('Content-Range', 'bytes %s-%s/%s' % (start, end-1, size))
			response.setHeader('Content-Length', str(end - start))
			response.sendHeader()

			if not response.head:
				size = end - start

				i = 0
				status = Status.create(size, 'Downloading ' + os.path.basename(path))

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
		Print.error('File download exception: ' + str(e))

	if response.bytesSent == 0:
		response.write(b'')

def getDownload(request, response, start = None, end = None):
	try:
		nsp = Nsps.getByTitleId(request.bits[2])
		response.attachFile(nsp.titleId + '.nsp')

		if len(request.bits) >= 5:
			start = int(request.bits[-2])
			end = int(request.bits[-1])
	
		#chunkSize = 0x1000000
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

def getScan(request, response):
	success(request, response, nut.scan(scanTitles = True))


def postTinfoilSetInstalledApps(request, response):
	try:
		if len(request.bits) >= 3:
			serial = request.bits[2]
		else:
			serial = 'incognito'

		path = 'switch/' + serial + ''
		Print.info('path: ' + path)
		os.makedirs(path, exist_ok=True)

		with open(path + '/installed.json', 'wb') as f:
			f.write(request.post)

		return success(request, response, "OK")
	except:
		raise


def getSwitchList(request, response):
	try:
		dirs = [f for f in os.listdir('switch/') if os.path.isdir(os.path.join('switch/', f))]
		response.write(json.dumps(dirs))
	except BaseException as e:
		error(request, response, str(e))

def getSwitchInstalled(request, response):
	try:
		path = 'switch/' + request.bits[2] + '/installed.json'
		with open(path, encoding="utf-8-sig") as f:
			response.write(f.read())
			return

	except BaseException as e:
		error(request, response, str(e))
		
def isWindows():
	if "win" in sys.platform[:3].lower():
		return True
	else:
		return False

def listDrives():
	drives = []
	for label,url in Config.paths.mapping().items():
		drives.append(label)
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

def isBlocked(path):
	path = path.lower()

	whitelist = ['.nro', '.xci', '.nsp', '.nsx', '.nsz', '.xcz', '.conf', '.json', '.db', '.tfl', '.jpg', '.gif', '.png', '.bin', '.enc', '.ini', '.ips', '.txt', '.pdf']

	for ext in whitelist:
		if path.endswith(ext):
			return False

	return True
	
def isNetworkPath(url):
	return url.startswith('http://') or url.startswith('https://')

def cleanPath(path = None):
	if not path:
		return None
		
	bits = path.replace('\\', '/').split('/')
	drive = bits[0]
	bits = bits[1:]
	
	if drive in Config.paths.mapping():
		url = Config.paths.mapping()[drive]
		if isNetworkPath(url):
			path = os.path.join(url, '/'.join(bits))
		else:
			path = os.path.abspath(os.path.join(os.path.abspath(url), '/'.join(bits)))
	elif isWindows():
		path = os.path.abspath(os.path.join(drive+':/', '/'.join(bits)))
	else:
		path = os.path.abspath('/'.join(bits))

	return path

def resolveRelativeUrl(path, parent):
	if path[0] == '/':
		#return '/' + parent + path
		if len(path) > 1:
			return path[1:]
	#return '/'.join(parent.split('/')[0:3]) + path
	return path
	
def isValidCache(cacheFileName, expiration = 10 * 60):
	if not os.path.isfile(cacheFileName):
		return False

	if not expiration or time.time() - os.path.getmtime(cacheFileName) < expiration:
		return True
	return False
	
def gdriveQuery(service, q, fields = ['id', 'name', 'size', 'mimeType'], expiration = 10 * 60, teamDriveId = None):
	cacheFileName = 'cache/gdrive/' + hashlib.md5((str(teamDriveId) + str(q) + ','.join(fields)).encode()).hexdigest()
	
	os.makedirs('cache/gdrive/', exist_ok=True)
	
	try:
		if isValidCache(cacheFileName, expiration = expiration):
			with open(cacheFileName, encoding="utf-8-sig") as f:
				return json.loads(f.read())
	except:
		pass
	
	nextToken = None
	items = []
	
	while True:
		if teamDriveId:
			results = service.files().list(pageSize=100, teamDriveId=teamDriveId, includeItemsFromAllDrives = True, corpora = "teamDrive", supportsTeamDrives = True, q = q, fields="nextPageToken, files(" + ', '.join(fields)  + ")", pageToken = nextToken).execute()
		else:
			results = service.files().list(pageSize=100, q = q, fields="nextPageToken, files(" + ', '.join(fields)  + ")", pageToken = nextToken).execute()
		items += results.get('files', [])
			
		if not 'nextPageToken' in results:
			break

		nextToken = results['nextPageToken']
		
	try:
		with open(cacheFileName, 'w') as f:
			json.dump(items, f)
	except:
		pass
		
	return items
	
def gdriveDrives(service, fields = ['nextPageToken', 'drives(id, name)']):

	cacheFileName = 'cache/gdrive/' + hashlib.md5((','.join(fields)).encode()).hexdigest()
	
	os.makedirs('cache/gdrive/', exist_ok=True)
	
	try:
		if isValidCache(cacheFileName, expiration = expiration):
			with open(cacheFileName, encoding="utf-8-sig") as f:
				return json.loads(f.read())
	except:
		pass
		
	nextToken = None
	items = []
	
	while True:
		results = service.drives().list(pageSize=100, fields=', '.join(fields), pageToken = nextToken).execute()
		items += results.get('drives', [])
			
		if not 'nextPageToken' in results:
			break
		nextToken = results['nextPageToken']
		break
		
	try:
		with open(cacheFileName, 'w') as f:
			json.dump(items, f)
	except:
		pass
		
	return items

def gdriveSearchTree(pathBits, nameIdMap, children, id = None, roots = None):
	if id is None:
		for name, id in roots.items():
			if name == pathBits[0]:
				r = gdriveSearchTree(pathBits[1:], nameIdMap, children, id, roots)
				if r is not None:
					return r
		return None
		
	if len(pathBits) <= 0:
		return id
		
	for folderId in nameIdMap[pathBits[0]]:	
		if len(pathBits) == 1:
			return folderId

		if folderId in children:
			for item in children[folderId]:
				r = gdriveSearchTree(pathBits[1:], nameIdMap, children, folderId, roots)
			
				if r is not None:
					return r

	return None

def getFileInfo(service, path):
	bits = [x for x in path.split('/') if x]
	folderId = gdriveGetFolderId(service, '/'.join(bits[0:-1]))
	return gdriveQuery(service, "'%s' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'" % folderId)

def getTeamDriveId(service, path):
	bits = [x for x in path.replace('\\', '/').split('/') if x]
	
	if len(bits) == 0:
		return None
	
	if bits[0] == 'mydrive':			
		return None
	else:
		for item in gdriveDrives(service):
			id = item['id']
			name = item['name']
			if name == bits[0]:
				return id

	return None
	
def gdriveGetFolderId(service, path):
	bits = [x for x in path.replace('\\', '/').split('/') if x]
	
	if len(bits) == 0:
		return 'root'

	nextToken = None
	items = []
	
	children = {'root': []}
	names = {}
	roots = {}	

	rootId = None
	teamDriveId = None
	
	if bits[0] == 'mydrive':			
		rootId = 'root'
	else:
		for item in gdriveDrives(service):
			id = item['id']
			name = item['name']
			if name == bits[0]:
				rootId = id
				teamDriveId = id
				break

	if not rootId:
		return None
		
	if len(bits) == 1:
		return rootId
		
	for item in gdriveQuery(service, "'%s' in parents and trashed=false and mimeType = 'application/vnd.google-apps.folder'" % rootId, teamDriveId = teamDriveId):
		roots[item['name']] = item['id']
	
	if rootId == 'root':
		items = gdriveQuery(service, "mimeType = 'application/vnd.google-apps.folder'", fields = ['id', 'name', 'size', 'mimeType', 'parents'])
	else:
		items = gdriveQuery(service, "mimeType = 'application/vnd.google-apps.folder'", fields = ['id', 'name', 'size', 'mimeType', 'parents'], teamDriveId = rootId)
		
	for item in items:
		if 'parents' in item:
			for parentId in item['parents']:
				if not parentId in children:
					children[parentId] = []
				children[parentId].append(item)
		else:
			children['root'].append(item)
		
		if not item['name'] in names:
			names[item['name']] = []
		names[item['name']].append(item['id'])
		

	return gdriveSearchTree(bits[1:], names, children, None, roots)
	
def getFileInfo(service, path):
	try:
		bits = [x for x in path.replace('\\', '/').split('/') if x]
		dirPath = '/'.join(bits[0:-1])
		folderId = gdriveGetFolderId(service, dirPath)
		
		teamDriveId = getTeamDriveId(service, path)

		for item in gdriveQuery(service, "'%s' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'" % folderId, fields = ['*'], teamDriveId = teamDriveId):
			if item['name'] == bits[-1]:
				return item
	except:
		raise
	return None
	
def getGdriveToken(request, response):
	creds = None

	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)

	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				Config.getGdriveCredentialsFile(), SCOPES)
			creds = flow.run_local_server(port=0)

		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)
	
	r = {}
	r['access_token'] = creds.token
	r['refresh_token'] = creds.refresh_token
	
	with open(Config.getGdriveCredentialsFile(), 'r') as f:
		r['credentials'] = json.loads(f.read())
	
	
	response.write(json.dumps(r))
		
def listGdriveDir(path):
	r = {'dirs': [], 'files': []}
	
	creds = None

	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)

	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				Config.getGdriveCredentialsFile(), SCOPES)
			creds = flow.run_local_server(port=0)

		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	service = build('drive', 'v3', credentials=creds)

	bits = [x for x in path.replace('\\', '/').split('/') if x]


	
	if len(bits) == 0:
		r['dirs'].append({'name': 'mydrive'})
		for item in gdriveDrives(service):
			r['dirs'].append({'name': item['name']})
	else:
		teamDriveId = getTeamDriveId(service, path)
		for item in gdriveQuery(service, "'%s' in parents and trashed=false" % gdriveGetFolderId(service, path), teamDriveId = teamDriveId):
			o = {'name':  item['name']}
			if 'size' in item:
				o['size'] = int(item['size'])
				
			if 'kind' in item:
				o['kind'] = item['kind']
				
			if 'mimeType' in item and item['mimeType'] == 'application/vnd.google-apps.folder':
				r['dirs'].append(o)
			else:
				r['files'].append(o)			

	return r
	
def getDirectoryList(request, response):
	try:
		path = ''
		
		if len(request.bits) > 2:
			virtualDir = request.bits[2]
		else:
			virtualDir = ''

		if virtualDir == 'gdrive':
			for i in request.bits[3:]:
				path = os.path.join(path, i)
			r = listGdriveDir(path)
			response.write(json.dumps(r))
			return
			
		for i in request.bits[2:]:
			path = os.path.join(path, i)
			
		path = cleanPath(path)
		
		r = {'dirs': [], 'files': []}
		
		if not path:
			for d in listDrives():
				r['dirs'].append({'name': d})
			response.write(json.dumps(r))
			return
		
		if isNetworkPath(path):
			x = makeRequest('GET', path)
			soup = BeautifulSoup(x.text, 'html.parser')
			items = soup.select('a')
			
			for a in items:
				href = a['href']
				
				if href.endswith('/'):
					r['dirs'].append({'name': resolveRelativeUrl(href, virtualDir)})
				else:
					r['files'].append({'name': resolveRelativeUrl(href, virtualDir)})
			
		else:
			for name in os.listdir(path):
				abspath = os.path.join(path, name)

				if os.path.isdir(abspath):
					r['dirs'].append({'name': name})
				elif os.path.isfile(abspath):
					if not isBlocked(abspath):
						r['files'].append({'name': name, 'size': os.path.getsize(abspath), 'mtime': os.path.getmtime(abspath)})

		response.write(json.dumps(r))
	except:
		raise
		raise IOError('dir list access denied')
		
def downloadProxyFile(url, response, start = None, end = None, headers = {}):
	bytes = 0
	
	r = makeRequest('GET', url, start = start, end = end, hdArgs = headers)
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
		raise ValueError('Downloaded data is not as big as expected (%s/%s)!' % (bytes, size))

	return bytes
	
def downloadGdriveFile(response, url, start = None, end = None):
	creds = None

	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)

	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				Config.getGdriveCredentialsFile(), SCOPES)
			creds = flow.run_local_server(port=0)

		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	service = build('drive', 'v3', credentials=creds)
	
	info = getFileInfo(service, url)

	if not info:
		return Server.Response404(request, response)
		
	#request = service.files().get_media(fileId=info['id'])
	
	return downloadProxyFile('https://www.googleapis.com/drive/v3/files/%s?alt=media' % info['id'], response, start, end, headers = {'Authorization': 'Bearer ' + creds.token })
	
def getFile(request, response, start = None, end = None):
	try:
		path = ''
		
		if len(request.bits) > 2:
			virtualDir = request.bits[2]
		else:
			virtualDir = ''
		
		for i in request.bits[2:]:
			path = os.path.join(path, i)
		path = cleanPath(path)

		if isBlocked(path):
			raise IOError('access denied');

		if 'Range' in request.headers:
			start, end = request.headers.get('Range').strip().strip('bytes=').split('-')

			if end != '':
				end = int(end) + 1

			if start != '':
				start = int(start)

		if virtualDir == 'gdrive':
			path = ''
			for i in request.bits[3:]:
				path = os.path.join(path, i)				
			return downloadGdriveFile(response, path, start = start, end = end)
			
		elif isNetworkPath(path):
			downloadProxyFile(path, response, start = start, end = end)
		else:
			return serveFile(response, path, start = start, end = end)
	except:
		raise
		raise IOError('file read access denied')

def getFileSize(request, response):
	t = {}
	path = ''
	for i in request.bits[2:]:
		path = os.path.join(path, i)
	path = cleanPath(path)
	try:
		t['size'] = os.path.getsize(path);
		t['mtime'] = os.path.getmtime(path);
		response.write(json.dumps(t))
	except BaseException as e:
		response.write(json.dumps({'success': False, 'message': str(e)}))



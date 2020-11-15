import os
import io
import Fs.driver
from nut import Print
from nut import Config
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import hashlib
import requests

SCOPES = ['https://www.googleapis.com/auth/drive']

def resolveRelativeUrl(path, parent):
	if path[0] == '/':
		if len(path) > 1:
			return path[1:]
	return path


def isValidCache(cacheFileName, expiration=10 * 60):
	if not os.path.isfile(cacheFileName):
		return False

	if not expiration or time.time() - os.path.getmtime(cacheFileName) < \
			expiration:
		return True
	return False


def gdriveQuery(
		service,
		q,
		fields=['id', 'name', 'size', 'mimeType'],
		expiration=10 * 60,
		teamDriveId=None
):
	hashText = str(teamDriveId) + str(q) + ','.join(fields)
	cacheFileName = 'cache/gdrive/' + hashlib.md5(
		hashText.encode()
	).hexdigest()

	os.makedirs('cache/gdrive/', exist_ok=True)

	try:
		if isValidCache(cacheFileName, expiration=expiration):
			with open(cacheFileName, encoding="utf-8-sig") as f:
				return json.loads(f.read())
	except:
		pass

	nextToken = None
	items = []

	while True:
		if teamDriveId:
			results = service.files().list(
				pageSize=100,
				teamDriveId=teamDriveId,
				includeItemsFromAllDrives=True,
				corpora="teamDrive",
				supportsTeamDrives=True,
				q=q,
				fields="nextPageToken, files(" + ', '.join(fields) + ")",
				pageToken=nextToken,
			).execute()
		else:
			results = service.files().list(
				pageSize=100,
				q=q,
				fields="nextPageToken, files(" + ', '.join(fields) + ")",
				pageToken=nextToken,
			).execute()
		items += results.get('files', [])

		if 'nextPageToken' not in results:
			break

		nextToken = results['nextPageToken']

	try:
		with open(cacheFileName, 'w') as f:
			json.dump(items, f)
	except:
		pass

	return items


def gdriveDrives(service, fields=['nextPageToken', 'drives(id, name)']):
	cacheName = hashlib.md5((','.join(fields)).encode()).hexdigest()
	cacheFileName = 'cache/gdrive/' + cacheName

	os.makedirs('cache/gdrive/', exist_ok=True)

	try:
		if isValidCache(cacheFileName):
			with open(cacheFileName, encoding="utf-8-sig") as f:
				return json.loads(f.read())
	except:
		pass

	nextToken = None
	items = []

	while True:
		results = service.drives().list(
			pageSize=100,
			fields=', '.join(fields),
			pageToken=nextToken
		).execute()
		items += results.get('drives', [])

		if 'nextPageToken' not in results:
			break
		nextToken = results['nextPageToken']
		break

	try:
		with open(cacheFileName, 'w') as f:
			json.dump(items, f)
	except:
		pass

	return items


def gdriveSearchTree(pathBits, children, id=None, roots=None):
	if id is None:
		for name, id in roots.items():
			if name == pathBits[0]:
				r = gdriveSearchTree(
					pathBits[1:],
					children[id] if id in children else [],
					id,
					roots
				)
				if r is not None:
					return r
		return None

	if len(pathBits) <= 0:
		return id

	for entry in children:
		if entry['name'] != pathBits[0]:
			continue

		folderId = entry['id']

		if len(pathBits) == 1:
			return folderId

		if folderId in children:
			for newChildren in children[folderId]:
				r = gdriveSearchTree(
					pathBits[1:],
					newChildren,
					folderId,
					roots
				)

				if r is not None:
					return r

	return None


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

	items = []

	children = {'root': []}
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

	for item in gdriveQuery(
			service,
			f"'{rootId}' in parents and trashed=false and mimeType = " +
			"'application/vnd.google-apps.folder'",
			teamDriveId=teamDriveId
	):
		roots[item['name']] = item['id']

	if rootId == 'root':
		items = gdriveQuery(
			service,
			"mimeType = 'application/vnd.google-apps.folder' and " +
			"trashed=false",
			fields=['id', 'name', 'size', 'mimeType', 'parents']
		)
	else:
		items = gdriveQuery(
			service,
			"mimeType = 'application/vnd.google-apps.folder' and " +
			"trashed=false",
			fields=['id', 'name', 'size', 'mimeType', 'parents'],
			teamDriveId=rootId
		)

	for item in items:
		if 'parents' in item:
			for parentId in item['parents']:
				if parentId not in children:
					children[parentId] = []
				children[parentId].append(item)
		else:
			children['root'].append(item)

	return gdriveSearchTree(bits[1:], children, None, roots)


def getFileInfo(service, path):
	try:
		if path.startswith('gdrive:'):
			path = path[len('gdrive:'):]
		bits = [x for x in path.replace('\\', '/').split('/') if x]
		dirPath = '/'.join(bits[0:-1])
		folderId = gdriveGetFolderId(service, dirPath)

		teamDriveId = getTeamDriveId(service, path)

		for item in gdriveQuery(service, f"'{folderId}' in parents and trashed=false and mimeType != " + "'application/vnd.google-apps.folder'", fields=['*'], teamDriveId=teamDriveId):
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

		with open('gdrive.token', 'w') as token:
			token.write(json.dumps({
				'access_token': creds.token,
				'refresh_token': creds.refresh_token
			}))

	r = {}
	r['access_token'] = creds.token
	r['refresh_token'] = creds.refresh_token

	with open(Config.getGdriveCredentialsFile(), 'r') as f:
		r['credentials'] = json.loads(f.read())

	if response is not None:
		response.write(json.dumps(r))

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

def download(url, callback, start=None, end=None, headers={}):
	bytes = 0

	r = makeRequest('GET', url, start=start, end=end, hdArgs=headers)
	size = int(r.headers.get('Content-Length'))

	chunkSize = 0x100000

	if size >= 10000:

		for chunk in r.iter_content(chunkSize):
			callback(chunk)
			bytes += len(chunk)

			if not Config.isRunning:
				break
	else:
		callback(r.content)
		bytes += len(r.content)

	if size != 0 and bytes != size:
		raise ValueError(
			f'Downloaded data is not as big as expected ({bytes}/{size})!'
		)

	return bytes

class FileContext(Fs.driver.FileContext):
	def __init__(self, url, sz, mode, parent):
		super(FileContext, self).__init__(url, sz, mode, parent)

	def close(self):
		pass

	def read(self, sz=None):
		output = io.BytesIO()
		self.chunk(output.write)
		return output.getvalue()

	def chunk(self, callback, offset=None, size=None):

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

			info = getFileInfo(service, self.url)

			if not info:
				return server.Response404(None, response)

			download(
				'https://www.googleapis.com/drive/v3/files/%s?alt=media' % info['id'],
				callback,
				offset,
				None if offset is None else (offset + size - 1),
				headers={'Authorization': 'Bearer ' + creds.token}
			)

class DirContext(Fs.driver.DirContext):
	def __init__(self, url, parent):
		super(DirContext, self).__init__(url, parent)

	def ls(self):
		entries = []
		r = {'dirs': [], 'files': []}
		path = self.url[len('gdrive:/'):]

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
				entries.append(Fs.driver.DirEntry(Fs.driver.join(self.url, item['name'])))
		else:
			teamDriveId = getTeamDriveId(service, path)
			for item in gdriveQuery( service, "'%s' in parents and trashed=false" % gdriveGetFolderId(service, path),	teamDriveId=teamDriveId):
				o = {'name': item['name']}
				if 'size' in item:
					o['size'] = int(item['size'])

				if 'kind' in item:
					o['kind'] = item['kind']

				if 'mimeType' in item and item['mimeType'] == \
						'application/vnd.google-apps.folder':
					entries.append(Fs.driver.DirEntry(Fs.driver.join(self.url, o['name'])))
				else:
					entries.append(Fs.driver.FileEntry(Fs.driver.join(self.url, o['name']), o['size']))

		return entries


class GoogleDrive(Fs.driver.Interface):
	def __init__(self, url=None):
		super(GoogleDrive, self).__init__(url)
		self.dirContextType = DirContext
		self.fileContextType = FileContext


Fs.driver.registry.add('gdrive', GoogleDrive)

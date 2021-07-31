from nut import Config
from nut import Title
from nut import Titles
from nut import Print
from nut import Nsps
import Fs
import os
import re
import nut
import shutil

class IndexedFile:
	def __init__(self, path, mode='rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		self.path = None
		self.titleId = None
		self.timestamp = None
		self.version = None
		self.fileSize = None
		self.fileModified = None
		self.extractedNcaMeta = False

		self.cr = None
		self.hasValidTicket = None
		self.verified = None
		self.attributes = {}

		if path:
			self.setPath(path)

		try:
			super(IndexedFile, self).__init__(None, path, mode, cryptoType, cryptoKey, cryptoCounter)
		except:
			super(IndexedFile, self).__init__()

	def __lt__(self, other):
		return str(self.path) < str(other.path)

	def __iter__(self):
		return self.files.__iter__()

	def getExtractedNcaMeta(self):
		if hasattr(self, 'extractedNcaMeta') and self.extractedNcaMeta:
			return 1
		return 0

	def setExtractedNcaMeta(self, val):
		if val and (val != 0 or val):
			self.extractedNcaMeta = True
		else:
			self.extractedNcaMeta = False

	def getHasValidTicket(self):
		if self.title().isUpdate:
			return 1
		return (1 if self.hasValidTicket and self.hasValidTicket else 0)

	def isUpdateAvailable(self):
		title = self.title()

		if self.titleId and str(title.version) is not None and str(self.version) < str(title.version) and str(title.version) != '0':
			return {'id': title.id, 'baseId': title.baseId, 'currentVersion': str(self.version), 'newVersion': str(title.version)}

		if not title.isUpdate and not title.isDLC and Titles.contains(title.updateId):
			updateFile = self.getUpdateFile()

			if updateFile:
				return updateFile.isUpdateAvailable()

			updateTitle = Titles.get(title.updateId)

			if str(updateTitle.version) and str(updateTitle.version) != '0':
				return {'id': updateTitle.id, 'baseId': title.baseId, 'currentVersion': None, 'newVersion': str(updateTitle.version)}

		return None

	def setId(self, id):
		if re.match(r'[A-F0-9]{16}', id, re.I):
			self.titleId = id

	def getId(self):
		return self.titleId or ('0' * 16)

	def setTimestamp(self, timestamp):
		try:
			self.timestamp = int(str(timestamp), 10)
		except BaseException:
			pass

	def getTimestamp(self):
		return str(self.timestamp or '')

	def setVersion(self, version):
		if version and len(version) > 0:
			self.version = version

	def getVersion(self):
		return self.version or ''

	def isUpdate(self):
		return self.titleId is not None and self.titleId.endswith('800')

	def isDLC(self):
		return self.titleId is not None and not self.isUpdate() and not self.titleId.endswith('000')

	def title(self):
		if not self.titleId:
			raise IOError('NSP no titleId set')

		if self.titleId in Titles.keys():
			return Titles.get(self.titleId)

		t = Title.Title()
		t.setId(self.titleId)
		Titles.data()[self.titleId] = t
		return t

	def setHasValidTicket(self, value):
		if hasattr(self.title(), 'isUpdate') and self.title().isUpdate:
			self.hasValidTicket = True
			return

		try:
			self.hasValidTicket = (True if value and int(value) != 0 else False) or self.title().isUpdate
		except BaseException:
			pass

	def move(self, forceNsp=False):
		if not self.path:
			Print.error('no path set')
			return False

		if os.path.abspath(self.path).startswith(os.path.abspath(Config.paths.nspOut)) and not self.path.endswith('.nsz') and not self.path.endswith('.xcz') and Config.compression.auto:
			nszFile = nut.compress(self.path, Config.compression.level, os.path.abspath(Config.paths.nspOut))

			if nszFile:
				nsp = Fs.Nsp(nszFile, None)
				nsp.hasValidTicket = True
				nsp.move(forceNsp=True)
				Nsps.files[nsp.path] = nsp
				Nsps.save()

		newPath = self.fileName(forceNsp=forceNsp)

		if not newPath:
			Print.error('could not get filename for ' + self.path)
			return False

		newPath = os.path.abspath(newPath)

		if newPath.lower().replace('\\', '/') == self.path.lower().replace('\\', '/'):
			return False

		if os.path.isfile(newPath):
			Print.info('\nduplicate title: ')
			Print.info(os.path.abspath(self.path))
			Print.info(newPath)
			Print.info('\n')
			return False

		if not self.verifyNcaHeaders():
			Print.error('verification failed: could not move title for ' + str(self.titleId) + ' or ' + str(Title.getBaseId(self.titleId)))
			return False

		try:
			Print.info(self.path + ' -> ' + newPath)

			if not Config.dryRun:
				os.makedirs(os.path.dirname(newPath), exist_ok=True)
			#newPath = self.fileName(forceNsp = forceNsp)

			if not Config.dryRun:
				if self.isOpen():
					self.close()
				shutil.move(self.path, newPath)
				Nsps.moveFile(self.path, newPath)
				#Nsps.files[newPath] = self
				self.path = newPath
		except BaseException as e:
			Print.error('failed to rename file! %s -> %s  : %s' % (self.path, newPath, e))
			if not Config.dryRun:
				self.moveDupe()

		return True

	def verifyNcaHeaders(self):
		return True

	def moveDupe(self):
		if Config.dryRun:
			return True

		try:
			newPath = self.fileName()
			os.makedirs(Config.paths.duplicates, exist_ok=True)
			origDupePath = Config.paths.duplicates + os.path.basename(newPath)
			dupePath = origDupePath
			Print.info('moving duplicate ' + os.path.basename(newPath))
			c = 0
			while os.path.isfile(dupePath):
				dupePath = Config.paths.duplicates + os.path.basename(newPath) + '.' + str(c)
				c = c + 1
			shutil.move(self.path, dupePath)
			return True
		except BaseException as e:
			Print.error('failed to move to duplicates! ' + str(e))
		return False

	def cleanFilename(self, s):
		if s is None:
			return ''
		#s = re.sub(r'\s+\Demo\s*', ' ', s, re.I)
		s = re.sub(r'\s*\[DLC\]\s*', '', s, re.I)
		s = re.sub(r'[\/\\\:\*\?\"\<\>\|\.\s™©®()\~]+', ' ', s)
		return s.strip()

	def storeValue(self, name, value):
		self.attributes[name] = value

	def getValue(self, name):
		return self.attributes[name]

	def dict(self):
		r = {
			"titleId": self.titleId,
			"hasValidTicket": self.hasValidTicket,
			'extractedNcaMeta': self.getExtractedNcaMeta(),
			'version': self.version,
			'timestamp': self.timestamp,
			'path': self.path,
			'verified': self.verified,
			'fileSize': self.fileSize
		}

		for k,v in self.attributes.items():
			r['__' + k] = v

		return r

	def getCr(self, inverted=False):
		if not hasattr(self, 'cr') or not self.cr:
			self.cr = self.getCrFromPath()

		if not hasattr(self, 'cr') or not self.cr:
			Print.info('extracting CR for ' + str(self.path))
			try:
				container = Fs.factory(self.path)
				container.open(self.path, 'rb')

				compressedSize = 0
				uncompressedSize = 0

				for f in container:
					if not isinstance(f, Fs.Nca):
						continue
					uncompressedSize += f.header.size
					compressedSize += f.size

				container.close()
				self.cr = int(compressedSize * 100.0 / uncompressedSize)

			except BaseException as e:
				Print.error('getCr exception: %s' % str(e))
				return ''

		if not self.cr:
			return ''

		if inverted:
			return '%02d' % (100 - int(self.cr))
		else:
			return '%02d' % int(self.cr)

	def fileName(self, forceNsp=False):
		bt = None

		if self.titleId not in Titles.keys():
			if not Title.getBaseId(self.titleId) in Titles.keys():
				if Config.allowNoMetadata:
						bt = Title.Title()
				else:
					Print.error('could not find base title for ' + str(self.titleId) + ' or ' + str(Title.getBaseId(self.titleId)))
					return None
			else:
				bt = Titles.get(Title.getBaseId(self.titleId))
			t = Title.Title()
			if bt.name is not None:
				t.loadCsv(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
			else:
				t.setId(self.titleId)
		else:
			t = Titles.get(self.titleId)

			if not t:
				Print.error('could not find title id ' + str(self.titleId))
				return None

			try:
				if t.baseId not in Titles.keys():
					if Config.allowNoMetadata:
						bt = Title.Title()
					else:
						Print.info('could not find baseId for ' + self.path)
						return None
				else:
					bt = Titles.get(t.baseId)
			except BaseException as e:
				Print.error('exception: could not find title id ' + str(self.titleId) + ' ' + str(e))
				return None
			

		isNsx = not self.hasValidTicket and not forceNsp

		try:
			if t.isDLC:
				format = Config.paths.getTitleDLC(isNsx, self.path)
			elif t.isDemo:
				if t.idExt != 0:
					format = Config.paths.getTitleDemoUpdate(isNsx, self.path)
				else:
					format = Config.paths.getTitleDemo(isNsx, self.path)
			elif t.idExt != 0:
				if bt and bt.isDemo:
					format = Config.paths.getTitleDemoUpdate(isNsx, self.path)
				else:
					format = Config.paths.getTitleUpdate(isNsx, self.path)
			else:
				format = Config.paths.getTitleBase(isNsx, self.path)
		except BaseException as e:
			Print.error('calc path exception: ' + str(e))
			return None

		if not format:
			return None

		newName = self.cleanFilename(t.getName() or '')

		format = format.replace('{id}', self.cleanFilename(t.id))
		format = format.replace('{region}', self.cleanFilename(t.getRegion() or bt.getRegion()))
		format = format.replace('{name}', newName)
		format = format.replace('{version}', str(self.getVersion() or 0))
		format = format.replace('{baseId}', self.cleanFilename(bt.id))

		if '{cr}' in format:
			format = format.replace('{cr}', str(self.getCr()))

		if '{icr}' in format:
			format = format.replace('{icr}', str(self.getCr(True)))

		bn = os.path.basename(self.path)
		if (not newName or len(newName) == 0) and not bn.upper().startswith(t.id.upper()):
			Print.error('could not get new name for ' + bn)
			return os.path.join(os.path.dirname(format), os.path.basename(self.path))

		baseName = self.cleanFilename(bt.getName() or '')

		if not baseName or len(baseName) == 0:
			baseName = os.path.basename(self.path)

		result = format.replace('{baseName}', baseName)

		while(len(os.path.basename(result).encode('utf-8')) > 240 and len(baseName) > 3):
			baseName = baseName[:-1]
			result = format.replace('{baseName}', baseName)

		return os.path.abspath(result)

	def getCrFromPath(self):
		z = re.match(r'.*\[CR([0-9]{1,3})\].*', self.path, re.I)
		if z:
			return int(z.groups()[0])

		return None

	def getFileSize(self):
		if self.fileSize is None:
			try:
				self.fileSize = os.path.getsize(self.path)
			except BaseException as e:
				Print.error(f"getting file size of title `{self.path}`: {str(e)}")
		return self.fileSize

	def getFileModified(self):
		if self.fileModified is None:
			self.fileModified = os.path.getmtime(self.path)
		return self.fileModified

	def baseName(self):
		return os.path.basename(self.path)

	def setPath(self, path):
		self.path = path
		self.version = '0'

		z = re.match(r'.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0].upper()
		else:
			z = re.match(r'^([a-zA-Z0-9]{16})\..*', os.path.basename(path), re.I)
			if z:
				self.titleId = z.groups()[0].upper()
			else:
				Print.info('could not get title id from filename, name needs to contain [titleId] : ' + path)
				self.titleId = None

		if not hasattr(self, 'cr') or not self.cr:
			self.cr = self.getCrFromPath()

		z = re.match(r'.*\[v([0-9]+)\].*', path, re.I)

		if z:
			self.version = z.groups()[0]

		if path.endswith('.nsp') or path.endswith('.nsz'):
			if self.hasValidTicket is None:
				self.setHasValidTicket(True)
		elif path.endswith('.nsx'):
			if self.hasValidTicket is None:
				self.setHasValidTicket(False)
		elif path.endswith('.xci') or path.endswith('.xcz'):
			if self.hasValidTicket is None:
				self.setHasValidTicket(True)
		else:
			print('unknown extension ' + str(path))
			return

	def getPath(self):
		return self.path or ''

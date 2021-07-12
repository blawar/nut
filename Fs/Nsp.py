from nut import aes128
from nut import Title
from nut import Titles
from nut import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from Fs.File import File
from hashlib import sha256
import Fs.Type
import os
import re
import pathlib
from nut import Keys
from nut import Config
from nut import Print
from nut import Nsps
from tqdm import tqdm
from Fs.Pfs0 import Pfs0
from Fs.Nca import Nca
from Fs.IndexedFile import IndexedFile
import shutil
from nut import blockchain

MEDIA_SIZE = 0x200

class Nsp(Pfs0, IndexedFile):
	def __init__(self, path=None, mode='rb'):
		self.path = None
		self.titleId = None
		self.hasValidTicket = None
		self.timestamp = None
		self.version = None
		self.fileSize = None
		self.fileModified = None
		self.extractedNcaMeta = False
		self.verified = None

		super(Nsp, self).__init__(None, path, mode)

		if path:
			self.setPath(path)
			# if files:
			#	self.pack(files)

		if self.titleId and self.isUnlockable():
			Print.info('unlockable title found ' + self.path)
		#	self.unlock()

	def loadCsv(self, line, map=['id', 'path', 'version', 'timestamp', 'hasValidTicket', 'extractedNcaMeta', 'fileSize']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				Print.info('invalid map index: ' + str(i) + ', ' + str(len(map)))
				continue

			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())

	def serialize(self, map=['id', 'path', 'version', 'timestamp', 'hasValidTicket', 'extractedNcaMeta', 'fileSize']):
		r = []
		for i in map:

			methodName = 'get' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda: methodName)
			r.append(str(method()))
		return '|'.join(r)

	def __lt__(self, other):
		return str(self.path) < str(other.path)

	def __iter__(self):
		return self.files.__iter__()

	def getUpdateFile(self):
		title = self.title()

		if title.isUpdate or title.isDLC or not title.updateId:
			return None

		for i, nsp in Nsps.files.items():
			if nsp.titleId == title.updateId:
				return nsp

		return None

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

	def readMeta(self):
		self.open()
		try:
			#a = self.application()
			# if a.header.titleId:
			#	self.titleId = a.header.titleId
			#	self.title().setRightsId(a.header.rightsId)

			t = self.ticket()
			rightsId = hx(t.getRightsId().to_bytes(0x10, byteorder='big')).decode('utf-8').upper()
			self.titleId = rightsId[0:16]
			self.title().setRightsId(rightsId)
			Print.info('rightsId = ' + rightsId)

			titleKey = t.getTitleKeyBlock()
			titleKeyStr = format(titleKey, 'X').zfill(32)
			if titleKey != 0 and blockchain.verifyKey(self.titleId, titleKeyStr):
				Print.info(self.titleId + ' key = ' + titleKeyStr)
				self.title().setKey(titleKeyStr)
				self.setHasValidTicket(True)
		except BaseException as e:
			Print.info('readMeta filed ' + self.path + ", " + str(e))
			raise
		self.close()

	def unpack(self, path):
		os.makedirs(path, exist_ok=True)

		for nspF in self:
			filePath = os.path.abspath(path + '/' + nspF._path)
			f = open(filePath, 'wb')
			nspF.rewind()
			i = 0

			pageSize = 0x10000

			while True:
				buf = nspF.read(pageSize)
				if len(buf) == 0:
					break
				i += len(buf)
				f.write(buf)
			f.close()
			Print.info(filePath)

	# extractedNcaMeta

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

	def open(self, path=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(Nsp, self).open(path or self.path, mode, cryptoType, cryptoKey, cryptoCounter)

	def hasDeltas(self):
		return b'DeltaFragment' in self.xml().read()

	def application(self):
		for f in (f for f in self if f._path.endswith('.nca') and not f._path.endswith('.cnmt.nca')):
			return f
		raise IOError('no application in NSP')

	def isUnlockable(self, reunlock=False):
		return (not self.hasValidTicket or reunlock) and self.titleId and Titles.contains(self.titleId) and Titles.get(self.titleId).key

	def unlock(self):
		# if not self.isOpen():
		#	self.open('r+b')

		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database!')

		self.ticket().setTitleKeyBlock(int(Titles.get(self.titleId).key, 16))
		Print.info('setting title key to ' + Titles.get(self.titleId).key)
		self.ticket().flush()

		if self._path:
			self.path = self._path
		self.hasValidTicket = True
		self.move(forceNsp=True)
		self.close()

	def verifyKey(self, titleId, userkey=None):
		if not userkey:
			try:
				ticket = self.ticket()
				masterKeyRev = ticket.getMasterKeyRevision()
				userkey = ticket.getTitleKeyBlock().to_bytes(16, byteorder='big')
			except BaseException:
				userkey = None
		else:
			userkey = uhx(userkey)

		for f in self:
			if not isinstance(f, Nca) or not f.header.hasTitleRights() or f.header.titleId != titleId:
				continue
			try:
				if f.verifyKey(userkey):
					return True
			except BaseException:
				pass
		return False

	def verifyNcaHeaders(self):
		for f in self:
			if not isinstance(f, Nca):
				continue
			if not f.verifyHeader():
				return False
		return True

	def setMasterKeyRev(self, newMasterKeyRev):
		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database! ' + self.titleId)

		ticket = self.ticket()
		masterKeyRev = ticket.getMasterKeyRevision()
		titleKey = ticket.getTitleKeyBlock()
		newTitleKey = Keys.changeTitleKeyMasterKey(titleKey.to_bytes(16, byteorder='big'),
												   Keys.getMasterKeyIndex(masterKeyRev), Keys.getMasterKeyIndex(newMasterKeyRev))
		rightsId = ticket.getRightsId()

		if rightsId != 0:
			raise IOError('please remove titlerights first')

		if (newMasterKeyRev is None and rightsId == 0) or masterKeyRev == newMasterKeyRev:
			Print.info('Nothing to do')
			return

		Print.info('rightsId =\t' + hex(rightsId))
		Print.info('titleKey =\t' + str(hx(titleKey.to_bytes(16, byteorder='big'))))
		Print.info('newTitleKey =\t' + str(hx(newTitleKey)))
		Print.info('masterKeyRev =\t' + hex(masterKeyRev))

		for nca in self:
			if isinstance(nca, Nca):
				if nca.header.getCryptoType2() != masterKeyRev:
					pass
					raise IOError('Mismatched masterKeyRevs!')

		ticket.setMasterKeyRevision(newMasterKeyRev)
		ticket.setRightsId((ticket.getRightsId() & 0xFFFFFFFFFFFFFFFF0000000000000000) + newMasterKeyRev)
		ticket.setTitleKeyBlock(int.from_bytes(newTitleKey, 'big'))

		for nca in self:
			if isinstance(nca, Nca):
				if nca.header.getCryptoType2() != newMasterKeyRev:
					Print.info('writing masterKeyRev for %s, %d -> %s' % (str(nca._path), nca.header.getCryptoType2(), str(newMasterKeyRev)))

					encKeyBlock = nca.header.getKeyBlock()

					if sum(encKeyBlock) != 0:
						key = Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex)
						Print.info('decrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
						crypto = aes128.AESECB(key)
						decKeyBlock = crypto.decrypt(encKeyBlock)

						key = Keys.keyAreaKey(Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex)
						Print.info('encrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex))
						crypto = aes128.AESECB(key)

						reEncKeyBlock = crypto.encrypt(decKeyBlock)
						nca.header.setKeyBlock(reEncKeyBlock)

					if newMasterKeyRev >= 3:
						nca.header.setCryptoType(2)
						nca.header.setCryptoType2(newMasterKeyRev)
					else:
						nca.header.setCryptoType(newMasterKeyRev)
						nca.header.setCryptoType2(0)

	def removeTitleRights(self):
		if not Titles.contains(self.titleId):
			raise IOError('No title key found in database! ' + self.titleId)

		ticket = self.ticket()
		masterKeyRev = ticket.getMasterKeyRevision()
		titleKeyDec = Keys.decryptTitleKey(ticket.getTitleKeyBlock().to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(masterKeyRev))
		rightsId = ticket.getRightsId()

		Print.info('rightsId =\t' + hex(rightsId))
		Print.info('titleKeyDec =\t' + str(hx(titleKeyDec)))
		Print.info('masterKeyRev =\t' + hex(masterKeyRev))

		for nca in self:
			if isinstance(nca, Nca):
				if nca.header.getCryptoType2() != masterKeyRev:
					pass
					raise IOError('Mismatched masterKeyRevs!')

		ticket.setRightsId(0)

		for nca in self:
			if isinstance(nca, Nca):
				if nca.header.getRightsId() == 0:
					continue

				kek = Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex)
				Print.info('writing masterKeyRev for %s, %d' % (str(nca._path), masterKeyRev))
				Print.info('kek =\t' + hx(kek).decode())
				crypto = aes128.AESECB(kek)

				encKeyBlock = crypto.encrypt(titleKeyDec * 4)
				nca.header.setRightsId(0)
				nca.header.setKeyBlock(encKeyBlock)
				Hex.dump(encKeyBlock)

	def setGameCard(self, isGameCard=False):
		if isGameCard:
			targetValue = 1
		else:
			targetValue = 0

		for nca in self:
			if isinstance(nca, Nca):
				if nca.header.getIsGameCard() == targetValue:
					continue

				Print.info('writing isGameCard for %s, %d' % (str(nca._path), targetValue))
				nca.header.setIsGameCard(targetValue)

	def pack(self, files, rights_id=None, key=None):
		if not self.path:
			return False

		Print.info('\tRepacking to NSP...')

		if rights_id:
			if not key:
				key = Titles.get(rights_id[0:16].upper()).key

			if not key:
				raise IOError('title key not found')

			base = os.path.join(os.path.dirname(files[0]), rights_id.lower())

			certFile = base + '.cert'
			tikFile = base + '.tik'

			shutil.copyfile('Certificate.cert', certFile)

			with open('Ticket.tik', 'rb') as intik:
				data = bytearray(intik.read())
				data[0x180:0x190] = uhx(key)
				data[0x285] = int(rights_id[-2:], 16) + 1

				data[0x2A0:0x2B0] = uhx(rights_id)

				with open(tikFile, 'wb') as f:
					f.write(data)

				if certFile not in files:
					files.append(certFile)

				if tikFile not in files:
					files.append(tikFile)

		hd = self.generateHeader(files)

		totalSize = len(hd) + sum(os.path.getsize(file) for file in files)
		if os.path.exists(self.path) and os.path.getsize(self.path) == totalSize:
			Print.info('\t\tRepack %s is already complete!' % self.path)
			return

		t = tqdm(total=totalSize, unit='B', unit_scale=True, desc=os.path.basename(self.path), leave=False)

		t.write('\t\tWriting header...')
		outf = open(self.path, 'wb')
		outf.write(hd)
		t.update(len(hd))

		done = 0
		for file in files:
			t.write('\t\tAppending %s...' % os.path.basename(file))
			with open(file, 'rb') as inf:
				while True:
					buf = inf.read(4096)
					if not buf:
						break
					outf.write(buf)
					t.update(len(buf))

		t.close()

		Print.info('\t\tRepacked to %s!' % outf.name)
		outf.close()

	def generateHeader(self, files):
		filesNb = len(files)

		stringTable = '\x00'.join(os.path.basename(file) for file in files)
		headerSize = 0x10 + (filesNb)*0x18 + len(stringTable)
		remainder = 0x10 - headerSize % 0x10
		headerSize += remainder

		fileSizes = [os.path.getsize(file) for file in files]
		fileOffsets = [sum(fileSizes[:n]) for n in range(filesNb)]

		fileNamesLengths = [len(os.path.basename(file))+1 for file in files]  # +1 for the \x00
		stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(filesNb)]

		header = b''
		header += b'PFS0'
		header += pk('<I', filesNb)
		header += pk('<I', len(stringTable)+remainder)
		header += b'\x00\x00\x00\x00'
		for n in range(filesNb):
			header += pk('<Q', fileOffsets[n])
			header += pk('<Q', fileSizes[n])
			header += pk('<I', stringTableOffsets[n])
			header += b'\x00\x00\x00\x00'
		header += stringTable.encode()
		header += remainder * b'\x00'

		return header

	def verify(self):
		success = True
		for f in self:
			if not isinstance(f, Nca):
				continue
			hash = str(f.sha256())

			if hash[0:16] != str(f._path)[0:16]:
				Print.error('BAD HASH %s = %s' % (str(f._path), str(f.sha256())))
				success = False

		return success

from nut import aes128
from nut import Title
from nut import Titles
from nut import Hex
from binascii import hexlify as hx, unhexlify as uhx
from struct import pack as pk, unpack as upk
from hashlib import sha256
import Fs.Type
import os
import re
import math
import pathlib
from nut import Keys
from nut import Config
from nut import Print
from nut import Nsps
from tqdm import tqdm
import Fs
from Fs.File import File
from Fs.Rom import Rom
from Fs.Pfs0 import Pfs0
from Fs.BaseFs import BaseFs
from Fs import Type
from Fs.File import MemoryFile
import traceback
import sys


MEDIA_SIZE = 0x200

def rootFile(o):
	try:
		if o is None:
			return None

		return rootFile(o.f) or o._path
	except:
		return None

class SectionTableEntry:
	def __init__(self, d):
		self.mediaOffset = int.from_bytes(d[0x0:0x4], byteorder='little', signed=False)
		self.mediaEndOffset = int.from_bytes(d[0x4:0x8], byteorder='little', signed=False)

		self.offset = self.mediaOffset * MEDIA_SIZE
		self.endOffset = self.mediaEndOffset * MEDIA_SIZE

		self.unknown1 = int.from_bytes(d[0x8:0xc], byteorder='little', signed=False)
		self.unknown2 = int.from_bytes(d[0xc:0x10], byteorder='little', signed=False)
		self.sha1 = None

class HierarchicalSha256:
	def __init__(self, d, f, header):
		self.f = f
		self.data = d
		self.hash = hx(d[0x0:0x20]).decode()
		self.blockSize = int.from_bytes(d[0x20:0x24], byteorder='little', signed=False)
		self.unk1 = int.from_bytes(d[0x24:0x28], byteorder='little', signed=False)
		self.offset = int.from_bytes(d[0x28:0x30], byteorder='little', signed=False)
		self.size = int.from_bytes(d[0x30:0x38], byteorder='little', signed=False)

		self.pfs0Offset = int.from_bytes(d[0x38:0x40], byteorder='little', signed=False)
		self.pfs0Size = int.from_bytes(d[0x40:0x48], byteorder='little', signed=False)		

		self.multiplier = math.ceil(self.pfs0Size / self.blockSize)
		self.header = header

		self.verify()

	def verify(self):
		if self.unk1 != 2:
			raise IOError('invalid HierarchicalSha256 value')

		hash1 = sha256(uhx(self.getHashTable())).hexdigest()

		if hash1 != self.hash:
			Print.error('\n\n ********** invalid HierarchicalSha256 hash value ********** \n\n')

	def getHashTable(self):
		fs = self.header.fs.f
		fs.seek(0)
		data = fs.read(0x20*self.multiplier)
		return hx(data).decode()

	def calculateHashTableHash(self):
		fs = self.header.fs.f
		fs.seek(0)
		data = fs.read(0x20*self.multiplier)
		return sha256(data).hexdigest()

	def getHashTableHash(self):
		self.f.seek(self.header.hashOffset)
		return hx(self.f.read(0x20)).decode()

	def setHashTableHash(self, hash):
		self.f.seek(self.header.hashOffset)
		self.f.write(uhx(hash))

	def calculateHash(self):
		r = ''
		fs = self.header.fs
		remaining = self.pfs0Size
		fs.seek(0)

		for i in range(self.multiplier):
			data = fs.read(min(remaining, self.blockSize))
			remaining -= len(data)
			r += sha256(data).hexdigest()
		return r

	def setHash(self):
		newHash = uhx(self.calculateHash())
		fs = self.header.fs.f
		fs.seek(0)
		fs.write(newHash)

		sbhash = sha256(newHash).hexdigest()
		self.setHashTableHash(sbhash)

	def printInfo(self, maxDepth=3, indent=0):
		tabs = '\t' * indent

		Print.info(tabs + 'HierarchicalSha256: ')
		Print.info(tabs + 'Block Size: ' + str(self.blockSize))
		Print.info(tabs + 'Offset: ' + str(self.offset))
		Print.info(tabs + 'Size: ' + str(self.size))
		Print.info(tabs + 'PFS0 Offset: ' + str(self.pfs0Offset))
		Print.info(tabs + 'PFS0 Size: ' + str(self.pfs0Size))
		Print.info(tabs + 'Multiplier: ' + str(self.multiplier))

		
		
		try:
			storedHash = str(self.getHashTable()).lower()
			calculatedHash = str(self.calculateHash()).lower()

			if calculatedHash != storedHash:
				Print.info(tabs + '** BAD CONTENT HASH **:')
				Print.info(tabs + 'Hash Stored: ' + storedHash)
				Print.info(tabs + 'Hash Clcltd: ' + calculatedHash)
		except BaseException as e:
			Print.info(tabs + 'Hash Clcltd: ' + str(e))
		Print.info(tabs + 'Hash Table Hash Stored: ' + str(self.getHashTableHash()))

		Print.info(tabs + 'Hash Table Hash Actual: ' + self.calculateHashTableHash())

class FsHeader:
	def __init__(self, f, fs = None):
		self.version = f.readInt16()
		self.fsType = f.readInt8()
		self.hashType = f.readInt8()
		self.encryptionType = f.readInt8()
		self.padding = f.read(3)
		self.hashOffset = f.tell()
		self.hashInfo = f.read(0xF8)
		self.patchInfo = f.read(0x40)
		self.generation = f.readInt32()
		self.secureValue = f.readInt32()
		self.sparseInfo = f.read(0x30)
		self.reserved = f.read(0x88)

		self.hash = None
		self.fs = fs

		try:
			if self.hashType == 2:
				self.hash = HierarchicalSha256(self.hashInfo, f, self)
		except BaseException as e:
			Print.error(str(e))

	def printInfo(self, maxDepth=3, indent=0):
		tabs = '\t' * indent
		Print.info('\n')
		Print.info(tabs + 'version: ' + str(self.version))
		Print.info(tabs + 'fsType: ' + str(self.fsType))
		Print.info(tabs + 'hashType: ' + str(self.hashType))
		Print.info(tabs + 'encryptionType: ' + str(self.encryptionType))
		Print.info(tabs + 'padding: ' + hx(self.padding).decode())
		Print.info(tabs + 'generation: ' + str(self.generation))
		Print.info(tabs + 'secureValue: ' + str(self.secureValue))

		if self.hash:
			self.hash.printInfo(maxDepth, indent+1)

		#Print.info(tabs + 'hashInfo: ' + hx(self.hashInfo).decode())
		Print.info(tabs + 'patchInfo: ' + hx(self.patchInfo).decode())
		Print.info(tabs + 'sparseInfo: ' + hx(self.sparseInfo).decode())
		#Print.info(tabs + 'reserved: ' + hx(self.reserved).decode())


def GetSectionFilesystem(buffer, cryptoKey):
	fsType = buffer[0x3]
	if fsType == Fs.Type.Fs.PFS0:
		return Fs.Pfs0(buffer, cryptoKey=cryptoKey)

	if fsType == Fs.Type.Fs.ROMFS:
		return Fs.Rom(buffer, cryptoKey=cryptoKey)

	return BaseFs(buffer, cryptoKey=cryptoKey)

class NcaHeader(File):
	def __init__(self, path=None, mode=None, cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		self.signature1 = None
		self.signature2 = None
		self.magic = None
		self.isGameCard = None
		self.contentType = None
		self.cryptoType = None
		self.keyIndex = None
		self.size = None
		self.titleId = None
		self.contentIndex = None
		self.sdkVersion = None
		self.cryptoType2 = None
		self.rightsId = None
		self.titleKeyDec = None
		self.masterKey = None
		self.sectionTables = []
		self.keys = []

		super(NcaHeader, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

	def open(self, file=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(NcaHeader, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signature1 = self.read(0x100)
		self.signature2 = self.read(0x100)
		self.magic = self.read(0x4)
		self.isGameCard = self.readInt8()
		self.contentType = self.readInt8()

		try:
			self.contentType = Fs.Type.Content(self.contentType)
		except BaseException:
			pass

		self.cryptoType = self.readInt8()
		self.keyIndex = self.readInt8()
		self.size = self.readInt64()
		self.titleId = hx(self.read(8)[::-1]).decode('utf-8').upper()
		self.contentIndex = self.readInt32()
		self.sdkVersion = self.readInt32()
		self.cryptoType2 = self.readInt8()

		self.read(0xF)  # padding

		self.rightsId = hx(self.read(0x10))

		if self.magic not in [b'NCA3', b'NCA2']:
			raise Exception('Failed to decrypt NCA header: ' + str(self.magic))

		containerPath = rootFile(self)
		if containerPath:
			tikFile = os.path.join(os.path.dirname(containerPath), self.rightsId.decode('utf-8').lower()) + '.tik'

			if os.path.isfile(tikFile):
				tik = Fs.factory(tikFile)
				tik.open(tikFile, 'r+b')
				title = Titles.get(tik.titleId())
				title.key = format(tik.getTitleKeyBlock(), 'X').zfill(32)
				tik.close()

		self.sectionHashes = []

		for i in range(4):
			self.sectionTables.append(SectionTableEntry(self.read(0x10)))

		for i in range(4):
			self.sectionHashes.append(hx(self.read(0x20)).decode())

		self.masterKey = (self.cryptoType if self.cryptoType > self.cryptoType2 else self.cryptoType2)-1

		if self.masterKey < 0:
			self.masterKey = 0

		self.encKeyBlock = self.getKeyBlock()
		# for i in range(4):
		#	offset = i * 0x10
		#	key = encKeyBlock[offset:offset+0x10]
		#	Print.info('enc %d: %s' % (i, hx(key)))

		#crypto = aes128.AESECB(Keys.keyAreaKey(self.masterKey, 0))
		self.keyBlock = Keys.unwrapAesWrappedTitlekey(self.encKeyBlock, self.masterKey)
		self.keys = []
		for i in range(4):
			offset = i * 0x10
			key = self.keyBlock[offset:offset+0x10]
			#Print.info('dec %d: %s' % (i, hx(key)))
			self.keys.append(key)

		if self.hasTitleRights():
			titleRightsTitleId = self.rightsId.decode()[0:16].upper()

			if titleRightsTitleId in Titles.keys() and Titles.get(titleRightsTitleId).key:
				self.titleKeyDec = Keys.decryptTitleKey(uhx(Titles.get(titleRightsTitleId).key), self.masterKey)
			else:
				pass
				#Print.info('could not find title key!')
		else:
			self.titleKeyDec = self.key()

		return True

	def calculateFsHeaderHash(self, index):
		self.seek(0x400 + (index * 0x200))
		buffer = self.read(0x200)
		h = sha256(buffer).hexdigest()

		return h

	def getFsHeader(self, index, fs = None):
		self.seek(0x400 + (index * 0x200))
		return FsHeader(self, fs = fs)

	def realTitleId(self):
		if not self.hasTitleRights():
			return self.titleId

		return self.getRightsIdStr()[0:16]

	def key(self):
		return self.keys[2]

	def hasTitleRights(self):
		return self.rightsId != (b'0' * 32)

	def getKeyBlock(self):
		self.seek(0x300)
		return self.read(0x40)

	def setKeyBlock(self, value):
		if len(value) != 0x40:
			raise IOError('invalid keyblock size')

		self.seek(0x300)
		return self.write(value)

	def getCryptoType(self):
		self.seek(0x206)
		return self.readInt8()

	def setCryptoType(self, value):
		self.seek(0x206)
		self.writeInt8(value)

	def getCryptoType2(self):
		self.seek(0x220)
		return self.readInt8()

	def setCryptoType2(self, value):
		self.seek(0x220)
		self.writeInt8(value)

	def getRightsId(self):
		self.seek(0x230)
		return self.readInt128('big')

	def getRightsIdStr(self):
		self.seek(0x230)
		return hx(self.read(16)).decode()

	def setRightsId(self, value):
		self.seek(0x230)
		self.writeInt128(value, 'big')

	def getIsGameCard(self):
		self.seek(0x204)
		return self.readInt8()

	def setIsGameCard(self, value):
		self.seek(0x204)
		self.writeInt8(value)

	def verify(self):
		self.seek(0x200)
		buffer = self.read(0x200)
		if self.verifyBuffer(buffer):
			return True
		# TODO try different combos incase it was converted
		return False

	def verifyBuffer(self, buffer):
		if Keys.pssVerify(buffer, self.signature1, Keys.ncaHdrFixedKeyModulus):
			return True
		return False

	def setRightsIdBuffer(self, buffer, keyGen):
		buffer[0x30:0x38] = int(self.titleId, 16).to_bytes(8, byteorder='big')
		buffer[0x38:0x40] = keyGen.to_bytes(8, byteorder='big')
		buffer[0x100:0x140] = b'\x00' * 0x40

		if keyGen <= 2:
			buffer[0x6] = keyGen
			buffer[0x20] = 0
		else:
			buffer[0x6] = 2
			buffer[0x20] = keyGen
		return buffer

	def setStandardCryptoBuffer(self, buffer, keyGen):
		buffer[0x30:0x40] = b'\x00' * 0x10

		emptyKey = b'\x00' * 0x10

		kek = Keys.keyAreaKey(Keys.getMasterKeyIndex(keyGen), self.keyIndex)
		crypto = aes128.AESECB(kek)

		encKeyBlock = crypto.encrypt(emptyKey + emptyKey + self.titleKeyDec + emptyKey)

		buffer[0x100:0x140] = encKeyBlock

		if keyGen <= 2:
			buffer[0x6] = keyGen
			buffer[0x20] = 0
		else:
			buffer[0x6] = 2
			buffer[0x20] = keyGen

		return buffer

	def getVerifiedHeader(self):
		self.seek(0x200)
		buffer = bytearray(self.read(0x200))

		if self.verifyBuffer(buffer):
			return buffer

		for gameCardValue in [0, 1]:
			buffer[0x04] = gameCardValue

			if self.verifyBuffer(buffer):
				Print.info('isGameCard = %d' % gameCardValue)
				return buffer

		if self.hasTitleRights():
			return None

		title = Titles.get(self.titleId)

		'''
		if title.rightsId:
			for gameCardValue in [0, 1]:
				buffer[0x04] = gameCardValue
			#return False
		'''

		for gameCardValue in [0, 1]:
			buffer[0x04] = gameCardValue
			for keyGen in Keys.getKeyGens():
				buffer = self.setRightsIdBuffer(buffer, keyGen)
				if self.verifyBuffer(buffer):
					Print.info('Title Rights: isGameCard = %d, keyGen = %d' % (gameCardValue, keyGen))
					return buffer

		for gameCardValue in [0, 1]:
			buffer[0x04] = gameCardValue
			for keyGen in Keys.getKeyGens():
				buffer = self.setStandardCryptoBuffer(buffer, keyGen)
				if self.verifyBuffer(buffer):
					Print.info('Standard Crypto: isGameCard = %d, keyGen = %d' % (gameCardValue, keyGen))
					return buffer

		return None

	def restore(self):
		header = self.getVerifiedHeader()

		if not header:
			raise IOError('could not restore nca header for %s - %s' % (self.titleId, str(self.f._path)))

		if not self.hasTitleRights():
			if header[0x30:0x40] != b'\x00' * 0x10:
				self.rightsId = hx(header[0x30:0x40])
				key = hx(Keys.encryptTitleKey(self.key(), max(max(header[0x6], header[0x20])-1, 0))).decode().upper()
				#key = hx(self.key()).decode().upper()
				title = Titles.get(self.titleId)

				if title.key and title.key != key:
					raise IOError('nca title key does not match database: %s vs %s' % (title.key, key))
				elif not title.key:
					title.key = key
			else:
				self.rightsId = b'0' * 32

		self.seek(0x200)
		self.write(header)
		return True


class Nca(File):
	def __init__(self, path=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		self.header = None
		self.sectionFilesystems = []
		self.sections = []
		super(Nca, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

	def __iter__(self):
		return self.sectionFilesystems.__iter__()

	def __getitem__(self, key):
		return self.sectionFilesystems[key]

	def open(self, file=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(Nca, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)

		self.header = NcaHeader()
		self.partition(0x0, 0xC00, self.header, Fs.Type.Crypto.XTS, uhx(Keys.get('header_key')))
		#Print.info('partition complete, seeking')
		self.header.seek(0x400)
		# Print.info('reading')
		# Hex.dump(self.header.read(0x200))
		# exit()

		if self._path is not None and self._path.endswith('.ncz'):
			return

		for i in range(4):
			hdr = self.header.read(0x200)
			section = BaseFs(hdr, cryptoKey=self.header.titleKeyDec)
			fs = GetSectionFilesystem(hdr, cryptoKey=-1)
			#Print.info('fs type = ' + hex(fs.fsType))
			#Print.info('fs crypto = ' + hex(fs.cryptoType))
			#Print.info('st end offset = ' + str(self.header.sectionTables[i].endOffset - self.header.sectionTables[i].offset))
			#Print.info('fs offset = ' + hex(self.header.sectionTables[i].offset))
			#Print.info('fs section start = ' + hex(fs.sectionStart))
			#Print.info('titleKey = ' + hex(self.header.titleKeyDec))

			self.partition(self.header.sectionTables[i].offset, self.header.sectionTables[i].endOffset - self.header.sectionTables[i].offset, section, cryptoKey=self.header.titleKeyDec)

			try:
				section.partition(fs.sectionStart, section.size - fs.sectionStart, fs)
			except BaseException as e:
				pass
				# Print.info(e)
				# raise

			if fs.fsType:
				self.sectionFilesystems.append(fs)
				self.sections.append(section)

			try:
				fs.open(None, 'rb')
			except BaseException as e:
				Print.error(str(e))
				traceback.print_exc(file=sys.stdout)

		self.titleKeyDec = None

	def masterKey(self):
		return max(self.header.cryptoType, self.header.cryptoType2)

	def buildId(self):
		if self.header.contentType != Fs.Type.Content.PROGRAM:
			return None

		if self._path.endswith('.ncz'):
			return None

		try:
			f = self[0]['main']
			f.seek(0x40)
			return hx(f.read(0x20)).decode('utf8').upper()
		except IOError as e:
			pass
		except BaseException:
			raise
			return None

	def updateFsHashes(self):
		for i in range(4):
			tbl = self.header.sectionTables[i]

			if not tbl.endOffset:
				continue

			header = self.header.getFsHeader(i, fs = self.sectionFilesystems[i])

			if header.hash:
				header.hash.setHash()

			hash = self.header.calculateFsHeaderHash(i)
			self.header.seek(0x280 + (i * 0x20))
			hash2 = hx(self.header.read(0x20))
			self.header.seek(0x280 + (i * 0x20))
			self.header.write(uhx(hash))

		self.flush()

	def verifyHeader(self):
		return self.header.verify()

	def verifyKey(self, userkey):
		if not self.header.hasTitleRights():
			titleKeyDec = Keys.decryptTitleKey(file.getTitleKeyBlock().to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(self.masterKey()))
		else:
			encKey = userkey

			titleKeyDec = Keys.decryptTitleKey(encKey, Keys.getMasterKeyIndex(self.masterKey()))

			'''
			print('\nTesting {} with:'.format(self))
			print('- Keygeneration {}'.format(self.masterKey()))
			print('- Encrypted key {}'.format(str(hx(encKey))[2:-1]))
			print('- Decrypted key {}'.format(str(hx(titleKeyDec))[2:-1]))
			'''

		decKey = titleKeyDec
		f = self

		if self.header.getRightsId() != 0:
			for fs in self:
				# print(fs.fsType)
				# print(fs.cryptoType)
				if fs.fsType == Type.Fs.PFS0 and fs.cryptoType == Type.Crypto.CTR:
					f.seek(0)
					ncaHeader = NcaHeader()
					ncaHeader.open(MemoryFile(f.read(0x400), Type.Crypto.XTS, uhx(Keys.get('header_key'))))
					pfs0 = fs
					sectionHeaderBlock = fs.buffer

					#fs.f.setKey(b'\x00' * 16)
					#print('- Current key {}'.format(str(hx(fs.f.cryptoKey))[2:-1]))

					fs.seek(0)
					pfs0Offset = 0  # int.from_bytes(sectionHeaderBlock[0x38:0x40], byteorder='little', signed=False)
					pfs0Header = fs.read(0x10)

					# Hex.dump(sectionHeaderBlock)
					#mem = MemoryFile(pfs0Header, Type.Crypto.CTR, decKey, pfs0.cryptoCounter, offset = pfs0Offset)
					data = pfs0Header  # mem.read();
					# Hex.dump(pfs0Header)
					magic = data[0:4]
					# print(magic)
					if magic != b'PFS0':
						return False
					else:
						return True

				if fs.fsType == Type.Fs.ROMFS and fs.cryptoType == Type.Crypto.CTR:
					f.seek(0)
					ncaHeader = NcaHeader()
					ncaHeader.open(MemoryFile(f.read(0x400), Type.Crypto.XTS, uhx(Keys.get('header_key'))))
					ncaHeader = f.read(0x400)
					pfs0 = fs
					sectionHeaderBlock = fs.buffer

					levelOffset = int.from_bytes(sectionHeaderBlock[0x18:0x20], byteorder='little', signed=False)
					levelSize = int.from_bytes(sectionHeaderBlock[0x20:0x28], byteorder='little', signed=False)

					pfs0Offset = levelOffset
					f.seek(pfs0Offset + fs.f.offset)
					pfs0Header = f.read(levelSize)

					# fs.seek(pfs0Offset)
					#pfs0Header = fs.read(levelSize)

					#print(sectionHeaderBlock[8:12] == b'IVFC')
					if sectionHeaderBlock[8:12] == b'IVFC':
						# Hex.dump(sectionHeaderBlock)
						# Print.info(hx(sectionHeaderBlock[0xc8:0xc8+0x20]).decode('utf-8'))
						mem = MemoryFile(pfs0Header, Type.Crypto.CTR, decKey, pfs0.cryptoCounter, offset=fs.f.offset)

						data = mem.read()

						#Hex.dump(data, 48)
						#print('hash = %s' % str(sha256(data).hexdigest()))
						if hx(sectionHeaderBlock[0xc8:0xc8+0x20]).decode('utf-8') == str(sha256(data).hexdigest()):
							return True
						else:
							return False
					else:
						mem = MemoryFile(pfs0Header, Type.Crypto.CTR, decKey, pfs0.cryptoCounter, offset=pfs0Offset)
						data = mem.read()
						# Hex.dump(data)
						magic = mem.read()[0:4]
						# print(magic)
						if magic != b'PFS0':
							pass
						else:
							return True

				if fs.fsType == Type.Fs.ROMFS and fs.cryptoType == Type.Crypto.BKTR and str(f.header.contentType) == 'Content.PROGRAM':
					f.seek(0)
					ncaHeader = NcaHeader()
					ncaHeader.open(MemoryFile(f.read(0x400), Type.Crypto.XTS, uhx(Keys.get('header_key'))))
					ncaHeader = f.read(0x400)
					pfs0 = fs
					sectionHeaderBlock = fs.buffer

					levelOffset = int.from_bytes(sectionHeaderBlock[0x18:0x20], byteorder='little', signed=False)
					levelSize = int.from_bytes(sectionHeaderBlock[0x20:0x28], byteorder='little', signed=False)

					pfs0Offset = fs.offset + levelOffset
					f.seek(pfs0Offset)
					pfs0Header = f.read(levelSize)

					if sectionHeaderBlock[8:12] == b'IVFC':
						for i in range(10):
							ini = 0x100+(i*0x10)
							fin = 0x110+(i*4)
							test = sectionHeaderBlock[ini:fin]
							if test == b'BKTR':
								return True
		return False

	def restore(self):
		return self.header.restore()

	def printInfo(self, maxDepth=3, indent=0):
		tabs = '\t' * indent
		Print.info('\n%sNCA Archive\n' % (tabs))
		super(Nca, self).printInfo(maxDepth, indent)

		Print.info(tabs + 'verified header = ' + str(self.header.verify()))
		Print.info(tabs + 'magic = ' + str(self.header.magic))
		Print.info(tabs + 'titleId = ' + str(self.header.titleId))
		Print.info(tabs + 'rightsId = ' + str(self.header.rightsId.decode()))
		Print.info(tabs + 'isGameCard = ' + hex(self.header.isGameCard))
		Print.info(tabs + 'contentType = ' + str(self.header.contentType))
		Print.info(tabs + 'cryptoType = ' + str(self.cryptoType))
		Print.info(tabs + 'Size: ' + str(self.header.size))
		Print.info(tabs + 'crypto master key: ' + str(self.header.cryptoType))
		Print.info(tabs + 'crypto master key2: ' + str(self.header.cryptoType2))
		Print.info(tabs + 'key Index: ' + str(self.header.keyIndex))

		try:
			Print.info('\n' + tabs + 'FsSections:')
			for i in range(4):
				tbl = self.header.sectionTables[i]

				if not tbl.endOffset:
					continue

				Print.info('\t%soffset = %X, endOffset = %X' % (tabs, tbl.offset, tbl.endOffset))

				actualHash = self.header.calculateFsHeaderHash(i)

				if actualHash != str(self.header.sectionHashes[i]):
					Print.info('\t%s ** HASH MISMATCH! **' % (tabs))
					Print.info('\t%sstored hash = %s' % (tabs, str(self.header.sectionHashes[i])))
					Print.info('\t%sactual hash = %s' % (tabs, actualHash))
		except:
			pass

		try:
			Print.info('\n\n' + tabs + 'FsHeaders:')
			for i in range(4):
				tbl = self.header.sectionTables[i]

				if not tbl.endOffset:
					continue

				self.header.getFsHeader(i, fs = self.sectionFilesystems[i]).printInfo(maxDepth = maxDepth, indent = indent + 1)

			Print.info('\n')
		except:
			pass

		'''
		encTitleBlock = hx(self.header.getKeyBlock()).decode()
		for i in range(4):
			Print.info(tabs + 'key Block Enc: ' + encTitleBlock[i * 32 : i * 32 + 32].upper())
		'''

		for key in self.header.keys:
			if key:
				Print.info(tabs + 'key Block Dec: ' + hx(key).decode().upper())

		if(indent+1 < maxDepth):
			Print.info('\n%sPartitions:' % (tabs))

			for s in self:
				s.printInfo(maxDepth, indent+1)

		if self.header.contentType == Fs.Type.Content.PROGRAM:
			Print.info(tabs + 'build Id: ' + str(self.buildId()))

		if self.header.signature1:
			Print.info(tabs + 'Signature1: ' + hx(self.header.signature1).decode())

		if self.header.signature2:
			Print.info(tabs + 'Signature2: ' + hx(self.header.signature2).decode())

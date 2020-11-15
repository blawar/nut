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
import Fs
from Fs.BaseFs import BaseFs

MEDIA_SIZE = 0x200

class Pfs0Stream():
	def __init__(self, path):
		try:
			os.makedirs(os.path.dirname(path), exist_ok=True)
		except BaseException:
			pass
		self.path = path
		self.f = open(path, 'wb')
		self.offset = 0x8000
		self.files = []

		self.f.seek(self.offset)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def add(self, name, size):
		Print.info('Adding file %s %d bytes to NSP' % (name, int(size)))
		self.files.append({'name': name, 'size': size, 'offset': self.f.tell()})
		return self.f

	def get(self, name):
		for i in self.files:
			if i['name'] == name:
				return i
		return None

	def resize(self, name, size):
		for i in self.files:
			if i['name'] == name:
				i['size'] = size
				return True
		return False

	def close(self):
		self.f.seek(0)
		self.f.write(self.getHeader())
		self.f.close()

	def getHeader(self):
		stringTable = '\x00'.join(file['name'] for file in self.files)

		headerSize = 0x10 + len(self.files) * 0x18 + len(stringTable)
		remainder = 0x10 - headerSize % 0x10
		headerSize += remainder

		h = b''
		h += b'PFS0'
		h += len(self.files).to_bytes(4, byteorder='little')
		h += (len(stringTable)+remainder).to_bytes(4, byteorder='little')
		h += b'\x00\x00\x00\x00'

		stringOffset = 0

		for f in self.files:
			h += (f['offset'] - headerSize).to_bytes(8, byteorder='little')
			h += f['size'].to_bytes(8, byteorder='little')
			h += stringOffset.to_bytes(4, byteorder='little')
			h += b'\x00\x00\x00\x00'

			stringOffset += len(f['name']) + 1

		h += stringTable.encode()
		h += remainder * b'\x00'

		return h

class Pfs0(BaseFs):
	def __init__(self, buffer, path=None, mode=None, cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		super(Pfs0, self).__init__(buffer, path, mode, cryptoType, cryptoKey, cryptoCounter)

		if buffer:
			self.size = int.from_bytes(buffer[0x48:0x50], byteorder='little', signed=False)
			self.sectionStart = int.from_bytes(buffer[0x40:0x48], byteorder='little', signed=False)
			#self.offset += self.sectionStart
			#self.size -= self.sectionStart

	def getHeader(self):
		stringTable = '\x00'.join(file.name for file in self.files)

		headerSize = 0x10 + len(self.files) * 0x18 + len(stringTable)
		remainder = 0x10 - headerSize % 0x10
		headerSize += remainder

		h = b''
		h += b'PFS0'
		h += len(self.files).to_bytes(4, byteorder='little')
		h += (len(stringTable)+remainder).to_bytes(4, byteorder='little')
		h += b'\x00\x00\x00\x00'

		stringOffset = 0

		for f in range(len(self.files)):
			header += f.offset.to_bytes(8, byteorder='little')
			header += f.size.to_bytes(8, byteorder='little')
			header += stringOffset.to_bytes(4, byteorder='little')
			header += b'\x00\x00\x00\x00'

			stringOffset += len(f.name) + 1

		h += stringTable.encode()
		h += remainder * b'\x00'

		return h

	def open(self, path=None, mode='rb', cryptoType=-1, cryptoKey=-1, cryptoCounter=-1):
		r = super(Pfs0, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		# self.setupCrypto()
		#Print.info('cryptoType = ' + hex(self.cryptoType))
		#Print.info('titleKey = ' + (self.cryptoKey.hex()))
		#Print.info('cryptoCounter = ' + (self.cryptoCounter.hex()))

		self.magic = self.read(4)
		if self.magic != b'PFS0':
			raise IOError('Not a valid PFS0 partition ' + str(self.magic))

		fileCount = self.readInt32()
		stringTableSize = self.readInt32()
		self.readInt32()  # junk data

		self.stringTableOffset = 0x10 + fileCount * 0x18
		self.seek(self.stringTableOffset)
		self.stringTable = self.read(stringTableSize)
		stringEndOffset = stringTableSize

		headerSize = 0x10 + 0x18 * fileCount + stringTableSize
		self.files = []

		self.namePartitions = []

		for i in range(fileCount):
			i = fileCount - i - 1
			self.seek(0x10 + i * 0x18)

			offset = self.readInt64()
			size = self.readInt64()
			nameOffset = self.readInt32()  # just the offset

			self.namePartitions.append([nameOffset, stringEndOffset - nameOffset])
			name = self.stringTable[nameOffset:stringEndOffset].decode('utf-8').rstrip(' \t\r\n\0')
			stringEndOffset = nameOffset

			self.readInt32()  # junk data

			f = Fs.factory(name)

			f._path = name
			f.offset = offset
			f.size = size

			self.files.append(self.partition(offset + headerSize, f.size, f, autoOpen=False))

		ticket = None

		try:
			ticket = self.ticket()
			ticket.open(None, None)
			#key = format(ticket.getTitleKeyBlock(), 'X').zfill(32)

			if ticket.titleKey() != ('0' * 32) and not Titles.get(ticket.titleId()).key:
				#Print.info('titleId: ' + ticket.titleId())
				#Print.info('titleKey: ' + ticket.titleKey())
				Titles.get(ticket.titleId()).key = ticket.titleKey()

		except BaseException as e:
			pass

		for i in range(fileCount):
			if self.files[i] != ticket:
				self.files[i].open(None, None)

		self.files.reverse()
		'''
		self.seek(0x10 + fileCount * 0x18)
		stringTable = self.read(stringTableSize)

		for i in range(fileCount):
			if i == fileCount - 1:
				self.files[i].name = stringTable[self.files[i].nameOffset:].decode('utf-8').rstrip(' \t\r\n\0')
			else:
				self.files[i].name = stringTable[self.files[i].nameOffset:self.files[i+1].nameOffset].decode('utf-8').rstrip(' \t\r\n\0')
		'''

	def ticket(self, rightsId=None):
		for f in self:
			if type(f).__name__ == 'Ticket' and (rightsId is None or f._path == rightsId + '.tik'):
				return f
		raise IOError('no ticket in NSP')

	def cert(self, rightsId=None):
		for f in self:
			if f._path.endswith('.cert') and (rightsId is None or f._path == rightsId + '.tik'):
				return f
		raise IOError('no cert in NSP')

	def cnmt(self):
		for f in (f for f in self if f._path.endswith('.cnmt.nca')):
			return f
		raise IOError('no cnmt in NSP')

	def xml(self):
		for f in (f for f in self if f._path.endswith('.xml')):
			return f
		raise IOError('no XML in NSP')

	def rename(self, currentName, newName):
		if currentName == newName:
			return True

		Print.info('renaming %s -> %s' % (currentName, newName))
		if len(currentName) != len(newName):
			raise IOError('pfs0 rename must be the same length!')

		for p in self.namePartitions:
			n = self.stringTable[p[0]:p[0]+p[1]].decode('utf-8').rstrip(' \t\r\n\0')

			if n == currentName:
				self.seek(self.stringTableOffset + p[0])
				self.write(newName.encode('utf-8'))
				return True

		raise IOError('failed to renamed pfs0 file')

	def restore(self):
		rightsIds = {}
		ticketCount = 0
		certCount = 0

		lst = [[], []]

		for f in self:
			if type(f).__name__ == 'Nca':
				if f._path.endswith('.cnmt.nca'):
					lst[1].append(f)
				else:
					lst[0].append(f)

			elif type(f).__name__ == 'Ticket':
				ticketCount += 1
			elif f._path.endswith('.cert'):
				certCount += 1

		for l in lst:
			for f in l:
				if type(f).__name__ == 'Nca':
					if f.header.key() == b'\x04' * 16 or f.header.signature1 == b'\x00' * 0x100:
						raise IOError('junk file')

					if f.restore():
						oldName = os.path.basename(f._path)

						if str(f.header.contentType) == 'Content.META':
							newName = f.sha256()[0:32] + '.cnmt.nca'
						else:
							newName = f.sha256()[0:32] + '.nca'

						if f.header.hasTitleRights():
							rightsIds[f.header.rightsId] = True

		if len(rightsIds) > ticketCount:
			raise IOError('missing tickets in NSP, expected %d got %d in %s' % (len(rightsIds), ticketCount, self._path))

		if len(rightsIds) > certCount:
			raise IOError('missing certs in NSP')

		for rightsId in rightsIds:
			rightsId = rightsId.decode()
			title = Titles.get(rightsId[0:16].upper())

			if not title.key:
				raise IOError("could not get title key for " + rightsId)

			if ticketCount == 1:
				ticket = self.ticket()
			else:
				ticket = self.ticket(rightsId)

			if ticketCount == 1:
				cert = self.cert()
			else:
				cert = self.cert(rightsId)

			ticket.setRightsId(int(rightsId, 16))
			ticket.setTitleKeyBlock(int(title.key, 16))
			ticket.setMasterKeyRevision(int(rightsId[16:32], 16))

			self.rename(os.path.basename(ticket._path), rightsId.lower() + '.tik')
			self.rename(os.path.basename(cert._path), rightsId.lower() + '.cert')
		return True

	def printInfo(self, maxDepth=3, indent=0):
		tabs = '\t' * indent
		Print.info('\n%sPFS0\n' % (tabs))
		super(Pfs0, self).printInfo(maxDepth, indent)

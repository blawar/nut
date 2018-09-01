from Fs.File import File
import Fs.Type
from binascii import hexlify as hx, unhexlify as uhx
import Print
import Keys


class Ticket(File):
	def __init__(self, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Ticket, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

		self.signatureType = None
		self.signature = None
		self.signaturePadding = None

		self.issuer = None
		self.titleKeyBlock = None
		self.keyType = None
		self.masterKeyRevision = None
		self.ticketId = None
		self.deviceId = None
		self.rightsId = None
		self.accountId = None

		self.signatureSizes = {}
		self.signatureSizes[Fs.Type.TicketSignature.RSA_4096_SHA1] = 0x200
		self.signatureSizes[Fs.Type.TicketSignature.RSA_2048_SHA1] = 0x100
		self.signatureSizes[Fs.Type.TicketSignature.ECDSA_SHA1] = 0x3C
		self.signatureSizes[Fs.Type.TicketSignature.RSA_4096_SHA256] = 0x200
		self.signatureSizes[Fs.Type.TicketSignature.RSA_2048_SHA256] = 0x100
		self.signatureSizes[Fs.Type.TicketSignature.ECDSA_SHA256] = 0x3C

	def open(self, file = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Ticket, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signatureType = self.readInt32()
		try:
			self.signatureType = Fs.Type.TicketSignature(self.signatureType)
		except:
			raise IOError('Invalid ticket format')

		self.signaturePadding = 0x40 - ((self.signatureSizes[self.signatureType] + 4) % 0x40)

		self.seek(0x4 + self.signatureSizes[self.signatureType] + self.signaturePadding)

		self.issuer = self.read(0x40)
		self.titleKeyBlock = self.read(0x100)
		self.readInt8() # unknown
		self.keyType = self.readInt8()
		self.read(0x4) # unknown
		self.masterKeyRevision = self.readInt8()
		self.read(0x9) # unknown
		self.ticketId = hx(self.read(0x8)).decode('utf-8')
		self.deviceId = hx(self.read(0x8)).decode('utf-8')
		self.rightsId = hx(self.read(0x10)).decode('utf-8')
		self.accountId = hx(self.read(0x4)).decode('utf-8')
		self.seek(0x286)
		self.masterKeyRevision = self.readInt8()

	def seekStart(self, offset):
		self.seek(0x4 + self.signatureSizes[self.signatureType] + self.signaturePadding + offset)

	def getSignatureType(self):
		self.seek(0x0)
		self.signatureType = self.readInt32()
		return self.signatureType

	def setSignatureType(self, value):
		self.seek(0x0)
		self.signatureType = value
		self.writeInt32(value)
		return self.signatureType


	def getSignature(self):
		self.seek(0x4)
		self.signature = self.read(self.signatureSizes[self.getSignatureType()])
		return self.signature

	def setSignature(self, value):
		self.seek(0x4)
		self.signature = value
		self.write(value, self.signatureSizes[self.getSignatureType()])
		return self.signature


	def getSignaturePadding(self):
		self.signaturePadding = 0x40 - ((self.signatureSizes[self.signatureType] + 4) % 0x40)
		return self.signaturePadding


	def getIssuer(self):
		self.seekStart(0x0)
		self.issuer = self.read(0x40)
		return self.issuer

	def setIssuer(self, value):
		self.seekStart(0x0)
		self.issuer = value
		self.write(value, 0x40)
		return self.issuer


	def getTitleKeyBlock(self):
		self.seekStart(0x40)
		#self.titleKeyBlock = self.readInt(0x100, 'big')
		self.titleKeyBlock = self.readInt(0x10, 'big')
		return self.titleKeyBlock

	def getTitleKey(self):
		self.seekStart(0x40)
		return self.read(0x10)

	def setTitleKeyBlock(self, value):
		self.seekStart(0x40)
		self.titleKeyBlock = value
		#self.writeInt(value, 0x100, 'big')
		self.writeInt(value, 0x10, 'big')
		return self.titleKeyBlock


	def getKeyType(self):
		self.seekStart(0x141)
		self.keyType = self.readInt8()
		return self.keyType

	def setKeyType(self, value):
		self.seekStart(0x141)
		self.keyType = value
		self.writeInt8(value)
		return self.keyType


	def getMasterKeyRevision(self):
		self.seekStart(0x146)
		self.masterKeyRevision = self.readInt8()
		return self.masterKeyRevision

	def setMasterKeyRevision(self, value):
		self.seekStart(0x146)
		self.masterKeyRevision = value
		self.writeInt8(value)
		return self.masterKeyRevision


	def getTicketId(self):
		self.seekStart(0x150)
		self.ticketId = self.readInt64('big')
		return self.ticketId

	def setTicketId(self, value):
		self.seekStart(0x150)
		self.ticketId = value
		self.writeInt64(value, 'big')
		return self.ticketId


	def getDeviceId(self):
		self.seekStart(0x158)
		self.deviceId = self.readInt64('big')
		return self.deviceId

	def setDeviceId(self, value):
		self.seekStart(0x158)
		self.deviceId = value
		self.writeInt64(value, 'big')
		return self.deviceId


	def getRightsId(self):
		self.seekStart(0x160)
		self.rightsId = self.readInt128('big')
		return self.rightsId

	def setRightsId(self, value):
		self.seekStart(0x160)
		self.rightsId = value
		self.writeInt128(value, 'big')
		return self.rightsId


	def getAccountId(self):
		self.seekStart(0x170)
		self.accountId = self.readInt32('big')
		return self.accountId

	def setAccountId(self, value):
		self.seekStart(0x170)
		self.accountId = value
		self.writeInt32(value, 'big')
		return self.accountId





	def printInfo(self, indent = 0):
		tabs = '\t' * indent
		Print.info('\n%sTicket\n' % (tabs))
		super(Ticket, self).printInfo(indent)
		Print.info(tabs + 'signatureType = ' + str(self.signatureType))
		Print.info(tabs + 'keyType = ' + str(self.keyType))
		Print.info(tabs + 'masterKeyRev = ' + str(self.masterKeyRevision))
		Print.info(tabs + 'ticketId = ' + str(self.ticketId))
		Print.info(tabs + 'deviceId = ' + str(self.deviceId))
		Print.info(tabs + 'rightsId = ' + hex(self.getRightsId()))
		Print.info(tabs + 'accountId = ' + str(self.accountId))
		Print.info(tabs + 'titleKey = ' + hex(self.getTitleKeyBlock()))
		Print.info(tabs + 'titleKeyDec = ' + str(hx(Keys.decryptTitleKey((self.getTitleKey()), self.masterKeyRevision))))



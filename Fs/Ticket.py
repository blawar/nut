from Fs.File import File
import Fs.Type
from binascii import hexlify as hx, unhexlify as uhx
from nut import Print
from nut import Keys
from nut import blockchain

class Ticket(File):
	def __init__(self, path = None, mode = None, cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(Ticket, self).__init__(path, mode, cryptoType, cryptoKey, cryptoCounter)

		self.signatureType = None
		self.signature = None
		self.signaturePadding = None

		self.issuer = None
		self.titleKeyBlock = None
		self.formatVersion = None
		self.keyType = None
		self.ticketVersion = None
		self.licenseType = None
		self.masterKeyRevision = None
		self.propertyMask = None
		self.ticketId = None
		self.deviceId = None
		self.rightsId = None
		self.accountId = None
		self.sectTotalSize = None
		self.sectHeaderOffset = None
		self.sectNum = None
		self.EntrySize = None

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
		self.formatVersion = self.readInt8()
		self.keyType = self.readInt8()
		self.ticketVersion = self.readInt16()
		self.licenseType = self.readInt8()
		self.masterKeyRevision = self.readInt8()
		self.propertyMask = self.readInt8()
		self.read(0x9) # reserved
		self.ticketId = hx(self.read(0x8)).decode('utf-8')
		self.deviceId = hx(self.read(0x8)).decode('utf-8')
		self.rightsId = hx(self.read(0x10)).decode('utf-8')
		self.accountId = hx(self.read(0x4)).decode('utf-8')
		self.sectTotalSize = self.readInt32()
		self.sectHeaderOffset = self.readInt32()
		self.sectNum = self.readInt16()
		self.sectEntrySize = self.readInt16()
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
		
		
	def getFormatVersion(self):
		self.seekStart(0x140)
		self.formatVersion = self.readInt8()
		return self.formatVersion
	
	def setFormatVersion(self, value):
		self.seekStart(0x140)
		self.formatVersion = value
		self.writeInt8(value)
		return self.formatVersion


	def getKeyType(self):
		self.seekStart(0x141)
		self.keyType = self.readInt8()
		#b = self.readInt8()
		#if b == 0:
		#	self.keyType = 'AES128_CBC'
		#elif b == 1:
		#	self.keyType = 'RSA2048'
		#else:
		#	self.keyType = 'Unknown'
		return self.keyType

	def setKeyType(self, value):
		self.seekStart(0x141)
		self.keyType = value
		self.writeInt8(value)
		return self.keyType
		
		
	def getTicketVersion(self):
		self.seekStart(0x142)
		self.ticketVersion = self.readInt16()
		return self.ticketVersion
	
	def setTicketVersion(self, value):
		self.seekStart(0x142)
		self.ticketVersion = value
		self.writeInt16(value)
		return self.ticketVersion
		
		
	def getLicenseType(self):
		self.seekStart(0x144)
		b = self.readInt8()
		if b == 0:
			self.licenseType = 'Permanent'
		elif b == 1:
			self.licenseType = 'Demo'
		elif b == 2:
			self.licenseType = 'Trial'
		elif b == 3:
			self.licenseType = 'Rental'
		elif b == 4:
			self.licenseType = 'Subscription'
		elif b == 5:
			self.licenseType = 'Service'
		else:
			self.licenseType = 'Unknown'
		return self.licenseType
	
	def setLicenseType(self, value):
		self.seekStart(0x144)
		self.licenseType = value
		self.writeInt8(value)
		return self.licenseType


	def getMasterKeyRevision(self):
		self.seekStart(0x145)
		self.masterKeyRevision = self.readInt8() | self.readInt8()
		return self.masterKeyRevision

	def setMasterKeyRevision(self, value):
		self.seekStart(0x145)
		self.masterKeyRevision = value
		self.writeInt8(value)
		return self.masterKeyRevision
		
		
	def getPropertyMask(self):
		self.seekStart(0x146)
		b = self.readInt8()
		if b == 0:
			self.propertyMask = 'None'
		elif b == 1:
			self.propertyMask = 'PreInstall'
		elif b == 2:
			self.propertyMask = 'SharedTitle'
		elif b == 3:
			self.propertyMask = 'PreInstall & SharedTitle'
		elif b == 4:
			self.propertyMask = 'AllowAllContents'
		elif b == 5:
			self.propertyMask = 'PreInstall & AllowAllContents'
		elif b == 6:
			self.propertyMask = 'SharedTitle & AllowAllContents'
		elif b == 7:
			self.propertyMask = 'PreInstall & SharedTitle & AllowAllContents'
		else:
			self.propertyMask = 'Unknown'
		return self.propertyMask
	
	def setPropertyMask(self, value):
		self.seekStart(0x146)
		self.propertyMask = value
		self.writeInt8(value)
		return self.propertyMask


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
		
		
	def getSectTotalSize(self):
		self.seekStart(0x174)
		self.sectTotalSize = self.readInt32()
		return self.sectTotalSize
	
	def setSectTotalSize(self, value):
		self.seekStart(0x174)
		self.sectTotalSize = value
		self.writeInt32(value)
		return self.sectTotalSize
		
		
	def getSectHeaderOffset(self):
		self.seekStart(0x178)
		self.sectHeaderOffset = self.readInt32()
		return self.sectHeaderOffset
	
	def setSectHeaderOffset(self, value):
		self.seekStart(0x178)
		self.sectHeaderOffset = value
		self.writeInt32(value)
		return self.sectHeaderOffset
		
		
	def getSectNum(self):
		self.seekStart(0x17C)
		self.sectNum = self.readInt16()
		return self.sectNum
	
	def setSectNum(self, value):
		self.seekStart(0x17C)
		self.sectNum = value
		self.writeInt16(value)
		return self.sectNum
		
		
	def getSectEntrySize(self):
		self.seekStart(0x17E)
		self.sectEntrySize = self.readInt16()
		return self.sectEntrySize
	
	def setSectEntrySize(self, value):
		self.seekStart(0x17E)
		self.sectEntrySize = value
		self.writeInt16(value)
		return self.sectEntrySize


	def printInfo(self, maxDepth = 3, indent = 0):
		tabs = '\t' * indent

		rightsId = format(self.getRightsId(), 'X').zfill(32)
		titleId = rightsId[0:16]
		titleKey = format(self.getTitleKeyBlock(), 'X').zfill(32)

		Print.info('\n%sTicket\n' % (tabs))
		super(Ticket, self).printInfo(maxDepth, indent)
		Print.info(tabs + 'signatureType = ' + str(self.signatureType))
		Print.info(tabs + 'formatVersion = ' + str(self.formatVersion))
		Print.info(tabs + 'keyType = ' + str(self.keyType)) # titleKeyEncType
		Print.info(tabs + 'ticketVersion = ' + str(self.ticketVersion))
		Print.info(tabs + 'licenseType = ' + str(self.getLicenseType()))
		Print.info(tabs + 'masterKeyRev = ' + str(self.masterKeyRevision)) # commonKeyId
		Print.info(tabs + 'propertyMask = ' + str(self.getPropertyMask()))
		Print.info(tabs + 'ticketId = ' + str(self.ticketId))
		Print.info(tabs + 'deviceId = ' + str(self.deviceId))
		Print.info(tabs + 'rightsId = ' + rightsId)
		Print.info(tabs + 'accountId = ' + str(self.accountId))
		Print.info(tabs + 'sectTotalSize = ' + hex(self.sectTotalSize))
		Print.info(tabs + 'sectHeaderOffset = ' + hex(self.sectHeaderOffset))
		Print.info(tabs + 'sectNum = ' + hex(self.sectNum))
		Print.info(tabs + 'sectEntrySize = ' + hex(self.sectEntrySize))
		Print.info(tabs + 'titleId = ' + titleId)
		Print.info(tabs + 'titleKey = ' + titleKey)
		Print.info(tabs + 'titleKeyDec = ' + str(hx(Keys.decryptTitleKey((self.getTitleKey()), self.masterKeyRevision))))

		try:
			if blockchain.verifyKey(titleId, titleKey):
				tkeyStatus = 'VERIFIED'
			else:
				tkeyStatus = 'BAD KEY'
		except BaseException as e:
			tkeyStatus = 'UNKNOWN - ' + str(e)
			raise

		Print.info(tabs + 'titleKeyStatus = ' + tkeyStatus)
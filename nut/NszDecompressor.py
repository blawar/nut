from pathlib import Path
from hashlib import sha256
from nut import Print, aes128
from zstandard import ZstdDecompressor
from Fs import factory, Type, Pfs0, Hfs0, Xci
from Fs.Pfs0 import Pfs0Stream
import Fs
from nut import Status
import os
from nut import Config

def isNspNsz(path):
	return path.endswith('.nsp') or path.endswith('.nsz') or path.endswith('.nsx')

def isCompressedGameFile(path):
	return path.endswith('.nca') or path.endswith('.ncz')

def changeExtension(path, ext):
	return path[0:-4] + ext

class Section:
	def __init__(self, f):
		self.f = f
		self.offset = f.readInt64()
		self.size = f.readInt64()
		self.cryptoType = f.readInt64()
		f.readInt64() # padding
		self.cryptoKey = f.read(16)
		self.cryptoCounter = f.read(16)

class FakeSection:
	def __init__(self, offset, size):
		self.offset = offset
		self.size = size
		self.cryptoType = 1

class Block:
	def __init__(self, f):
		self.f = f
		self.magic = f.read(8)
		self.version = f.readInt8()
		self.type = f.readInt8()
		self.unused = f.readInt8()
		self.blockSizeExponent = f.readInt8()
		self.numberOfBlocks = f.readInt32()
		self.decompressedSize = f.readInt64()
		self.compressedBlockSizeList = [f.readInt32() for _ in range(self.numberOfBlocks)]

def decompress(filePath, outputDir, statusReportInfo = None):
	if isNspNsz(filePath):
		return __decompressNsz(filePath, outputDir, True, False, statusReportInfo)

	elif isCompressedGameFile(filePath):
		filename = changeExtension(filePath, '.nca')
		outPath = filename if outputDir == None else str(Path(outputDir).joinpath(filename))
		Print.info('Decompressing %s -> %s' % (filePath, outPath))

		if Config.dryRun:
			return None

		container = factory(filePath)
		container.open(filePath, 'rb')
		try:
			with open(outPath, 'wb') as outFile:
				written, hexHash = __decompressNcz(container, outFile)
		except BaseException as ex:
			if not ex is KeyboardInterrupt:
				Print.error(format_exc())
			if outFile.is_file():
				outFile.unlink()
		finally:
			container.close()
		fileNameHash = Path(filePath).stem.lower()
		if hexHash[:32] == fileNameHash:
			Print.info('[VERIFIED]   {0}'.format(filename))
		else:
			Print.info('[MISMATCH]   Filename startes with {0} but {1} was expected - hash verified failed!'.format(fileNameHash, hexHash[:32]))
	else:
		raise NotImplementedError("Can't decompress {0} as that file format isn't implemented!".format(filePath))


def verify(filePath, raiseVerificationException, statusReportInfo):
	if isNspNsz(filePath):
		__decompressNsz(filePath, None, False, raiseVerificationException, statusReportInfo)


def __decompressContainer(readContainer, writeContainer, fileHashes, write, raiseVerificationException, statusReportInfo):
	for nspf in readContainer:
		CHUNK_SZ = 0x100000
		f = None
		if isCompressedGameFile(nspf._path) and nspf.header.contentType == Type.Content.DATA:
			Print.info('skipping delta fragment')
			continue
		if not nspf._path.endswith('.ncz'):
			verifyFile = nspf._path.endswith('.nca') and not nspf._path.endswith('.cnmt.nca')
			if write:
				f = writeContainer.add(nspf._path, nspf.size)
			hash = sha256()
			nspf.seek(0)
			while not nspf.eof():
				inputChunk = nspf.read(CHUNK_SZ)
				hash.update(inputChunk)
				if write:
					f.write(inputChunk)
			if verifyFile:
				if hash.hexdigest()[0:32] in fileHashes:
					Print.info('[VERIFIED]   {0}'.format(nspf._path))
				else:
					Print.info('[CORRUPTED]  {0}'.format(nspf._path))
					if raiseVerificationException:
						raise Exception("Verification detected hash missmatch!")
			elif not write:
				Print.info('[EXISTS]     {0}'.format(nspf._path))
			continue
		newFileName = Path(nspf._path).stem + '.nca'
		if write:
			f = writeContainer.add(newFileName, nspf.size)
		written, hexHash = __decompressNcz(nspf, f, statusReportInfo)
		if write:
			writeContainer.resize(newFileName, written)
		if hexHash[0:32] in fileHashes:
			Print.info('[VERIFIED]   {0}'.format(nspf._path))
		else:
			Print.info('[CORRUPTED]  {0}'.format(nspf._path))
			if raiseVerificationException:
				raise Exception("Verification detected hash missmatch")


def __decompressNcz(nspf, f, statusReportInfo):
	UNCOMPRESSABLE_HEADER_SIZE = 0x4000
	blockID = 0
	nspf.seek(0)
	header = nspf.read(UNCOMPRESSABLE_HEADER_SIZE)
	if f != None:
		start = f.tell()

	magic = nspf.read(8)
	if not magic == b'NCZSECTN':
		raise ValueError("No NCZSECTN found! Is this really a .ncz file?")
	sectionCount = nspf.readInt64()
	sections = [Section(nspf) for _ in range(sectionCount)]
	if sections[0].offset-UNCOMPRESSABLE_HEADER_SIZE > 0:
		fakeSection = FakeSection(UNCOMPRESSABLE_HEADER_SIZE, sections[0].offset-UNCOMPRESSABLE_HEADER_SIZE)
		sections.insert(0, fakeSection)
	nca_size = UNCOMPRESSABLE_HEADER_SIZE
	for i in range(sectionCount):
		nca_size += sections[i].size

	decompressor = ZstdDecompressor().stream_reader(nspf)
	hash = sha256()
	
	bar = Status.create(nspf.size, desc=os.path.basename(nspf._path), unit='B')

	#if statusReportInfo == None:
	#	BAR_FMT = u'{desc}{desc_pad}{percentage:3.0f}%|{bar}| {count:{len_total}d}/{total:d} {unit} [{elapsed}<{eta}, {rate:.2f}{unit_pad}{unit}/s]'
	#	bar = enlighten.Counter(total=nca_size//1048576, desc='Decompress', unit="MiB", color='red', bar_format=BAR_FMT)
	decompressedBytes = len(header)
	if f != None:
		f.write(header)
		bar.add(len(header))

	hash.update(header)

	firstSection = True
	for s in sections:
		i = s.offset
		useCrypto = s.cryptoType in (3, 4)
		if useCrypto:
			crypto = aes128.AESCTR(s.cryptoKey, s.cryptoCounter)
		end = s.offset + s.size
		if firstSection:
			firstSection = False
			uncompressedSize = UNCOMPRESSABLE_HEADER_SIZE-sections[0].offset
			if uncompressedSize > 0:
				i += uncompressedSize
		while i < end:
			if useCrypto:
				crypto.seek(i)
			chunkSz = 0x10000 if end - i > 0x10000 else end - i

			inputChunk = decompressor.read(chunkSz)
			decompressor.flush()

			if not len(inputChunk):
				break
			if useCrypto:
				inputChunk = crypto.encrypt(inputChunk)
			if f != None:
				f.write(inputChunk)
				bar.add(len(inputChunk))
			hash.update(inputChunk)
			lenInputChunk = len(inputChunk)
			i += lenInputChunk
			decompressedBytes += lenInputChunk
			bar.add(lenInputChunk)

	bar.close()
	print()

	hexHash = hash.hexdigest()
	if f != None:
		end = f.tell()
		written = (end - start)
		return (written, hexHash)
	return (0, hexHash)


def __decompressNsz(filePath, outputDir, write, raiseVerificationException, statusReportInfo):
	fileHashes = []# FileExistingChecks.ExtractHashes(filePath)
	container = factory(filePath)
	container.open(str(filePath), 'rb')

	for f in container:
		if isCompressedGameFile(f._path):
			fileHashes.append(f._path.split('.')[0])
	
	if write:
		filename = changeExtension(filePath, '.nsp')
		outPath = filename if outputDir == None else os.path.join(outputDir, os.path.basename(filename))
		Print.info('Decompressing %s -> %s' % (filePath, outPath))

		if Config.dryRun:
			return outPath

		with Pfs0Stream(outPath) as nsp:
			__decompressContainer(container, nsp, fileHashes, write, raiseVerificationException, statusReportInfo)
		return outPath
	else:
		__decompressContainer(container, None, fileHashes, write, raiseVerificationException, statusReportInfo)

	container.close()
	return None


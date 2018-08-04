#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import pathlib
from Title import Title
import Titles
import Nut
import Config
from binascii import hexlify as hx, unhexlify as uhx
from Nca import PFS0
from Nca import Nca

class Nsp(PFS0):
		
	def __init__(self, path = None, files = None):
		super(Nsp, self).__init__()
		self.path = None
		self.titleId = None
		self.hasValidTicket = None
		
		if path:
			self.setPath(path)
			if files:
				self.pack(files)
				
		if self.titleId and self.isUnlockable():
			print('unlocking ' + self.path)
			self.unlock()
				
	def __iter__(self):
		return self.files.__iter__()
		
	def title(self):
		if not self.titleId:
			raise IOError('NSP no titleId set')
			
		if self.titleId in Titles.keys():
			return Titles.get(self.titleId)
			
		self.title = Title()
		self.title.setId(self.titleId)
		Titles.data()[self.titleId] = self.title
		return self.title
		
	def readMeta(self):
		print(self.path)
		self.open()
		try:
			a = Nca(self.application())
			if a.titleId:
				self.titleId = a.titleId
				self.title().setRightsId(a.rightsId)
		except BaseException as e:
			print('readMeta filed ' + self.path + ", " + str(e))
			raise
		self.close()
			
	def setPath(self, path):
		ext = pathlib.Path(path).suffix
		if ext == '.nsp':
			self.hasValidTicket = True
		elif ext == '.nsx':
			self.hasValidTicket = False
		else:
			return
			
			
		self.path = path
		self.version = '0'
		
		z = re.match('.*\[([a-zA-Z0-9]{16})\].*', path, re.I)
		if z:
			self.titleId = z.groups()[0].upper()
			
			if self.titleId:
				self.title().path = path
		else:
			print('could not get title id from filename, name needs to contain [titleId] : ' + path)
			self.titleId = None

		z = re.match('.*\[v([0-9]+)\].*', path, re.I)
		if z:
			self.version = z.groups()[0]
			
	def open(self, mode = 'rb'):
		super(Nsp, self).open(self.path, mode)
					
	def move(self):
		if not self.path:
			return False
			
		if not self.fileName():
			#print('could not get filename for ' + self.path)
			return False
			
		if os.path.abspath(self.fileName()) == os.path.abspath(self.path):
			return False
			
		if os.path.isfile(self.fileName()) and os.path.abspath(self.path) == os.path.abspath(self.fileName()):
			print('duplicate title: ')
			print(os.path.abspath(self.path))
			print(os.path.abspath(self.fileName()))
			return False
			
		try:
			os.makedirs(os.path.dirname(self.fileName()), exist_ok=True)
			os.rename(self.path, self.fileName())
		except:
			print('failed to rename file! ' + self.path + ' -> ' + self.fileName())
		#print(self.path + ' -> ' + self.fileName())
		
		if self.titleId in Titles.keys():
			Titles.get(self.titleId).path = self.fileName()
		return True
		
	def cleanFilename(self, s):
		s = re.sub('\s+\Demo\s*', ' ', s, re.I)
		s = re.sub('\s*\[DLC\]\s*', '', s, re.I)
		s = re.sub('[\/\\\:\*\?\"\<\>\|\.\s™©®()\~]+', ' ', s)
		return s.strip()
		
	def fileName(self):
		bt = None
		if not self.titleId in Titles.keys():
			if not Title.getBaseId(self.titleId) in Titles.keys():
				print('could not find title key for ' + self.titleId + ' or ' + Title.getBaseId(self.titleId))
				return None
			bt = Titles.get(Title.getBaseId(self.titleId))
			t = Title()
			t.loadCsv(self.titleId + '0000000000000000|0000000000000000|' + bt.name)
		else:
			t = Titles.get(self.titleId)
		
			if not t.baseId in Titles.keys():
				print('could not find baseId for ' + self.path)
				return None
			bt = Titles.get(t.baseId)
		
		if t.isDLC:
			format = Config.paths.titleDLC
		elif t.isDemo:
			if t.idExt != 0:
				format = Config.paths.titleDemoUpdate
			else:
				format = Config.paths.titleDemo
		elif t.idExt != 0:
			format = Config.paths.titleUpdate
		else:
			format = Config.paths.titleBase
			
		format = format.replace('{id}', self.cleanFilename(t.id))
		format = format.replace('{name}', self.cleanFilename(t.name or ''))
		format = format.replace('{version}', str(self.version or 0))
		format = format.replace('{baseId}', self.cleanFilename(bt.id))
		format = format.replace('{baseName}', self.cleanFilename(bt.name or ''))
		
		if self.hasValidTicket:
			format = os.path.splitext(format)[0] + '.nsp'
		else:
			format = os.path.splitext(format)[0] + '.nsx'
		
		return format
		
	def ticket(self):
		for f in (f for f in self if pathlib.Path(f.name).suffix == '.tik'):
			return f
		raise IOError('no ticket in NSP')
		
	def cnmt(self):
		for f in (f for f in self if f.name.endswith('.cnmt.nca')):
			return f
		raise IOError('no cnmt in NSP')
		
	def application(self):
		for f in (f for f in self if f.name.endswith('.nca') and not f.name.endswith('.cnmt.nca')):
			return f
		raise IOError('no application in NSP')
	
	def readTikTitleKey(self):
		t = self.ticket()
		t.seek(0x180)
		return t.read(0x10)
		
	def writeTikTitleKey(self, titleKey):
		t = self.ticket()
		t.seek(0x180)
		
		if t.read(0x10) != b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
			raise IOError('Ticket Title Key has already been set')
		
		t.seek(0x180)
		
		binTitleKey = uhx(titleKey)
		
		if len(binTitleKey) != 16:
			raise IOError('incorrect title key size')
		
		t.write(binTitleKey)
		return True

		
	def isUnlockable(self):
		return (not self.hasValidTicket) and self.titleId and Titles.contains(self.titleId) and Titles.get(self.titleId).key
		
	def unlock(self):
		if not self.isOpen():
			self.open('r+b')

		self.writeTikTitleKey(Titles.get(self.titleId).key)
		self.close()
		self.hasValidTicket = True
		self.move()
			
		
	def pack(self, files):
		if not self.path:
			return False
			
		print_('\tRepacking to NSP...')
		
		hd = self.generateHeader(files)
		
		totSize = len(hd) + sum(os.path.getsize(file) for file in files)
		if os.path.exists(self.path) and os.path.getsize(self.path) == totSize:
			print_('\t\tRepack %s is already complete!' % self.path)
			return
			
		t = tqdm(total=totSize, unit='B', unit_scale=True, desc=os.path.basename(self.path), leave=False)
		
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
		
		print_('\t\tRepacked to %s!' % outf.name)
		outf.close()

	def generateHeader(self, files):
		filesNb = len(files)
		stringTable = '\x00'.join(os.path.basename(file) for file in files)
		headerSize = 0x10 + (filesNb)*0x18 + len(stringTable)
		remainder = 0x10 - headerSize%0x10
		headerSize += remainder
		
		fileSizes = [os.path.getsize(file) for file in files]
		fileOffsets = [sum(fileSizes[:n]) for n in range(filesNb)]
		
		fileNamesLengths = [len(os.path.basename(file))+1 for file in files] # +1 for the \x00
		stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(filesNb)]
		
		header =  b''
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
		
	def printInfo(self, indent = 0):
		super(Nsp, self).printInfo(indent)
		tabs = '\t' * indent
		
		print('\n%sNSP Archive\n\nFiles:' % (tabs))
		
		for f in self:
			print('%s%s' % (tabs, f.name))
			
			if f.name.endswith('.nca'):
				Nca(f).printInfo(indent+1)
			else:
				f.printInfo(indent+1)
			
			print('\n%s%s\n' % (tabs, '*' * 64))

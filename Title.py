#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import json
import CDNSP

class Title:
	def __init__(self):
		self.id = None
		self.rightsId = None
		self.name = None
		self.isDLC = False
		self.idExt = None
		self.updateId = None
		self.path = None
		self.version = None
		self.key = None
		self.isDemo = False
		self.region = None
		self.isModified = False
		
	def loadCsv(self, line, map = ['id', 'key', 'name']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				print('invalid map index')
				continue
				
			methodName = 'set' + str(map[i]).capitalize()
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())
			
		#self.setId(split[0].strip())
		#self.setName(split[2].strip())
		#self.setKey(split[1].strip())

	def setRightsId(self, rightsId):
		if not id:
			self.setId(rightsId)
		elif not self.rightsId:
			self.rightsId = rightsId.upper()
			
	def setId(self, id):
		if not id or self.id:
			return
			
		id = id.upper();
		
		try:
			i = int(id, 16)
		except:
			return
		
		if len(id) == 32:
			self.id = id[:16]
			self.rightsId = id
		elif len(id) == 16:
			self.id = id[:16]
		else:
			return
		
		titleIdNum = int(self.id, 16)
		
		if self.id:
			self.baseId = '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
		else:
			self.baseId = None
		
		self.isDLC = (titleIdNum & 0xFFFFFFFFFFFFE000) != (titleIdNum & 0xFFFFFFFFFFFFF000)
		#self.isBase = self.id == titleIdNum & 0xFFFFFFFFFFFFE000
		self.idExt = titleIdNum & 0x0000000000000FFF
		
		if self.isDLC:
			# dlc
			pass
		elif self.idExt == 0:
			# base
			self.updateId = '%s800' % self.id[:-3]
		else:
			# update
			pass
			
	def setRegion(self, region):
		self.region = region
			
	def setName(self, name):
		if not name:
			return
		self.name = name
		
		if re.match('.*\sDemo\s*$', self.name, re.I) or re.match('.*\sDemo\s+.*$', self.name, re.I):
			self.isDemo = True
		else:
			self.isDemo = False
			
	def setKey(self, key):
		if not key:
			return
			
		key = key.upper()
		
		if len(key) != 32:
			return
			
		try:
			i = int(key, 16)
			
			if i <= 0:
				return
		except:
			return
			
		self.key = key
		
	def setVersion(self, version):
		if version != None:
			self.version = version
		
	def lastestVersion(self):
		#if self.isDLC:
		#	return '0'
			
		if self.version and self.version.lower() == 'none':
			self.version = None
		
		if not self.version:
			self.version = Title.getVersion(self.id)
			
		#print('version: ' + str(self.version))
		return self.version
		
	def isValid(self):
		if self.id:
			return True
		else:
			return False
		
	@staticmethod
	def getVersion(id):
		r = CDNSP.get_version(id)
		
		#if len(r) == 0 or r[0] == 'none':
		#	return ['0']

		return r
			
	@staticmethod
	def getBaseId(id):
		titleIdNum = int(id, 16)
		return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
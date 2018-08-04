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
		self.isUpdate = False
		self.idExt = None
		self.updateId = None
		self.path = None
		self.version = None
		self.key = None
		self.isDemo = False
		self.region = None
		self.isModified = False
	
	def __lt__(self, other):
		return str(self.name) < str(other.name)
		
	def loadCsv(self, line, map = ['id', 'key', 'name']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				print('invalid map index')
				continue
			
			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())
			
		#self.setId(split[0].strip())
		#self.setName(split[2].strip())
		#self.setKey(split[1].strip())
		
	def serialize(self, map = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']):
		r = []
		for i in map:
				
			methodName = 'get' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda: methodName)
			r.append(str(method()))
		return '|'.join(r)
		
	def getIsDLC(self):
		return self.isDLC*1
		
	def getIsUpdate(self):
		return self.isUpdate*1
		
	def getIsDemo(self):
		return self.isDemo*1

	def setRightsId(self, rightsId):
		if not id:
			self.setId(rightsId)
			
		if rightsId and len(rightsId) == 32 and rightsId != '00000000000000000000000000000000':
			self.rightsId = rightsId.upper()
			
	def getRightsId(self):
		return self.rightsId or '00000000000000000000000000000000'
			
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
			self.setRightsId(id)
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
			self.isUpdate = True
			pass
			
	def getId(self):
		return self.id or '0000000000000000'
			
	def setRegion(self, region):
		self.region = region
		
	def getRegion(self):
		return self.region or ''
			
	def setName(self, name):
		if not name:
			return
		self.name = name
		
		if re.match('.*\sDemo\s*$', self.name, re.I) or re.match('.*\sDemo\s+.*$', self.name, re.I):
			self.isDemo = True
		else:
			self.isDemo = False
	
	def getName(self):
		return self.name or ''
			
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
		
	def getKey(self):
		return self.key or '00000000000000000000000000000000'
		
	def setVersion(self, version):
		if version != None:
			self.version = version
			
	def getVersion(self):
		return self.version or ''
		
	def lastestVersion(self, force = False):
		#if self.isDLC:
		#	return '0'
		
		if not self.id:
			return None
			
		if self.version and self.version.lower() == 'none':
			self.version = None
		
		if not self.version or force:
			self.version = Title.getCdnVersion(self.id)
			
		#print('version: ' + str(self.version))
		return self.version
		
	def isValid(self):
		if self.id:
			return True
		else:
			return False
		
	@staticmethod
	def getCdnVersion(id):
		r = CDNSP.get_version(id)
		
		#if len(r) == 0 or r[0] == 'none':
		#	return ['0']

		return r
			
	@staticmethod
	def getBaseId(id):
		titleIdNum = int(id, 16)
		return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import json
import CDNSP
import Titles

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
		self.isDemo = None
		self.region = None
		self.isModified = False
	
	def __lt__(self, other):
		return str(self.name) < str(other.name)
		
	def loadCsv(self, line, map = ['id', 'key', 'name']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				print('invalid map index: ' + str(i) + ', ' + str(len(map)))
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

	def setIsDLC(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isDLC = True
			elif v == 0:
				self.isDLC = False
		except:
			pass
		
	def getIsUpdate(self):
		return self.isUpdate*1

	def setIsUpdate(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isUpdate = True
			elif v == 0:
				self.isUpdate = False
		except:
			pass
		
	def getIsDemo(self):
		try:
			return self.isDemo*1
		except:
			return 0

	def setIsDemo(self, v):
		try:
			v = int(v, 10)
			if v == 1:
				self.isDemo = True
			elif v == 0:
				self.isDemo = False
		except:
			pass

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
		if re.match('[A-Z]{2}', region):
			self.region = region
		
	def getRegion(self):
		return self.region or ''
			
	def setName(self, name):
		if not name:
			return
		self.name = name
		
		if self.isDemo == None:
			if re.match('.*\s[\(\[]?Demo[\)\]]?\s*$', self.name, re.I) or re.match('.*\s[\(\[]?Demo[\)\]]?\s+.*$', self.name, re.I):
				self.isDemo = True
			else:
				self.isDemo = False
	
	def getName(self):
		baseId = Title.getBaseId(self.id)
		if self.isUpdate and Titles.get(baseId):
			return Titles.get(baseId).name
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
		
	def setVersion(self, version, force = False):
		if version != None:
			try:
				n = int(str(version), 10)
			except:
				return
				
			try:
				o = int(str(self.version), 10)
			except:
				o = None
				
			if not o or n > o or force:
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
		if not id:
			return None
		titleIdNum = int(id, 16)
		return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import pathlib
import re
from nut import Status
import time
from nut import Print
import threading
import json
import Fs

global files
files = {}

global lock
lock = threading.Lock()

global hasScanned
global hasLoaded
hasScanned = False
hasLoaded = False

def get(key):
	return files[key]

def getByTitleId(id):
	for k,f in files.items():
		if f.titleId == id:
			return f
	return None
	
def getBaseId(id):
	if not id:
		return None
	titleIdNum = int(id, 16)
	return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)
	
def scan(base, force = False):
	global hasScanned
	#if hasScanned and not force:
	#	return

	hasScanned = True
	i = 0

	fileList = {}

	Print.info(base)
	for root, dirs, _files in os.walk(base, topdown=False, followlinks=True):
		for name in _files:
			suffix = pathlib.Path(name).suffix

			if suffix == '.nsp' or suffix == '.nsx' or suffix == '.nsz':
				path = os.path.abspath(root + '/' + name)
				fileList[path] = name

	if len(fileList) == 0:
		save()
		return 0

	status = Status.create(len(fileList), desc = 'Scanning files...')
	
	try:
		for path, name in fileList.items():
			try:
				status.add(1)

				if not path in files:
					Print.info('scanning ' + name)
					nsp = Fs.Nsp(path, None)
					nsp.getFileSize()
						
					files[nsp.path] = nsp

					i = i + 1
					if i % 20 == 0:
						save()
			except KeyboardInterrupt:
				status.close()
				raise
			except BaseException as e:
				Print.info('An error occurred processing file: ' + str(e))
				raise
		

		save()
		status.close()
	except BaseException as e:
		Print.info('An error occurred scanning files: ' + str(e))
		raise
	return i

def removeEmptyDir(path, removeRoot=True):
	if not os.path.isdir(path):
		return

	# remove empty subfolders
	_files = os.listdir(path)
	if len(_files):
		for f in _files:
			if not f.startswith('.') and not f.startswith('_'):
				fullpath = os.path.join(path, f)
				if os.path.isdir(fullpath):
					removeEmptyDir(fullpath)

	# if folder empty, delete it
	_files = os.listdir(path)
	if len(_files) == 0 and removeRoot:
		Print.info("Removing empty folder:" + path)
		os.rmdir(path)

def load(fileName = 'titledb/files.json'):
	global hasLoaded

	if hasLoaded:
		return

	hasLoaded = True

	try:
		timestamp = time.process_time()

		if os.path.isfile(fileName):
			with open(fileName, encoding="utf-8-sig") as f:
				for k in json.loads(f.read()):
					t = Fs.Nsp(None, None)

					t.path = k['path']
					t.titleId = k['titleId']
					t.version = k['version']
					
					if 'fileSize' in k:
						t.fileSize = k['fileSize']

					if not t.path:
						continue

					path = os.path.abspath(t.path)
					if os.path.isfile(path): 
						files[path] = t #Fs.Nsp(path, None)


	except:
		raise
	Print.info('loaded file list in ' + str(time.process_time() - timestamp) + ' seconds')

def save(fileName = 'titledb/files.json', map = ['id', 'path', 'version', 'fileSize']):
	lock.acquire()
	os.makedirs(os.path.dirname(fileName), exist_ok = True)

	try:
		j = []
		for i,k in files.items():
			k.getFileSize()
			j.append(k.dict())
		with open(fileName, 'w') as outfile:
			json.dump(j, outfile, indent=4, sort_keys=True)
	except:
		lock.release()
		raise
	lock.release()

if os.path.isfile('files.json'):
	os.rename('files.json', 'titledb/files.json')

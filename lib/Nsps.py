#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import Fs
import pathlib
import re
import Status
import time
import Print

global files
files = {}

global hasScanned
global hasLoaded
hasScanned = False
hasLoaded = False

def get(key):
	return files[key]
	
def scan(base):
	global hasScanned
	if hasScanned:
		return

	hasScanned = True
	i = 0

	fileList = {}

	Print.info(base)
	for root, dirs, _files in os.walk(base, topdown=False):
		for name in _files:
			if pathlib.Path(name).suffix == '.nsp' or pathlib.Path(name).suffix == '.nsx':
				path = os.path.abspath(root + '/' + name)
				fileList[path] = name

	status = Status.create(len(fileList), desc = 'Scanning files...')


	for path, name in fileList.items():
		try:
			status.add(1)

			if not path in files:
				Print.info('scanning ' + name)
				nsp = Fs.Nsp(path, None)
						
				files[nsp.path] = nsp
				#files[nsp.path].readMeta()

				i = i + 1
				if i % 20 == 0:
					save()
		except KeyboardInterrupt:
			raise
		except BaseException as e:
			Print.info('An error occurred processing file: ' + str(e))
	save()
	status.close()

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

def load(fileName = 'files.txt', map = ['id', 'path', 'version', 'timestamp', 'hasValidTicket']):
	global hasLoaded

	if hasLoaded:
		return

	hasLoaded = True

	try:
		timestamp = time.clock()
		with open(fileName , encoding="utf-8-sig") as f:
			firstLine = True
			for line in f.readlines():
				line = line.strip()
				if firstLine:
					firstLine = False
					if re.match('[A-Za-z\|\s]+', line, re.I):
						map = line.split('|')
						continue
				t = Fs.Nsp()
				t.loadCsv(line, map)

				if not t.path:
					continue

				path = os.path.abspath(t.path)
				if os.path.isfile(path): 
					files[path] = Fs.Nsp(path, None)
	except:
		pass
	Print.info('loaded file list in ' + str(time.clock() - timestamp) + ' seconds')

def save(fileName = 'files.txt', map = ['id', 'path', 'version', 'timestamp', 'hasValidTicket']):
	buffer = ''
	
	buffer += '|'.join(map) + '\n'
	for t in sorted(list(files.values())):
		buffer += t.serialize(map) + '\n'
		
	with open(fileName, 'w', encoding='utf-8') as csv:
		csv.write(buffer)
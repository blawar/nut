#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import pathlib
import threading
import time

import Fs
from nut import Config, Print, Status, Title

files = {}

lock = threading.Lock()

hasLoaded = False

def get(key):
	return files[key]

def getByTitleId(id_):
	for _, f in files.items():
		if f.titleId == id_:
			return f
	return None

def registerFile(path):
	path = os.path.abspath(path)

	nsp = Fs.Nsp(path, None)
	files[path] = nsp

	if nsp.titleId:
		Title.fileLUT[nsp.titleId].append(nsp)

def unregisterFile(path):
	path = os.path.abspath(path)
	if path not in files:
		return False

	nsp = files[path]

	if nsp.titleId and nsp.titleId in Title.fileLUT:
		#Title.fileLUT[nsp.titleId].remove(nsp)
		Title.fileLUT[nsp.titleId] = [item for item in Title.fileLUT[nsp.titleId] \
			if item.path != nsp.path]
	del files[path]
	return True


def scan(base):
	i = 0

	fileList = {}

	nspOut = os.path.abspath(Config.paths.nspOut)
	duplicatesFolder = os.path.abspath(Config.paths.duplicates)

	Print.info('scanning %s' % base)
	for root, _, _files in os.walk(base, topdown=False):
		for name in _files:
			suffix = pathlib.Path(name).suffix

			if suffix in ('.nsp', '.nsx', '.xci', '.nsz'):
				path = os.path.abspath(root + '/' + name)
				if not path.startswith(nspOut) and not path.startswith(duplicatesFolder):
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
					nsp.timestamp = time.time()
					nsp.getFileSize() # cache file size

					files[nsp.path] = nsp

					i = i + 1
					if i % 20 == 0:
						save()
			except KeyboardInterrupt:
				status.close()
				raise
			except BaseException as e: # pylint: disable=broad-except
				Print.info('An error occurred processing file: ' + str(e))

		save()
		status.close()
	except BaseException as e: # pylint: disable=broad-except
		Print.info('An error occurred scanning files: ' + str(e))
	return i

def removeEmptyDir(path, removeRoot=True):
	if not os.path.isdir(path):
		return

	# remove empty subfolders
	_files = os.listdir(path)
	if len(_files) > 0:
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

def load(fileName = 'titledb/files.json', verify = True):
	global hasLoaded # pylint: disable=global-statement

	if hasLoaded:
		return

	hasLoaded = True

	timestamp = time.perf_counter()

	if os.path.isfile(fileName):
		with open(fileName, encoding="utf-8-sig") as f:
			for k in json.loads(f.read()):
				t = Fs.Nsp(k['path'], None)
				t.timestamp = k['timestamp']
				t.titleId = k['titleId']
				t.version = k['version']

				if 'extractedNcaMeta' in k and k['extractedNcaMeta'] == 1:
					t.extractedNcaMeta = True
				else:
					t.extractedNcaMeta = False

				if 'fileSize' in k:
					t.fileSize = k['fileSize']

				if 'cr' in k:
					t.cr = k['cr']
				else:
					t.cr = None

				if not t.path:
					continue

				path = os.path.abspath(t.path)
				if verify and Config.isScanning:
					if os.path.isfile(path) and os.path.exists(path):
						files[path] = t
				else:
					files[path] = t
	Print.info('loaded file list in ' + str(time.perf_counter() - timestamp) + ' seconds')

def save(fileName = 'titledb/files.json'):
	lock.acquire()

	try:
		j = []
		for _, k in files.items():
			j.append(k.dict())
		with open(fileName, 'w') as outfile:
			json.dump(j, outfile, indent=4, sort_keys=True)
	except:
		lock.release()
		raise
	lock.release()

if os.path.isfile('files.json'):
	os.rename('files.json', 'titledb/files.json')

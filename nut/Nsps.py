#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import pathlib
import threading
import time

import Fs
from nut import Config, Print, Status, Title, Hook

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

def registerFile(path, registerLUT = True):
	path = os.path.abspath(path)

	if not path in files:
		nsp = Fs.Nsp(path, None)
		nsp.timestamp = time.time()
		nsp.getFileSize()

		files[path] = nsp

		Hook.call("files.register", nsp)
	else:
		nsp = files[path]

	if registerLUT and nsp.titleId:
		if nsp.titleId not in Title.fileLUT:
			Title.fileLUT[nsp.titleId] = []

		if nsp not in Title.fileLUT[nsp.titleId]:
			Title.fileLUT[nsp.titleId].append(nsp)

	return nsp

def unregisterFile(path):
	path = os.path.abspath(path)
	if path not in files:
		return False

	nsp = files[path]

	if nsp.titleId and nsp.titleId in Title.fileLUT:
		# Title.fileLUT[nsp.titleId].remove(nsp)
		if nsp.titleId in Title.fileLUT:
			Title.fileLUT[nsp.titleId] = [item for item in Title.fileLUT[nsp.titleId] if item.path != nsp.path]
	del files[path]

	Hook.call("files.unregister", nsp)
	return True

def moveFile(path, newPath):
	path = os.path.abspath(path)
	newPath = os.path.abspath(newPath)

	if path == newPath:
		return False

	if path not in files:
		return registerFile(newPath)

	nsp = files[path]

	nsp.setPath(newPath)
	files[newPath] = nsp
	del files[path]

	Hook.call("files.move", nsp, path)
	return True

def _is_file_hidden(filepath):
	name = os.path.basename(os.path.abspath(filepath))
	return name.startswith('.')

def scan(base):
	i = 0

	fileList = {}

	nspOut = os.path.abspath(Config.paths.nspOut)
	duplicatesFolder = os.path.abspath(Config.paths.duplicates)

	Print.info('scanning %s' % base)
	for root, _, _files in os.walk(base, topdown=False):
		for name in _files:
			if _is_file_hidden(name):
				continue
			suffix = pathlib.Path(name).suffix

			if suffix in ('.nsp', '.nsx', '.xci', '.nsz'):
				path = os.path.abspath(root + '/' + name)
				if not path.startswith(nspOut) and not path.startswith(duplicatesFolder):
					fileList[path] = name

	if len(fileList) == 0:
		save()
		return 0

	status = Status.create(len(fileList), desc='Scanning files...')

	try:
		for path, name in fileList.items():
			try:
				status.add(1)
				path = os.path.abspath(path)

				if path not in files:
					Print.info('scanning ' + name)

					registerFile(path)

					i = i + 1
					#if i % 20 == 0:
					#	save()
			except KeyboardInterrupt:
				status.close()
				raise
			except BaseException as e:  # pylint: disable=broad-except
				Print.info('An error occurred processing file: ' + str(e))

		save()
		status.close()
	except BaseException as e:  # pylint: disable=broad-except
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

def _load_nsp_filesize(json_title, nsp):
	if 'fileSize' in json_title:
		nsp.fileSize = json_title['fileSize']

	if nsp.fileSize is None:
		_path = json_title['path']
		Print.warning(f"Missing file size for `{_path}`. Trying to get size again...")
		_file_size = nsp.getFileSize()
		if _file_size is None:
			return False

	return True

def _fill_nsp_from_json_object(nsp, json_object):
	if 'timestamp' in json_object:
		nsp.timestamp = json_object['timestamp']
	nsp.titleId = json_object['titleId']
	nsp.version = json_object['version']

	if 'extractedNcaMeta' in json_object and json_object['extractedNcaMeta'] == 1:
		nsp.extractedNcaMeta = True
	else:
		nsp.extractedNcaMeta = False

	nsp.cr = json_object['cr'] if 'cr' in json_object else None

def load(fileName='titledb/files.json', verify=True):
	global hasLoaded  # pylint: disable=global-statement

	if hasLoaded:
		return

	hasLoaded = True

	timestamp = time.perf_counter()

	if os.path.isfile(fileName):
		with open(fileName, encoding="utf-8-sig") as f:
			for k in json.loads(f.read()):
				_nsp = Fs.Nsp(k['path'], None)

				if not _load_nsp_filesize(k, _nsp) or not _nsp.path:
					continue

				_fill_nsp_from_json_object(_nsp, k)

				path = os.path.abspath(_nsp.path)
				if verify and Config.isScanning:
					if os.path.isfile(path) and os.path.exists(path) and not _is_file_hidden(path):
						files[path] = _nsp
				else:
					files[path] = _nsp
	Print.info('loaded file list in ' + str(time.perf_counter() - timestamp) + ' seconds')

def save(fileName='titledb/files.json'):
	lock.acquire()

	try:
		j = []
		for _, k in files.items():
			j.append(k.dict())
		with open(fileName, 'w') as outfile:
			json.dump(j, outfile, indent=4, sort_keys=True)
	except BaseException:
		lock.release()
		raise
	lock.release()


if os.path.isfile('files.json'):
	os.rename('files.json', 'titledb/files.json')

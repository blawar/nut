#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import pathlib
from nut import status
import time
from nut import printer
import threading
import json
from nut.nsp import Nsp

files = {}
lock = threading.Lock()
hasScanned = False
hasLoaded = False


def get(key):
    return files[key]


def getByTitleId(id):
    for _, f in files.items():
        if f.titleId == id:
            return f
    return None


def getBaseId(id):
    if not id:
        return None
    titleIdNum = int(id, 16)
    return '{:02X}'.format(titleIdNum & 0xFFFFFFFFFFFFE000).zfill(16)


def scan(base, force=False):
    global hasScanned

    hasScanned = True
    i = 0

    fileList = {}

    printer.info(base)
    for root, _, _files in os.walk(base, topdown=False, followlinks=True):
        for name in _files:
            suffix = pathlib.Path(name).suffix

            if suffix in ['.nsp', '.nsz', '.nsz', '.xci', '.xcz']:
                path = os.path.abspath(root + '/' + name)
                fileList[path] = name

    if len(fileList) == 0:
        save()
        return 0

    progress = status.create(len(fileList), desc='Scanning files...')

    try:
        for path, name in fileList.items():
            try:
                progress.add(1)

                if path not in files:
                    printer.info('scanning ' + name)
                    nsp = Nsp(path, None)
                    nsp.getFileSize()

                    files[nsp.path] = nsp

                    i = i + 1
                    if i % 20 == 0:
                        save()
            except KeyboardInterrupt:
                progress.close()
                raise
            except BaseException as e:
                printer.info('An error occurred processing file: ' + str(e))
                raise

        save()
        progress.close()
    except BaseException as e:
        printer.info('An error occurred scanning files: ' + str(e))
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
        printer.info("Removing empty folder:" + path)
        os.rmdir(path)


def load(fileName='conf/files.json'):
    global hasLoaded

    if hasLoaded:
        return

    hasLoaded = True

    try:
        timestamp = time.process_time()

        if os.path.isfile(fileName):
            with open(fileName, encoding="utf-8-sig") as f:
                for k in json.loads(f.read()):
                    t = Nsp(None, None)

                    t.path = k['path']
                    t.titleId = k['titleId']
                    t.version = k['version']

                    if 'fileSize' in k:
                        t.fileSize = k['fileSize']

                    if not t.path:
                        continue

                    path = os.path.abspath(t.path)
                    if os.path.isfile(path) and os.path.exists(path):
                        files[path] = t  # Fs.Nsp(path, None)

    except:
        raise
    printer.info(f'loaded file list in {time.process_time() - timestamp} ' +
                 'seconds')


def save(
    fileName='conf/files.json',
    map=['id', 'path', 'version', 'fileSize']
):
    lock.acquire()
    os.makedirs(os.path.dirname(fileName), exist_ok=True)

    try:
        j = []
        for _, k in files.items():
            k.getFileSize()
            j.append(k.dict())
        with open(fileName, 'w') as outfile:
            json.dump(j, outfile, indent=4, sort_keys=True)
    except:
        lock.release()
        raise
    lock.release()


if os.path.isfile('files.json'):
    os.rename('files.json', 'conf/files.json')

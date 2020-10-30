#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

from nut_impl import nsps


class Server:
    def __init__(self):
        self.hostname = '0.0.0.0'
        self.port = 9000


class Paths:
    def __init__(self):
        self.scan = ['.']

    def mapping(self):
        m = {}

        if getGdriveCredentialsFile() is not None:
            m['gdrive'] = ''

        unknown = 0
        for f in self.scan:
            bits = f.split('#', 2)
            if len(bits) == 1:
                label = os.path.basename(f)
            else:
                label = bits[1]

            if not label or not len(label) or label == '':
                label = 'L' + str(unknown)
                unknown += 1
            m[label] = bits[0]
        return m


def getGdriveCredentialsFile():
    files = ['credentials.json', 'conf/credentials.json']

    for file in files:
        if os.path.exists(file):
            return file

    return None


paths = Paths()
server = Server()

isRunning = True

region = 'US'
language = 'en'


def set(j, paths, value):
    last = paths.pop()
    for path in paths:
        if path not in j:
            j[path] = {}
        j = j[path]
    j[last] = value


def save(confFile='conf/nut.conf'):
    os.makedirs(os.path.dirname(confFile), exist_ok=True)
    j = {}
    try:
        with open(confFile, encoding="utf8") as f:
            j = json.load(f)
    except json.JSONDecodeError:
        pass

    set(j, ['paths', 'scan'], paths.scan)
    set(j, ['server', 'hostname'], server.hostname)
    set(j, ['server', 'port'], server.port)

    with open(confFile, 'w', encoding='utf-8') as f:
        json.dump(j, f, indent=4)


def load(confFile):
    global paths
    global server

    with open(confFile, encoding="utf8") as f:
        j = json.load(f)

        try:
            paths.scan = j['paths']['scan']
        except KeyError:
            pass

        if not isinstance(paths.scan, list):
            paths.scan = [paths.scan]

        try:
            server.hostname = j['server']['hostname']
        except KeyError:
            pass

        try:
            server.port = int(j['server']['port'])
        except KeyError:
            pass

def updateMainPath(newPath):
    """Function updateMainPath is intended to update a new main path (first element
    with 0 index in the config file).
    NSPs will be cleared (in memory) if path has been changed.

    Parameters:
    newPath (string): a new main path (first element with 0 index in the config file)

    Returns:
    Nothing
    """
    global paths

    pathChanged = False
    oldPath = paths.scan[0]

    if newPath != oldPath:
        pathChanged = True

    if not pathChanged:
        return

    paths.scan[0] = newPath
    save()

    if pathChanged:
        nsps.files.clear()


if os.path.isfile('conf/nut.default.conf'):
    load('conf/nut.default.conf')

if os.path.isfile('conf/nut.conf'):
    load('conf/nut.conf')

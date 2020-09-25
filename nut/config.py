#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path


class Server:
    def __init__(self):
        self.hostname = '0.0.0.0'
        self.port = 9000


class Paths:
    def __init__(self):
        self.scan = ['.']

    @property
    def mapping(self):
        m = {}

        if getGdriveCredentialsFile() is not None:
            m['gdrive'] = ''

        unknown = 0
        for scan_str in self.scan:
            bits = scan_str.split('#', 2)
            if len(bits) == 1:
                label = Path(scan_str).name
            else:
                label = bits[1]

            if not label or not len(label) or label == '':
                label = 'L' + str(unknown)
                unknown += 1
            m[label] = bits[0]
        return m


def getGdriveCredentialsFile():
    files = ['credentials.json', 'conf/credentials.json']

    for _file in files:
        cred_path = Path(_file)
        if cred_path.is_file():
            return _file

    return None


paths = Paths()
server = Server()
isRunning = True
conf_path = Path('conf/nut.conf')


def save():
    conf_path.parent.mkdir(exist_ok=True, parents=True)
    conf = {}

    if conf_path.is_file():
        try:
            with conf_path.open(mode='r', encoding='utf8') as conf_stream:
                conf = json.load(conf_stream)
        except json.JSONDecodeError:
            pass

    conf.update({
        'paths': {
            'scan': paths.scan,
        },
        'server': {
            'hostname': server.hostname,
            'port': server.port,
        },
    })

    with conf_path.open(mode='w', encoding='utf8') as conf_stream:
        json.dump(conf, conf_stream, indent=4)


def load():
    global paths
    global server

    with conf_path.open(mode='r', encoding='utf8') as conf_stream:
        conf = json.load(conf_stream)

        try:
            paths.scan = conf['paths']['scan']
        except KeyError:
            pass

        if not isinstance(paths.scan, list):
            paths.scan = [paths.scan]

        try:
            server.hostname = conf['server']['hostname']
        except KeyError:
            pass

        try:
            server.port = int(conf['server']['port'])
        except KeyError:
            pass


if conf_path.is_file():
    load()

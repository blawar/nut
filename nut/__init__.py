#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut import nsps
from nut import config
from nut import printer

isInitFiles = False
hasScanned = False


def initFiles():
    global isInitFiles
    if isInitFiles:
        return

    isInitFiles = True

    printer.info('Loading NSPs from the configuration file')
    nsps.load()


def scan():
    global hasScanned

    hasScanned = True

    initFiles()

    r = 0

    printer.info('Scanning NSPs on the filesystem')
    for path in config.paths.scan:
        r += nsps.scan(path)
    printer.info('Saving NSPs to the configuration file')
    nsps.save()
    return r

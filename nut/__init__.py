#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut import nsps
from nut import config

isInitFiles = False
hasScanned = False


def initFiles():
    global isInitFiles
    if isInitFiles:
        return

    isInitFiles = True

    nsps.load()


def scan():
    global hasScanned

    hasScanned = True

    initFiles()

    r = 0

    for path in config.paths.scan:
        r += nsps.scan(path)
    nsps.save()
    return r

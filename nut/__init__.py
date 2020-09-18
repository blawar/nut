#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut import Nsps
from nut import Config

isInitFiles = False
hasScanned = False


def initFiles():
    global isInitFiles
    if isInitFiles:
        return

    isInitFiles = True

    Nsps.load()


def scan():
    global hasScanned

    hasScanned = True

    initFiles()

    r = 0

    for path in Config.paths.scan:
        r += Nsps.scan(path)
    Nsps.save()
    return r

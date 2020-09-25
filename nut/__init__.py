#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut import titles
from nut import config

titles_loaded = False


def load_titles():
    global titles_loaded
    if titles_loaded:
        return

    titles_loaded = True

    titles.load()


def scan():
    load_titles()

    scan_count = 0

    for path in config.paths.scan:
        scan_count += titles.scan(path)
    titles.save()
    return scan_count

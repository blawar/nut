#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut_impl import status

enableInfo = True
enableError = True
enableWarning = True
enableDebug = False
silent = False


def info(s):
    if not silent and enableInfo:
        status.print_(s)


def error(s):
    if not silent and enableError:
        status.print_(s)


def warning(s):
    if not silent and enableWarning:
        status.print_(s)


def debug(s):
    if not silent and enableDebug:
        status.print_(s)

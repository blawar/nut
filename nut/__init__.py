from nut import Nsps
from nut import Print
import threading
import time
import colorama
import requests
import queue
import os

isInitTitles = False

def initTitles():
	return

isInitFiles = False
def initFiles():
	global isInitFiles
	if isInitFiles:
		return

	isInitFiles = True

	Nsps.load()

global hasScanned
hasScanned = False

def scan():
	global hasScanned

	hasScanned = True
	initFiles()

	r = Nsps.scan(Config.paths.scan)
	Nsps.save()
	return r
	
global status
status = None


from nut import Nsps
from nut import Print
from nut import Config
from nut import Status
import threading
import time
import requests
import queue
import os

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
	
	r = 0

	for path in Config.paths.scan:
		r += Nsps.scan(path)
	Nsps.save()
	return r

from nut import Nsps
from nut import Print
import threading
import time
import colorama
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
	
global status
status = None


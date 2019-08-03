#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import platform

class Server:
	def __init__(self):
		self.hostname = '0.0.0.0'
		self.port = 9000


		
class Paths:
	def __init__(self):
		self.scan = ['.']
		self.titleDatabase = 'titledb'

		





paths = Paths()
server = Server()

isRunning = True


def set(j, paths, value):
	last = paths.pop()
	for path in paths:
		if not path in j:
			j[path] = {}
		j = j[path]
	j[last] = value

def save(confFile = 'conf/nut.conf'):
	os.makedirs(os.path.dirname(confFile), exist_ok = True)
	j = {}
	try:
		with open(confFile, encoding="utf8") as f:
			j = json.load(f)
	except:
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
		except:
			pass
			
		if not isinstance(paths.scan, list):
			paths.scan = [paths.scan]


		try:
			server.hostname = j['server']['hostname']
		except:
			pass

		try:
			server.port = int(j['server']['port'])
		except:
			pass


if os.path.isfile('conf/nut.default.conf'):
	load('conf/nut.default.conf')

if os.path.isfile('conf/nut.conf'):
	load('conf/nut.conf')


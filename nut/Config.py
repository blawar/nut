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
		
	def mapping(self):
		m = {}
		
		if getGdriveCredentialsFile() is not None:
			m['gdrive'] = ''

		unknown = 0
		for f in self.scan:
			bits = f.split('#', 2)
			if len(bits) == 1:
				label = os.path.basename(f)
			else:
				label = bits[1]
				
			if not label or not len(label) or label == '':
				label = 'L' + str(unknown)
				unknown += 1
			m[label] = bits[0]
		return m


def getGdriveCredentialsFile():
	files = ['credentials.json', 'conf/credentials.json']
	
	for file in files:
		if os.path.exists(file):
			return file
			
	return None




paths = Paths()
server = Server()

isRunning = True

region = 'US'
language = 'en'


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
	
g_regionLanguages = json.loads('{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"],"PE":["en","es"],"KR":["ko"],"HK":["zh"],"NZ":["en"],"AT":["de"],"BE":["fr","nl"],"CZ":["en"],"DK":["en"],"ES":["es"],"FI":["en"],"GR":["en"],"HU":["en"],"NL":["nl"],"NO":["en"],"PL":["en"],"PT":["pt"],"RU":["ru"],"ZA":["en"],"SE":["en"],"MX":["en","es"],"IT":["it"],"CA":["en","fr"],"FR":["fr"],"DE":["de"],"JP":["ja"],"AU":["en"],"GB":["en"],"US":["es", "en"]}')

def regionLanguages(fileName = 'titledb/languages.json'):
	return g_regionLanguages


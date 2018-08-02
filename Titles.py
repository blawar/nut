#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import json
from Title import Title

global titles
titles = {}

def list():
	return titles

def items():
	return titles.items()

def get(key):
	return titles[key]
	
def contains(key):
	return key in titles
	
def set(key, value):
	titles[key] = value
	
#def titles():
#	return titles
	
def keys():
	return titles.keys()
	
def loadTitlekeys(path):
	with open(path, encoding="utf-8-sig") as f:
		firstLine = True
		map = ['id', 'key', 'name']
		for line in f.readlines():
			line = line.strip()
			if firstLine:
				firstLine = False
				if re.match('[A-Za-z\|\s]+', line, re.I):
					map = line.split('|')
					continue
			
			t = Title()
			t.loadCsv(line, map)
			
			if not t.id in keys():
				titles[t.id] = Title()
				
			titles[t.id].loadCsv(line, map)
	
def load():
	if os.path.isfile("titles.json"):	
		with open("titles.json", "r") as f:
			j = json.load(f)
			for id, t in j.items():
				titles[id] = Title()
				
				if t['rightsId']:
					titles[id].setId(t['rightsId'])
				else:
					titles[id].setId(id)
					
				titles[id].setName(t['name'])
				titles[id].setKey(t['key'])
				titles[id].setVersion(t['version'])

			
	files = [f for f in os.listdir('.') if f.endswith('titlekeys.txt')]
	files.sort()
	
	for file in files:
		loadTitlekeys(file)
	
def save():
	j = {}
	for k,t in items():
		if not t.id in j.keys():
			j[t.id] = {}
		
		j[t.id]['name'] = t.name
		
		j[t.id]['key'] = t.key
		
		j[t.id]['rightsId'] = t.rightsId
			
		j[t.id]['version'] = t.version
			
	with open("titles.json", "w+") as f:
		f.write(json.dumps(j))
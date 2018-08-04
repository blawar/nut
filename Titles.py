#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
import json
from Title import Title
import operator

global titles
titles = {}

def data():
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
			#print(str(titles[t.id].id) + ' version ' + str(titles[t.id].version))

	
def load():
	if os.path.isfile("titles.txt"):	
		loadTitlekeys('titles.txt')

			
	files = [f for f in os.listdir('.') if f.endswith('titlekeys.txt')]
	files.sort()
	
	for file in files:
		loadTitlekeys(file)
	
def save():
	map = ['id', 'rightsId', 'key', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']
	buffer = ''
	
	buffer += '|'.join(map) + '\n'
	for t in sorted(list(titles.values())):
		buffer += t.serialize() + '\n'
		
	with open('titles.txt', 'w', encoding='utf-8') as csv:
		csv.write(buffer)
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import Nsp
import pathlib

global files2
files2 = []

global files
files = {}


def list():
	return files2
	
def scan(base):
	print('scanning ' + base)
	for root, dirs, _files in os.walk(base, topdown=False):
		#for name in dirs:
		#	if name[0] != '.':
		#		scan(root + '/' + name)
			
		for name in _files:
			if pathlib.Path(name).suffix == '.nsp' or pathlib.Path(name).suffix == '.nsx':
				files2.append(Nsp.Nsp(root + '/' + name, None))

def removeEmptyDir(path, removeRoot=True):
	if not os.path.isdir(path):
		return

	# remove empty subfolders
	_files = os.listdir(path)
	if len(_files):
		for f in _files:
			if not f.startswith('.') and not f.startswith('_'):
				fullpath = os.path.join(path, f)
				if os.path.isdir(fullpath):
					removeEmptyDir(fullpath)

	# if folder empty, delete it
	_files = os.listdir(path)
	if len(_files) == 0 and removeRoot:
		print("Removing empty folder:" + path)
		os.rmdir(path)
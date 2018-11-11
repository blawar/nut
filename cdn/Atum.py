#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from binascii import hexlify as hx, unhexlify as uhx
from hashlib import sha256
from struct import pack as pk, unpack as upk
from io import TextIOWrapper
import Titles
import requests
import unidecode
import urllib3
import Print
import Status
import Config

quiet = False
truncateName = False
enxhop = False


def makeRequest(method, url, certificate='', hdArgs={}):
	if certificate == '':  # Workaround for defining errors
		certificate = NXclientPath

	fw = '6.1.0-4.0' #hard coding this incase newbs forget to update

	reqHd = {
		'X-Nintendo-DenebEdgeToken': Config.edgeToken.token,
		'User-Agent': 'NintendoSDK Firmware/%s (platform:NX; eid:%s)' % (fw, env),
		'Accept-Encoding': 'gzip, deflate',
		'Accept': '*/*',
		'Connection': 'keep-alive'
	}
	reqHd.update(hdArgs)

	r = requests.request(method, url, cert=certificate, headers=reqHd, verify=False, stream=True)

	if r.status_code == 403:
		raise IOError('Request rejected by server! Check your cert')

	return r


def get_versions(titleId):
	# url = 'https://tagaya.hac.%s.eshop.nintendo.net/tagaya/hac_versionlist' % env
	url = 'https://superfly.hac.%s.d4c.nintendo.net/v1/t/%s/dv' % (env, titleId)
	r = make_request('GET', url)
	j = r.json()

	try:
		if j['error']:
			return ['none']
	except Exception as e:
		pass
	try:
		lastestVer = j['version']
		if lastestVer < 65536:
			return ['%s' % lastestVer]
		else:
			versionList = ('%s' % "-".join(str(i) for i in range(0x10000, lastestVer + 1, 0x10000))).split('-')
			if titleId.endswith("00"):
				return versionList
			return [versionList[0]]
	except Exception as e:
		return ['none']
		
def get_version(titleId):
	# url = 'https://tagaya.hac.%s.eshop.nintendo.net/tagaya/hac_versionlist' % env
	url = 'https://superfly.hac.%s.d4c.nintendo.net/v1/t/%s/dv' % (env, titleId)
	r = make_request('GET', url)
	j = r.json()
	#Print.info('v: ' + str(j))
	try:
		if j['error']:
			return None
	except Exception as e:
		pass
	try:
		return str(j['version'])
	except Exception as e:
		return None
		
def get_versionUpdates():
	url = 'https://tagaya.hac.%s.eshop.nintendo.net/tagaya/hac_versionlist' % env
	r = make_request('GET', url)
	j = r.json()
	r = {}
	try:
		if j['error']:
			return r
	except Exception as e:
		pass
		
	for i in j['titles']:
		try:
			r[i['id']] = i['version']
		except Exception as e:
			pass
	return r

def get_name(titleId):
	titleId = titleId.upper()

	if Titles.contains(titleId):
			try:
				t = Titles.get(titleId)
				return (re.sub(r'[/\\:*?!"|???]+', "", unidecode.unidecode(t.name.strip())))[:70]
			except:
				pass
	return 'Unknown Title'


def download_cetk(rightsID, fPath):
	url = 'https://atum.hac.%s.d4c.nintendo.net/r/t/%s?device_id=%s' % (env, rightsID, deviceId)
	r = make_request('HEAD', url)
	id = r.headers.get('X-Nintendo-Content-ID')

	url = 'https://atum.hac.%s.d4c.nintendo.net/c/t/%s?device_id=%s' % (env, id, deviceId)
	cetk = download_file(url, fPath)

	return cetk



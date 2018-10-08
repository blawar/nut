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
import os
import hashlib
import Title


def makeRequest(method, url, hdArgs={}):

	reqHd = {
		'X-DeviceAuthorization': 'Bearer ' + Config.dauthToken.token,
		'User-Agent': 'NintendoSDK Firmware/%s (platform:NX; eid:%s)' % (Config.cdn.firmware, Config.cdn.environment),
		'Accept-Encoding': 'gzip, deflate',
		'Accept': '*/*',
		'Connection': 'keep-alive'
	}

	reqHd.update(hdArgs)

	r = requests.request(method, url, cert='ShopN.pem', headers=reqHd, verify=False, stream=True)

	if r.status_code == 403:
		raise IOError('Request rejected by server! Check your cert ' + r.text)

	return r

def makeJsonRequest(method, url, hdArgs={}):

	os.makedirs('cache/bugyo/', exist_ok=True)
	cacheFileName = 'cache/bugyo/' + hashlib.md5(url.encode()).hexdigest()
	if os.path.isfile(cacheFileName):
		with open(cacheFileName, encoding="utf-8-sig") as f:
			return json.loads(f.read())

	r = makeRequest(method, url, hdArgs)

	with open(cacheFileName, 'wb') as f:
		f.write(r.text.encode('utf-8'))

	j = r.json()

	try:
		if j['error']:
			return None
	except Exception as e:
		pass

	return j


def scrapeTitles(region = 'US', shop_id = 4):
	pageSize = 50
	offset = 0
	total = 1
	while offset < total:
		#url = 'https://superfly.hac.%s.d4c.nintendo.net/v1/t/%s/dv' % (env, titleId)
		url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles?shop_id=%d&lang=en&country=%s&sort=new&limit=%d&offset=%d' % (Config.cdn.environment, shop_id, region, pageSize, offset)
		#print(url)
		j = makeJsonRequest('GET', url)

		if not j:
			break

		total = int(j['total'])

		try:
			for i in j['contents']:
				title = Titles.getNsuid(i['id'])
				n = getTitleByNsuid(i['id'])

				if title:
					title.parseShogunJson(n)
				else:
					try:
						if n and len(n["applications"]) > 0:
							titleId = n["applications"][0]["id"].upper()
							if titleId:
								if Titles.contains(titleId):
									title = Titles.get(titleId)
									title.parseShogunJson(n)
									#print('existing title found!')
								else:
									title = Title.Title()
									title.id = titleId
									title.parseShogunJson(n)
									Titles.set(titleId, title)
									print('added new title %s %s' % (title.id, title.name))
							else:
								print('Could not get title json!')
						else:
							#print('no title id found in json!')
							pass
					except Exception as e:
						#print(str(e))
						pass

		except Exception as e:
			print(str(e))
			raise
			break

		offset = offset + len(j['contents'])
		Titles.save()
		#break
		
def getTitleByNsuid(nsuId, region = 'US', shop_id = 3):

	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles/%d?shop_id=%d&lang=en&country=%s' % (Config.cdn.environment, nsuId, shop_id, region)
	j = makeJsonRequest('GET', url)

	return j

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
import cdn.Superfly


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

def makeJsonRequest(method, url, hdArgs={}, key = None):
	os.makedirs('cache/bugyo/', exist_ok=True)
	cacheFileName = 'cache/bugyo/' + hashlib.md5(url.encode()).hexdigest()

	if key:
		key = 'cache/bugyo/' + Config.cdn.environment + '/' + key

	j = None

	if os.path.isfile(cacheFileName):
		if not key:
			with open(cacheFileName, encoding="utf-8-sig") as f:
				j = json.loads(f.read())
		else:
			os.makedirs(os.path.dirname(key), exist_ok=True)
			os.rename(cacheFileName, key)

	if key:
		cacheFileName = key
		if os.path.isfile(cacheFileName):
			with open(key, encoding="utf-8-sig") as f:
				j = json.loads(f.read())

	if not j:
		r = makeRequest(method, url, hdArgs)

		os.makedirs(os.path.dirname(cacheFileName), exist_ok=True)

		with open(cacheFileName, 'wb') as f:
			f.write(r.text.encode('utf-8'))

		j = r.json()

	try:
		if j['error']:
			print('error: ' + url)
			return None
	except Exception as e:
		pass

	return j

def country(region = 'US', shop_id=4):
	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/country?shop_id=%d&country=%s' % (Config.cdn.environment, shop_id, region)
	j = makeJsonRequest('GET', url, key = '%d/country/%s.json' % (shop_id, region))
	return j

def countryLanguage(region = 'US'):
	try:
		j = country(region)
		return j['default_language_code']
	except:
		return 'en'

def scrapeTitles(region = 'US', shop_id = 4):
	Print.info('Scraping %s' % region)
	pageSize = 50
	offset = 0
	total = 1
	c = 0
	while offset < total:
		url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles?shop_id=%d&lang=%s&country=%s&sort=new&limit=%d&offset=%d' % (Config.cdn.environment, shop_id, countryLanguage(region), region, pageSize, offset)
		#print(url)
		j = makeJsonRequest('GET', url, {}, '%d/%s/%s/titles/index/%d-%d.json' % (shop_id, countryLanguage(region), region, pageSize, offset))

		if not j:
			break

		total = int(j['total'])

		try:
			for i in j['contents']:
				title = Titles.getNsuid(i['id'])
				n = getTitleByNsuid(i['id'], region)

				if title:

					for x in cdn.Superfly.getAddOns(title.id):
						getNsuIds(x, 'aoc', region)

					title.parseShogunJson(n)

					rt = Title.Title()
					rt.setId(title.id)
					rt.setRegion(region)
					rt.parseShogunJson(n)
					Titles.set(title.id, rt, region)

					scrapeDlc(i['id'], region)
				else:
					try:
						if n and len(n["applications"]) > 0:
							titleId = n["applications"][0]["id"].upper()

							for x in cdn.Superfly.getAddOns(titleId):
								getNsuIds(x, 'aoc', region)

							if titleId:
								if Titles.contains(titleId):
									title = Titles.get(titleId)
									title.setId(titleId)
									title.parseShogunJson(n)
									#print('existing title found!')
								else:
									title = Title.Title()
									title.setId(titleId)
									title.parseShogunJson(n)
									Titles.set(titleId, title)
									print('added new title %s %s' % (title.id, title.name))

								rt = Title.Title()
								rt.setId(titleId)
								rt.setRegion(region)
								rt.parseShogunJson(n)
								Titles.set(titleId, rt, region)

								scrapeDlc(i['id'], region)
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

		#c = c + 1
		#if c % 100 == 0:
		#	Print.info('.')
		#	Titles.save()
	Titles.save()

def scrapeDlc(baseNsuid, region = 'US', shop_id = 3):

	pageSize = 50
	offset = 0
	total = 1
	while offset < total:
		url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles/%d/aocs?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, baseNsuid, shop_id, countryLanguage(region), region)
		#print(url)
		#exit(0)
		j = makeJsonRequest('GET', url, {}, '%d/%s/%s/titles/aocs/%d.json' % (shop_id, countryLanguage(region), region, baseNsuid))

		if not j:
			break

		total = int(j['total'])

		if total == 0:
			break

		try:
			for i in j['contents']:
				title = Titles.getNsuid(i['id'])
				n = getDlcByNsuid(i['id'])

				if title:
					title.parseShogunJson(n, region)

					rt = Title.Title()
					rt.setId(title.id)
					rt.setRegion(region)
					rt.parseShogunJson(n)
					Titles.set(title.id, rt, region)

				else:
					try:
						if n and len(n["applications"]) > 0:
							titleId = n["applications"][0]["id"].upper()
							if titleId:
								if Titles.contains(titleId):
									title = Titles.get(titleId)
									title.setId(titleId)
									title.parseShogunJson(n, region)
									#print('existing title found!')
								else:
									title = Title.Title()
									title.setId(titleId)
									title.parseShogunJson(n, region)
									Titles.set(titleId, title)
									print('added new DLC %s %s' % (title.id, title.name))

								rt = Title.Title()
								rt.setId(titleId)
								rt.setRegion(region)
								rt.parseShogunJson(n, region)
								Titles.set(titleId, rt, region)
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
		
def getTitleByNsuid(nsuId, region = 'US', shop_id = 3):

	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles/%d?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, nsuId, shop_id, countryLanguage(region), region)
	j = makeJsonRequest('GET', url, {}, '%d/%s/%s/titles/%d.json' % (shop_id, countryLanguage(region), region, baseNsuid))

	return j

def getDlcByNsuid(nsuId, region = 'US', shop_id = 3):

	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/aocs/%d?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, nsuId, shop_id, countryLanguage(region), region)
	j = makeJsonRequest('GET', url, {}, '%d/%s/%s/aocs/%d.json' % (shop_id, countryLanguage(region), region, nsuId))
	return j


def ids(titleIds, type='title', region = 'US', shop_id = 4):
	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/contents/ids?shop_id=%d&lang=%s&country=%s&type=%s&title_ids=%s' % (Config.cdn.environment, shop_id, countryLanguage(region), region, type, titleIds)
	j = makeJsonRequest('GET', url, {},  '%d/%s/%s/contents/ids/%s.json' % (shop_id, countryLanguage(region), region, titleIds))
	return j

def getNsuIds(titleIds, type='title', region = 'US', shop_id = 4):
	j = ids(titleIds, type, region, shop_id)
	lst = {}
	try:
		for i in j['id_pairs']:
			titleId = i['title_id'].upper()
			nsuId = int(['id'])
			lst[titleId] = nsuId

			if Titles.contains(titleId):
				Titles.get(titleId).nsuId = nsuId
			else:
				title = Title.Title()
				title.setId(titleId)
				title.nsuId = nsuId
				Titles.set(titleId, title)

	except BaseException as e:
		pass
	return lst
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
from nut import Titles
import requests
import unidecode
import urllib3
from nut import Print
from nut import Status
from nut import Config
import os
import hashlib
from nut import Title
import cdn.Superfly
import cdn


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

def makeJsonRequest(method, url, hdArgs={}, key = None, force = False):
	os.makedirs('cache/bugyo/', exist_ok=True)
	cacheFileName = 'cache/bugyo/' + hashlib.md5(url.encode()).hexdigest()

	if key:
		key = 'cache/bugyo/' + Config.cdn.environment + '/' + key

	j = None

	if cdn.isValidCache(cacheFileName) and not force:
		if not key:
			with open(cacheFileName, encoding="utf-8-sig") as f:
				j = json.loads(f.read())
		else:
			os.makedirs(os.path.dirname(key), exist_ok=True)
			os.rename(cacheFileName, key)

	if key:
		cacheFileName = key
		if cdn.isValidCache(cacheFileName) and not force:
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

def saveLanguages(fileName = 'titledb/languages.json'):
	r = {}
	for region in cdn.regions():
		r[region] = []
		for language in countryLanguages(region):
			r[region].append(language)

	with open(fileName, 'w') as outfile:
			json.dump(r, outfile, indent=4)

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

def countryLanguages(region = 'US'):
	try:
		j = country(region)
		return j['available_language_codes']
	except:
		return [countryLanguage(region)]

def scrapeTitles(region = 'US', shop_id = 4):
	for language in countryLanguages(region):
		scrapeLangTitles(region, language, shop_id)
	Titles.save()

def scrapeLangTitles(region = 'US', language = 'en', shop_id = 4, force = False):
	Print.info('Scraping %s %s' % (region, language))
	pageSize = 50
	offset = 0
	total = 1
	c = 0
	while offset < total:
		url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles?shop_id=%d&lang=%s&country=%s&sort=new&limit=%d&offset=%d' % (Config.cdn.environment, shop_id, language, region, pageSize, offset)
		#print(url)
		j = makeJsonRequest('GET', url, {}, '%d/%s/%s/titles/index/%d-%d.json' % (shop_id, language, region, pageSize, offset), force = False)

		if not j:
			break

		total = int(j['total'])

		try:
			for i in j['contents']:
				scrapeTitle(i['id'], region, language, shop_id)

		except Exception as e:
			print(str(e))
			raise
			break

		offset = offset + len(j['contents'])

	Titles.saveRegion(region, language)

def scrapeTitle(nsuid, region = 'US', language = 'en', shop_id = 3):
	title = Titles.getNsuid(nsuid, region, language)
	n = getTitleByNsuid(nsuid, region, language)

	title.parseShogunJson(n, region, language, True)

	try:
		if n and "applications" in n and len(n["applications"]) > 0:
			titleId = n["applications"][0]["id"].upper()

			if titleId:
				title.setId(titleId)

				for x in cdn.Superfly.getAddOns(titleId):
					getNsuIds(x, 'aoc', region, language)


				scrapeDlc(nsuid, region, language)
			else:
				print('Could not get title json!')
		else:
			#print('no title id found in json!')
			pass

		if n and "demos" in n:
			for d in n["demos"]:
				if "id" in d:
					scrapeTitle(d["id"], region, language, shop_id)
		return title
	except Exception as e:
		print(str(e))
		raise
		return None

def scrapeDlc(baseNsuid, region = 'US', language = 'en', shop_id = 3):

	pageSize = 50
	offset = 0
	total = 1
	while offset < total:
		url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/titles/%d/aocs?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, baseNsuid, shop_id, language, region)
		#print(url)
		#exit(0)
		j = makeJsonRequest('GET', url, {}, '%d/%s/%s/titles/aocs/%d.json' % (shop_id, language, region, baseNsuid))

		if not j:
			break

		total = int(j['total'])

		if total == 0:
			break

		try:
			for i in j['contents']:
				title = Titles.getNsuid(i['id'], region, language)
				n = getDlcByNsuid(i['id'], region, language)

				if n and "applications" in n and len(n["applications"]) > 0:
					title.setId(n["applications"][0]["id"].upper())

				title.parseShogunJson(n, region, language, True)


		except Exception as e:
			print(str(e))
			raise
			break

		offset = offset + len(j['contents'])
		
def getTitleByNsuid(nsuId, region = 'US', language = 'en', shop_id = 3):
	bit = str(nsuId)[0:4]
	if bit == '7003':
		type = 'demos'
	elif bit == '7001':
		type = 'titles'
	elif bit == '7005':
		type = 'aocs'
	elif bit == '7007':
		type = 'bundles'
	else:
		type = 'titles'
	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/%s/%d?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, type, nsuId, shop_id, language, region)
	j = makeJsonRequest('GET', url, {}, '%d/%s/%s/%s/%d.json' % (shop_id, language, region, type, nsuId))

	return j

def getDlcByNsuid(nsuId, region = 'US', language = 'en', shop_id = 3):

	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/aocs/%d?shop_id=%d&lang=%s&country=%s' % (Config.cdn.environment, nsuId, shop_id, language, region)
	j = makeJsonRequest('GET', url, {}, '%d/%s/%s/aocs/%d.json' % (shop_id, language, region, nsuId))
	return j


def ids(titleIds, type='title', region = 'US', language = 'en', shop_id = 4):
	url = 'https://bugyo.hac.%s.eshop.nintendo.net/shogun/v1/contents/ids?shop_id=%d&lang=%s&country=%s&type=%s&title_ids=%s' % (Config.cdn.environment, shop_id, language, region, type, titleIds)
	j = makeJsonRequest('GET', url, {},  '%d/%s/%s/contents/ids/%s.%s.json' % (shop_id, language, region, titleIds, type))
	return j

def getNsuIds(titleIds, type='title', region = 'US', language = 'en', shop_id = 4):
	j = ids(titleIds, type, region, language, shop_id)
	lst = {}
	try:
		for i in j['id_pairs']:
			titleId = i['title_id'].upper()
			nsuId = int(i['id'])
			lst[titleId] = nsuId

			title = Titles.getNsuid(nsuId, region, language)
			title.setId(titleId)

			try:
				pass
				if title.isDLC:
					title.parseShogunJson(getTitleByNsuid(nsuId, region, language), region, language, True)
				elif not title.isUpdate:
					title.parseShogunJson(getTitleByNsuid(nsuId, region, language), region, language, True)
			except:
				Print.error(str(e))
				pass



	except BaseException as e:
		Print.error(str(e))
	return lst
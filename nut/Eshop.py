#!/usr/bin/python3
# -*- coding: utf-8 -*-
# eShop metadata for nut: the replacement of cdn/Shogun.py (bugyo/shogun REST, gone), built on nut/Simba.py
# (Savanna GraphQL). nut code talks to this module only.
#
# nut/Simba.py is a standalone script kept in sync with its own repository (named simba.py there): it never imports
# nut, so fixes and upgrades can be copied either way as the whole file. Everything that fills nut's Titles lives here instead.
#
# Re-exported from simba unchanged (legacy names, arguments and return shapes, the JSON Title.parseSimbaJson reads):
# country, countryLanguage(s), saveLanguages, saveRegions, getTitleByNsuid, getDlcByNsuid, getAocs, getLatest,
# searchPage, ids, REGIONS. region / language are the legacy ones ("US", "en"); shop_id and force are accepted and ignored
# (simba uses SHOP; there is no disk cache).
#
# Scrape functions (cdn/Shogun.py names): scrapeTitle, scrapeNsuids (scrapeTitle for many, batched), scrapeDlc,
# getNsuIds, scrapeLangTitles, scrapeTitles.
#   - scrapeLangTitles (--scrape-simba-delta and the full scrapes) lists the newest LATEST_COUNT (1000, the search
#     maximum) titles first (Simba.latestNsuids, as simba's scrape-all-latest; listed once per store, its other
#     languages reuse the list), then scrapeNsuids.
#   - scrapeNsuids fetches applications SCRAPE_BATCH (15) per request together with their first DLC page
#     (Simba.fetch_apps) and asks only for what a title needs beyond that; bundles, demos and the applications'
#     demos come BATCH (25) per request (Simba.fetch_items). Same Titles result as scrapeTitle per nsUid.
#   - The refresh workers in nut/__init__.py look up base title IDs only, once per store (the id pairs do not depend on
#     the language), IDS_BATCH (200) per ids request (Simba.idsBatched), then scrapeNsuids per language. Settings are
#     simba's environment variables.

import os

from nut import Config, Titles
from nut import Simba
from nut.Simba import (REGIONS, country, countryLanguage, countryLanguages, err, fetch_apps, fetch_items, getAocs,
	getDlcByNsuid, getLatest, getTitleByNsuid, ids, idsBatched, latestNsuids, saveLanguages, saveRegions, searchPage)
from nut.Simba import simba_json as simbaJson

# simba's client certificate is nut's paths.shopNCert (ShopN.pem; nut.conf can move it) unless CERT is set. simba
# reads its CERT global per request, so this also covers nut modules that call simba directly.
if not os.environ.get('CERT'):
	Simba.CERT = Config.paths.shopNCert

# nut.conf cdn.savanna_userAgent replaces simba's User-Agent (Simba.UA, read when its session is created); unset or
# empty keeps simba's own.
if Config.cdn.savanna_userAgent:
	Simba.UA = Config.cdn.savanna_userAgent

# nut.conf cdn.savanna_latestCount: how many of the newest titles scrapeLangTitles (--scrape-simba-delta) lists
# (simba's LATEST_COUNT, read per call; at most 1000, the search maximum) unless LATEST_COUNT is set. Unset or 0 keeps 1000.
if not os.environ.get('LATEST_COUNT') and Config.cdn.savanna_latestCount:
	os.environ['LATEST_COUNT'] = str(Config.cdn.savanna_latestCount)

# nut keeps eShop text as Nintendo wrote it: only line terminators, control characters and stray whitespace are
# cleaned (no ASCII / accent folding or other character replacement).
Simba.WHITESPACE_ONLY = True


def scrapeTitle(nsuid, region='US', language='en', shop_id=3, force=False):
	'''Title (nsUid) into Titles, then its DLC (scrapeDlc) and demos (parentId = the title's id) -> the Title.'''
	return _applyTitle(nsuid, getTitleByNsuid(nsuid, region, language, force=force), region, language, shop_id, force)


def _applyTitle(nsuid, n, region, language, shop_id=3, force=False, dlcFirstPage=None, demos=None):
	'''cdn/Shogun.py's scrapeTitle body for already fetched JSON n (simbaJson): parseSimbaJson, setId from applications[0],
	its DLC (scrapeDlc), its demos (each looked up; parentId = the title's id). demos: a list to collect
	(demo nsUid, parent title id) in instead, for the caller to fetch in batches.'''
	title = Titles.getNsuid(nsuid, region, language)
	title.parseSimbaJson(n, region, language, True)
	if not n:
		return title
	if n.get('applications'):
		tid = (n['applications'][0].get('id') or '').upper()
		if tid:
			title.setId(tid)
			scrapeDlc(nsuid, region, language, force=force, first_page=dlcFirstPage)
	for d in n.get('demos') or []:
		if 'id' in d and demos is not None:
			demos.append((int(d['id']), title.id))
		elif 'id' in d:
			scrapeTitle(d['id'], region, language, shop_id, force=force)
			Titles.getNsuid(d['id'], region, language).setParentId(title.id)
	return title


def scrapeNsuids(nsuids, region='US', language='en', shop_id=3, force=False, label=None):
	'''scrapeTitle for many nsUids, same result per title in far fewer requests: applications (7001...) come from
	Simba.fetch_apps; other nsUids (bundles, demos, DLC) and the applications' demos from Simba.fetch_items, BATCH per
	request. Duplicates are scraped once. Progress on stderr. -> count.'''
	seen, order = set(), []
	for n in nsuids:
		n = int(n)
		if n not in seen:
			seen.add(n)
			order.append(n)
	label = label or '%s %s' % (region, language)
	total, done = len(order), 0
	apps = [n for n in order if str(n)[:4] == '7001']
	demos = []  # (demo nsUid, parent title id) of the applications, fetched with the other items below
	for n, row, ok in fetch_apps(apps, region, language):
		if not ok:  # rejected even alone: the single lookup reports why (and nut's empty entry is kept, as before)
			scrapeTitle(n, region, language, shop_id, force=force)
		else:
			first = ((row.get('dlcItems') or {}).get('items') or []) if row else None
			_applyTitle(n, simbaJson(row, nsuid=n), region, language, shop_id, force, first, demos)
		done += 1
		if done % 15 == 0 or done == len(apps):
			err('%s: %d/%d scraped' % (label, done, total))
	parents = {}
	for d, parent in demos:
		parents.setdefault(d, parent)
	others = [n for n in order if str(n)[:4] != '7001'] + [d for d in parents if d not in seen]
	for n, row, ok in fetch_items(others, region, language):
		if not ok:
			scrapeTitle(n, region, language, shop_id, force=force)
		else:
			_applyTitle(n, simbaJson(row, nsuid=n), region, language, shop_id, force)
		if n in parents:
			Titles.getNsuid(n, region, language).setParentId(parents[n])
		if n in seen:
			done += 1
			if done % 50 == 0 or done == total:
				err('%s: %d/%d scraped' % (label, done, total))
	return total


def scrapeDlc(baseNsuid, region='US', language='en', shop_id=3, force=False, first_page=None):
	'''Every DLC of application baseNsuid into Titles (ids from title_ids, then parseSimbaJson).'''
	j = getAocs(baseNsuid, region, language, force=force, first_page=first_page)
	for n in j['contents']:
		if 'id' not in n:
			continue
		title = Titles.getNsuid(n['id'], region, language)
		title.setIds([i['id'].upper() for key in ('applications', 'title_ids') for i in n.get(key) or [] if 'id' in i])
		title.parseSimbaJson(n, region, language, True)


def getNsuIds(titleIds, type='title', region='US', language='en', shop_id=4, force=False):
	'''ids() into Titles (addId + parseSimbaJson of each found nsUid) -> {titleId: nsUid}.'''
	lst = {}
	for i in (ids(titleIds, type, region, language) or {}).get('id_pairs', []):
		tid, ns = i['title_id'].upper(), int(i['id'])
		lst[tid] = ns
		title = Titles.getNsuid(ns, region, language)
		title.addId(tid)
		if title.isDLC or not title.isUpdate:
			title.parseSimbaJson(getTitleByNsuid(ns, region, language, force=force), region, language, True)
	return lst


def scrapeLangTitles(region='US', language='en', shop_id=4, force=False, refresh=False, save=True):
	'''The newest titles of one store/language (latestNsuids, then scrapeNsuids). Delta and full runs cover the same
	titles (the search cannot list more than 1000). refresh also re-scrapes titles of the region file the search did
	not list. save: Titles.saveRegion afterwards.'''
	err('Scraping %s %s %s' % (region, language, 'full' if force else 'delta'))
	nsuids = latestNsuids(language, region) or []
	err('%s %s: %d titles from the search' % (region, language, len(nsuids)))
	scrapeNsuids(nsuids, region, language, shop_id, force=force)
	if refresh:
		scanned = set(nsuids)
		missed = [t.nsuId for t in list(Titles.data(region, language).values()) if t.nsuId and t.nsuId not in scanned]
		err('%s %s: scanning %d missed titles' % (region, language, len(missed)))
		scrapeNsuids(missed, region, language, shop_id, label='%s %s missed' % (region, language))
	if save:
		Titles.saveRegion(region, language)


def scrapeTitles(region='US', shop_id=4, force=False, refresh=False, save=True):
	'''scrapeLangTitles for every language of region, then Titles.save() (save).'''
	for language in countryLanguages(region):
		scrapeLangTitles(region, language, shop_id, force=force, refresh=refresh)
	if save:
		Titles.save()

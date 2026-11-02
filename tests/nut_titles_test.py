# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest
from unittest import mock

import zstandard

import nut
from nut import Title
from nut import Titles

_BASE_ID = '0100000000010000'
_NEW_ID = '0100000000020000'


def _regionTitle(titleId, nsuId, name):
	t = Title.Title()
	t.setId(titleId)
	t.nsuId = nsuId
	t.name = name
	return t


class TitlesTest(unittest.TestCase):
	"""Tests for titles.json handling in nut/Titles.py (titledb tracks only titles.json.zst)
	"""
	def setUp(self):
		tmp = tempfile.TemporaryDirectory()
		self.addCleanup(tmp.cleanup)
		self.addCleanup(os.chdir, os.getcwd())
		os.chdir(tmp.name)
		os.mkdir('titledb')

		for name, value in (('titles', None), ('regionTitles', {}), ('titlesJsonSaved', False)):
			patcher = mock.patch.object(Titles, name, value)
			patcher.start()
			self.addCleanup(patcher.stop)

	def _writeZst(self, data):
		with open(Titles.TITLES_ZST, 'wb') as f:
			f.write(zstandard.ZstdCompressor().compress(data))

	def test_load_restores_titles_from_zst(self):
		self._writeZst(json.dumps({_BASE_ID: {'id': _BASE_ID, 'name': 'Kept'}}).encode('utf-8'))

		Titles.load()

		self.assertEqual(Titles.titles[_BASE_ID].name, 'Kept')
		self.assertTrue(os.path.isfile(Titles.TITLES_JSON))

	def test_load_prefers_existing_json(self):
		self._writeZst(json.dumps({_BASE_ID: {'id': _BASE_ID, 'name': 'From zst'}}).encode('utf-8'))
		with open(Titles.TITLES_JSON, 'w', encoding='utf-8') as f:
			json.dump({_BASE_ID: {'id': _BASE_ID, 'name': 'From json'}}, f)

		Titles.load()

		self.assertEqual(Titles.titles[_BASE_ID].name, 'From json')

	def test_load_stops_on_unreadable_zst(self):
		with open(Titles.TITLES_ZST, 'wb') as f:
			f.write(b'not a zstd frame')

		with self.assertRaises(zstandard.ZstdError):
			Titles.load()

		self.assertIsNone(Titles.titles)
		self.assertFalse(Titles.confLock.locked())

	def test_save_titles_json_adds_no_empty_titles(self):
		Titles.titles = {}

		Titles.saveTitlesJson({'1': _regionTitle(_NEW_ID, 1, 'Region only')}, 'titledb/US.en.json')

		self.assertEqual(Titles.titles, {})

	def test_save_titles_json_takes_known_rights_id(self):
		known = Title.Title()
		known.setId(_BASE_ID + '0000000000000001')
		Titles.titles = {_BASE_ID: known}

		Titles.saveTitlesJson({'1': _regionTitle(_BASE_ID, 1, 'Known')}, 'titledb/US.en.json')

		with open('titledb/US.en.json', encoding='utf-8') as f:
			saved = json.load(f)
		self.assertEqual(saved['1']['rightsId'], known.rightsId)

	def test_import_region_brings_region_metadata_into_titles(self):
		blank = Title.Title()
		blank.setId(_BASE_ID)
		Titles.titles = {_BASE_ID: blank}
		Titles.regionTitles = {'US': {'en': {'1': _regionTitle(_BASE_ID, 1, 'Named'), '2': _regionTitle(_NEW_ID, 2, 'New')}}}

		with mock.patch('nut.Config.regionLanguages', return_value={'US': ['en']}):
			nut.importRegion('US', 'en', save=False)

		self.assertEqual(Titles.titles[_BASE_ID].name, 'Named')
		self.assertEqual(Titles.titles[_NEW_ID].name, 'New')

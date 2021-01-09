#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import unittest
from pathlib import Path

from pyfakefs.fake_filesystem_unittest import TestCase

from nut import Nsps, Print
from nut import Config

Print.enableDebug = True

def _get_default_config_object():
	return {'paths': {'titleBase': 'titles/{name}[{id}][v{version}].nsp', 'titleDLC':
					  'titles/DLC/{name}[{id}][v{version}].nsp', 'titleUpdate':
					  'titles/updates/{name}[{id}][v{version}].nsp', 'titleDemo':
					  'titles/demos/{name}[{id}][v{version}].nsp', 'titleDemoUpdate':
					  'titles/demos/updates/{name}[{id}][v{version}].nsp', 'nsxTitleBase': None,
					  'nsxTitleDLC': None, 'nsxTitleUpdate': None, 'nsxTitleDemo': None,
					  'nsxTitleDemoUpdate': None, 'nszTitleBase': None, 'nszTitleDLC': None,
					  'nszTitleUpdate': None, 'nszTitleDemo': None, 'nszTitleDemoUpdate': None,
					  'xciTitleBase': None, 'xciTitleDLC': None, 'xciTitleUpdate': None, 'xciTitleDemo': None,
					  'xciTitleDemoUpdate': None, 'scan': ['.'], 'titleDatabase': 'titledb',
					  'keys': 'keys.txt', 'calibration': 'PRODINFO.bin', 'shopNCert': 'ShopN.pem',
					  'nspOut': '_NSPOUT', 'titleImages': 'titles/images/', 'duplicates': 'duplicates/'},
			'compression': {'level': 19, 'auto': False}, 'pullUrls': [], 'threads': 1, 'download':
			{'base': True, 'demo': False, 'DLC': True, 'update': False,
			 'sansTitleKey': False, 'deltas': False, 'regions': [], 'rankMin': None, 'rankMax': None,
			 'fileSizeMax': None, 'fileSizeMin': None, 'ratingMin': None, 'ratingMax': None,
			 'releaseDateMin': None, 'releaseDateMax': None}, 'server': {'hostname': '0.0.0.0',
																		 'port': 9000}, 'autolaunchBrowser': True, 'autoUpdateTitleDb': True}

def _get_default_config_path():
	return 'conf/nut.conf'

def _create_empty_config_file(fs):
	conf_file = _get_default_config_path()
	fs.create_file(conf_file)
	return conf_file

def _create_files(fs, folder_obj):
	for f in folder_obj["files"]:
		fs.create_file(os.path.join(folder_obj["path"], f))


def _get_default_languages():
	return json.loads('{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"],\
		"PE":["en","es"],"KR":["ko"],"HK":["zh"],"CN":["zh"],"NZ":["en"],"AT":["de"],\
		"BE":["fr","nl"],"CZ":["en"],"DK":["en"],"ES":["es"],"FI":["en"],"GR":["en"],\
		"HU":["en"],"NL":["nl"],"NO":["en"],"PL":["en"],"PT":["pt"],"RU":["ru"],"ZA":["en"],\
		"SE":["en"],"MX":["en","es"],"IT":["it"],"CA":["en","fr"],"FR":["fr"],"DE":["de"],\
		"JP":["ja"],"AU":["en"],"GB":["en"],"US":["es", "en"]}')


class NutConfigTest(TestCase):
	"""Tests for nut/Config.py
	"""

	def setUp(self):
		self.setUpPyfakefs(modules_to_reload=[Config])

	def test_default_region(self):
		self.assertEqual(Config.region, 'US')

	def test_default_language(self):
		self.assertEqual(Config.language, 'en')

	def test_set(self):
		paths = Config.Paths()
		server = Config.Server()
		j = {}
		Config.set(j, ['paths', 'scan'], paths.scan)
		Config.set(j, ['server', 'hostname'], server.hostname)
		Config.set(j, ['server', 'port'], server.port)

		self.assertEqual(j['paths']['scan'], paths.scan)
		self.assertEqual(j['server']['hostname'], server.hostname)
		self.assertEqual(j['server']['port'], server.port)

	def test_get_gdrive_credentials_file_without_files(self):
		self.assertIsNone(Config.getGdriveCredentialsFile())

	def test_get_gdrive_credentials_file_with_credentials_file(self):
		self.fs.create_file('credentials.json')
		self.assertIsNotNone(Config.getGdriveCredentialsFile())

	def test_get_gdrive_credentials_file_with_conf_credentials_file(self):
		self.fs.create_file('conf/credentials.json')
		self.assertIsNotNone(Config.getGdriveCredentialsFile())

	def test_load_non_existing_file(self):
		with self.assertRaises(OSError):
			Config.load(_get_default_config_path())
		self.assertListEqual(Config.paths.scan, ['.'])
		self.assertEqual(Config.server.hostname, '0.0.0.0')
		self.assertEqual(Config.server.port, 9000)

	def test_load_conf_default(self):
		conf_file = 'conf/nut.default.conf'
		conf_content = """
{
	"paths": {
		"scan": ["./"]
	},
	"server": {
		"hostname": "127.0.0.1",
		"port": 9005
	}
}
"""
		self.fs.create_file(conf_file, contents=conf_content)
		Config.load(conf_file)
		self.assertListEqual(Config.paths.scan, ['./'])
		self.assertEqual(Config.server.hostname, '127.0.0.1')
		self.assertEqual(Config.server.port, 9005)

	def __compare_config_in_file_with_object(self, conf_file, obj):
		self.assertTrue(os.path.exists(conf_file))
		with open(conf_file, 'r', encoding="utf8") as f:
			obj_from_file = json.load(f)
			self.assertEqual(obj_from_file, obj)

	def test_save_default_config_with_explicit_config_path(self):
		conf_file = _get_default_config_path()
		self.assertFalse(os.path.exists(conf_file))
		Config.save(conf_file)
		self.__compare_config_in_file_with_object(conf_file, _get_default_config_object())

	def test_save_default_config_with_implicit_config_path(self):
		conf_file = _get_default_config_path()
		self.assertFalse(os.path.exists(conf_file))
		Config.save()
		self.__compare_config_in_file_with_object(conf_file, _get_default_config_object())

	def test_save_custom_config_with_explicit_config_path(self):
		conf_file = _create_empty_config_file(self.fs)

		nsps_folder = "/Users/user1/Nsps"
		server_hostname = "127.0.0.1"
		server_port = 9001

		Config.paths.scan = [nsps_folder]
		Config.server.hostname = server_hostname
		Config.server.port = server_port

		object_to_compare = _get_default_config_object()
		object_to_compare["paths"]["scan"] = [nsps_folder]
		server = object_to_compare["server"]
		server["hostname"] = server_hostname
		server["port"] = server_port

		Config.save(conf_file)
		self.__compare_config_in_file_with_object(conf_file, object_to_compare)

	def test_update_scan_paths_for_default_config_and_empty_Nsps(self):
		_create_empty_config_file(self.fs)

		self.assertEqual(Config.paths.scan, ['.'])
		new_paths = ['/Users/user1/path1', '/Users/user1/path2']
		Config.update_scan_paths(new_paths, Nsps.files)
		self.assertEqual(Config.paths.scan, new_paths)

	def test_update_main_path_clears_out_Nsps(self):
		_create_empty_config_file(self.fs)

		new_paths = ["folder2"]
		folder1 = {"path": Config.paths.scan[0],
				   "files": ["title1 [abcdefa112345678].nsp", "title2 [abcdefa212345678].nsp"]}

		Nsps.files = {"files": folder1["files"]}

		Config.update_scan_paths(new_paths, Nsps.files)
		self.assertEqual(Nsps.files, {})

	def test_update_scan_paths_with_same_path(self):
		_old_nsp_files = Nsps.files
		initial_scan_paths = ['.']
		Config.paths.scan = initial_scan_paths
		initial_nsp_files = {"1.nsp", "2.nsp"}
		Nsps.files = initial_nsp_files
		Config.update_scan_paths(initial_scan_paths, Nsps.files)
		self.assertEqual(Config.paths.scan, initial_scan_paths)
		self.assertEqual(Nsps.files, initial_nsp_files)
		Nsps.files = _old_nsp_files

	def test_update_scan_paths_with_single_path(self):
		initial_scan_paths = ['.']
		Config.paths.scan = initial_scan_paths
		new_scan_path = "titles"
		Config.update_scan_paths(new_scan_path, Nsps.files)
		self.assertEqual(Config.paths.scan, [new_scan_path])

	def test_region_languages_with_empty_file(self):
		self.assertEqual(Config.regionLanguages(), _get_default_languages())
		# return same object
		self.assertEqual(Config.regionLanguages(), _get_default_languages())

	def test_regional_languages_from_file(self):
		file_ = 'titledb/languages.json'
		languages = '{"CO":["en","es"],"AR":["en","es"],"CL":["en","es"]}'
		self.fs.create_file(file_, contents=languages)
		self.assertEqual(Config.regionLanguages(), json.loads(languages))


class NutConfigServerTest(TestCase):
	"""Tests for nut/Config.py Server
	"""

	def setUp(self):
		self.setUpPyfakefs(modules_to_reload=[Config])

	def test_default_hostname(self):
		self.assertEqual(Config.server.hostname, '0.0.0.0')

	def test_default_port(self):
		self.assertEqual(Config.server.port, 9000)

class NutConfigPathsTest(TestCase):
	"""Tests for nut/Config.py Paths
	"""

	def setUp(self):
		self.setUpPyfakefs(modules_to_reload=[Config])

	def test_init(self):
		self.assertListEqual(Config.paths.scan, ['.'])

	def test_mapping_default(self):
		self.assertEqual(Config.paths.mapping(), {'.': '.'})

	def test_mapping_with_gdrive_credentials_file(self):
		self.assertIsNone(Config.getGdriveCredentialsFile())
		self.fs.create_file('credentials.json')
		self.assertEqual(Config.paths.mapping()['gdrive'], '')
		self.assertEqual(Config.paths.mapping()['.'], '.')

	def test_get_title_base(self):
		path = Path('titles')
		self.assertEqual(Config.paths.getTitleBase(False, None), None)
		self.assertEqual(Path(Config.paths.getTitleBase(False, 'name [123][v0].nsp')), Path(Config.paths.titleBase))
		self.assertEqual(Path(Config.paths.getTitleBase(False, 'name [123][v0].nsz')), \
			path / 'nsz' / '{name}[{id}][v{version}].nsz')
		self.assertEqual(Path(Config.paths.getTitleBase(False, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsp')
		self.assertEqual(Path(Config.paths.getTitleBase(False, 'name [123][v0].xci')), \
			path / 'xci' / '{name}[{id}][v{version}].xci')

		self.assertEqual(Path(Config.paths.getTitleBase(True, 'name [123][v0].nsp')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleBase(True, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')


	def test_get_title_dlc(self):
		path = Path('titles') / 'DLC'
		self.assertEqual(Config.paths.getTitleDLC(False, None), None)
		self.assertEqual(Path(Config.paths.getTitleDLC(False, 'name [123][v0].nsp')), Path(Config.paths.titleDLC))
		self.assertEqual(Path(Config.paths.getTitleDLC(False, 'name [123][v0].nsz')), \
			path / 'nsz' / '{name}[{id}][v{version}].nsz')
		self.assertEqual(Path(Config.paths.getTitleDLC(False, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsp')
		self.assertEqual(Path(Config.paths.getTitleDLC(False, 'name [123][v0].xci')), \
			path / 'xci' / '{name}[{id}][v{version}].xci')

		self.assertEqual(Path(Config.paths.getTitleDLC(True, 'name [123][v0].nsp')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleDLC(True, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')

	def test_get_title_update(self):
		path = Path('titles') / 'updates'
		self.assertEqual(Config.paths.getTitleUpdate(False, None), None)
		self.assertEqual(Path(Config.paths.getTitleUpdate(False, 'name [123][v0].nsp')), Path(Config.paths.titleUpdate))
		self.assertEqual(Path(Config.paths.getTitleUpdate(False, 'name [123][v0].nsz')), \
			path / 'nsz' / '{name}[{id}][v{version}].nsz')
		self.assertEqual(Path(Config.paths.getTitleUpdate(False, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleUpdate(False, 'name [123][v0].xci')), \
			path / 'xci' / '{name}[{id}][v{version}].xci')

		self.assertEqual(Path(Config.paths.getTitleUpdate(True, 'name [123][v0].nsp')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleUpdate(True, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')

	def test_get_title_demo(self):
		path = Path('titles') / 'demos'
		self.assertEqual(Config.paths.getTitleDemo(False, None), None)
		self.assertEqual(Path(Config.paths.getTitleDemo(False, 'name [123][v0].nsp')), Path(Config.paths.titleDemo))
		self.assertEqual(Path(Config.paths.getTitleDemo(False, 'name [123][v0].nsz')), \
			path / 'nsz' / '{name}[{id}][v{version}].nsz')
		self.assertEqual(Path(Config.paths.getTitleDemo(False, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsp')
		self.assertEqual(Path(Config.paths.getTitleDemo(False, 'name [123][v0].xci')), \
			path / 'xci' / '{name}[{id}][v{version}].xci')

		self.assertEqual(Path(Config.paths.getTitleDemo(True, 'name [123][v0].nsp')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleDemo(True, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')

	def test_get_title_demo_update(self):
		path = Path('titles') / 'demos' / 'updates'
		self.assertEqual(Config.paths.getTitleDemoUpdate(False, None), None)
		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(False, 'name [123][v0].nsp')), Path(Config.paths.titleDemoUpdate))
		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(False, 'name [123][v0].nsz')), \
			path / 'nsz' / '{name}[{id}][v{version}].nsz')
		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(False, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsp')
		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(False, 'name [123][v0].xci')), \
			path / 'xci' / '{name}[{id}][v{version}].xci')

		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(True, 'name [123][v0].nsp')), \
			path / '{name}[{id}][v{version}].nsx')
		self.assertEqual(Path(Config.paths.getTitleDemoUpdate(True, 'name [123][v0].nsx')), \
			path / '{name}[{id}][v{version}].nsx')


if __name__ == "__main__":
	unittest.main()

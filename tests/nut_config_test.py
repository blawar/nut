#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import unittest

from pyfakefs.fake_filesystem_unittest import TestCase

from nut import Nsps, Print
from nut import Config

Print.enableDebug = True

def _get_default_config_object():
	return {'paths': {'titleBase': 'titles/{name}[{id}][v{version}].nsp', 'titleDLC': 'titles/DLC/{name}[{id}][v{version}].nsp', \
		'titleUpdate': 'titles/updates/{name}[{id}][v{version}].nsp', 'titleDemo': 'titles/demos/{name}[{id}][v{version}].nsp', \
			'titleDemoUpdate': 'titles/demos/updates/{name}[{id}][v{version}].nsp', 'nsxTitleBase': None, 'nsxTitleDLC': None, \
			'nsxTitleUpdate': None, 'nsxTitleDemo': None, 'nsxTitleDemoUpdate': None, 'nszTitleBase': None, 'nszTitleDLC': None, \
			'nszTitleUpdate': None, 'nszTitleDemo': None, 'nszTitleDemoUpdate': None, 'xciTitleBase': None, \
			'xciTitleDLC': None, 'xciTitleUpdate': None, 'xciTitleDemo': None, 'xciTitleDemoUpdate': None, \
			'scan': ['.'], 'titleDatabase': 'titledb', 'hactool': '', 'keys': 'keys.txt', \
			'calibration': 'PRODINFO.bin', 'shopNCert': 'ShopN.pem', 'nspOut': '_NSPOUT', \
			'titleImages': 'titles/images/', 'duplicates': 'duplicates/'}, 'compression': \
			{'level': 19, 'auto': False}, 'pullUrls': [], 'threads': 1, 'download': \
			{'downloadBase': True, 'demo': False, 'DLC': True, 'update': False, \
			'sansTitleKey': False, 'deltas': False, 'regions': [], 'rankMin': None, 'rankMax': None, 'fileSizeMax': None, \
			'fileSizeMin': None, 'ratingMin': None, 'ratingMax': None, 'releaseDateMin': None, 'releaseDateMax': None}, \
				'server': {'hostname': '0.0.0.0', 'port': 9000}, 'autolaunchBrowser': True, 'autoUpdateTitleDb': True}

def _get_default_config_path():
	return 'conf/nut.conf'

def _create_empty_config_file(fs):
	conf_file = _get_default_config_path()
	fs.create_file(conf_file)
	return conf_file

def _create_files(fs, folder_obj):
	for f in folder_obj["files"]:
		fs.create_file(os.path.join(folder_obj["path"], f))


class NutConfigTest(TestCase):
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
			# ignoring platform-specific config value
			obj_from_file["paths"]['hactool'] = ''
			obj["paths"]['hactool'] = ''
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
		folder1 = {"path": Config.paths.scan[0], \
			"files": ["title1 [abcdefa112345678].nsp", "title2 [abcdefa212345678].nsp"]}

		Nsps.files = {"files": folder1["files"]}

		Config.update_scan_paths(new_paths, Nsps.files)
		self.assertEqual(Nsps.files, {})


class NutConfigServerTest(TestCase):
	def setUp(self):
		self.setUpPyfakefs(modules_to_reload=[Config])

	def test_default_hostname(self):
		self.assertEqual(Config.server.hostname, '0.0.0.0')

	def test_default_port(self):
		self.assertEqual(Config.server.port, 9000)

class NutConfigPathsTest(TestCase):
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


if __name__ == "__main__":
	unittest.main()

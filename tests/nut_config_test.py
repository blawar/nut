#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import unittest

from pyfakefs.fake_filesystem_unittest import TestCase
from nut_impl import config


def _get_default_config_object():
    return {'paths': {'scan': ['.']}, 'server': {'hostname': '0.0.0.0', 'port': 9000}}

def _get_default_config_path():
    return 'conf/nut.conf'


class NutConfigTest(TestCase):
    def setUp(self):
        self.setUpPyfakefs(modules_to_reload=[config])

    def test_default_region(self):
        self.assertEqual(config.region, 'US')

    def test_default_language(self):
        self.assertEqual(config.language, 'en')

    def test_set(self):
        paths = config.Paths()
        server = config.Server()
        j = {}
        config.set(j, ['paths', 'scan'], paths.scan)
        config.set(j, ['server', 'hostname'], server.hostname)
        config.set(j, ['server', 'port'], server.port)

        self.assertEqual(j['paths']['scan'], paths.scan)
        self.assertEqual(j['server']['hostname'], server.hostname)
        self.assertEqual(j['server']['port'], server.port)

    def test_get_gdrive_credentials_file_without_files(self):
        self.assertIsNone(config.getGdriveCredentialsFile())

    def test_get_gdrive_credentials_file_with_credentials_file(self):
        self.fs.create_file('credentials.json')
        self.assertIsNotNone(config.getGdriveCredentialsFile())

    def test_get_gdrive_credentials_file_with_conf_credentials_file(self):
        self.fs.create_file('conf/credentials.json')
        self.assertIsNotNone(config.getGdriveCredentialsFile())

    def test_load_non_existing_file(self):
        with self.assertRaises(OSError):
            config.load(_get_default_config_path())
        self.assertListEqual(config.paths.scan, ['.'])
        self.assertEqual(config.server.hostname, '0.0.0.0')
        self.assertEqual(config.server.port, 9000)

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
        config.load(conf_file)
        self.assertListEqual(config.paths.scan, ['./'])
        self.assertEqual(config.server.hostname, '127.0.0.1')
        self.assertEqual(config.server.port, 9005)

    def __compare_config_in_file_with_object(self, conf_file, obj):
        self.assertTrue(os.path.exists(conf_file))
        with open(conf_file, 'r', encoding="utf8") as f:
            obj_from_file = json.load(f)
            self.assertEqual(obj_from_file, obj)

    def test_save_default_config_with_explicit_config_path(self):
        conf_file = _get_default_config_path()
        self.assertFalse(os.path.exists(conf_file))
        with self.assertRaises(OSError):
            config.save(conf_file)
        self.fs.create_file(conf_file)
        config.save(conf_file)
        self.__compare_config_in_file_with_object(conf_file, _get_default_config_object())

    def test_save_default_config_with_implicit_config_path(self):
        conf_file = _get_default_config_path()
        self.assertFalse(os.path.exists(conf_file))
        with self.assertRaises(OSError):
            config.save()
        self.fs.create_file(conf_file)
        config.save()
        self.__compare_config_in_file_with_object(conf_file, _get_default_config_object())

    def test_save_custom_config_with_explicit_config_path(self):
        conf_file = _get_default_config_path()
        self.fs.create_file(conf_file)
        nsps_folder = "/Users/user1/nsps"
        server_hostname = "127.0.0.1"
        server_port = 9001

        config.paths.scan = [nsps_folder]
        config.server.hostname = server_hostname
        config.server.port = server_port

        object_to_compare = {'paths': {'scan': [nsps_folder]}, 'server': {\
            'hostname': server_hostname, 'port': server_port}}

        config.save(conf_file)
        self.__compare_config_in_file_with_object(conf_file, object_to_compare)


class NutConfigServerTest(TestCase):
    def setUp(self):
        self.setUpPyfakefs(modules_to_reload=[config])

    def test_default_hostname(self):
        self.assertEqual(config.server.hostname, '0.0.0.0')

    def test_default_port(self):
        self.assertEqual(config.server.port, 9000)

class NutConfigPathsTest(TestCase):
    def setUp(self):
        self.setUpPyfakefs(modules_to_reload=[config])

    def test_init(self):
        self.assertListEqual(config.paths.scan, ['.'])

    def test_mapping_default(self):
        self.assertEqual(config.paths.mapping(), {'.': '.'})

    def test_mapping_with_gdrive_credentials_file(self):
        self.assertIsNone(config.getGdriveCredentialsFile())
        self.fs.create_file('credentials.json')
        self.assertEqual(config.paths.mapping()['gdrive'], '')
        self.assertEqual(config.paths.mapping()['.'], '.')


if __name__ == "__main__":
    unittest.main()

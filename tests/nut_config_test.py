#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from nut_impl import config

class NutConfigTest(unittest.TestCase):
    def test_default_region(self):
        self.assertEqual(config.region, 'US')
    
    def test_default_language(self):
        self.assertEqual(config.language, 'en')

    def test_set_paths(self):
        paths = config.Paths()
        server = config.Server()
        j = {}
        config.set(j, ['paths', 'scan'], paths.scan)
        config.set(j, ['server', 'hostname'], server.hostname)
        config.set(j, ['server', 'port'], server.port)

        self.assertEqual(j['paths']['scan'], paths.scan)
        self.assertEqual(j['server']['hostname'], server.hostname)
        self.assertEqual(j['server']['port'], server.port)

class NutConfigServerTest(unittest.TestCase):
    def test_default_hostname(self):
        self.assertEqual(config.server.hostname, '0.0.0.0')

    def test_default_port(self):
        self.assertEqual(config.server.port, 9000)

class NutConfigPathsTest(unittest.TestCase):
    def test_init(self):
        self.assertListEqual(config.paths.scan, ['.'])

if __name__ == "__main__":
    unittest.main()
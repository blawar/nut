#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib
import os
import tempfile
import unittest

from nut import Config, Keys, Print

KEYS_CONTENT = """aes_kek_generation_source = 0123456789ABCDEFFEDCBA9876543210
aes_key_generation_source = 0123456789ABCDEFFEDCBA9876543210
titlekek_source = 0123456789ABCDEFFEDCBA9876543210
key_area_key_application_source = 0123456789ABCDEFFEDCBA9876543210
key_area_key_ocean_source = 0123456789ABCDEFFEDCBA9876543210
key_area_key_system_source = 0123456789ABCDEFFEDCBA9876543210
master_key_00 = 0123456789ABCDEFFEDCBA9876543210
"""


class NutKeysConfigPathTest(unittest.TestCase):
	"""Tests that nut/Keys.py loads the keys file from Config.paths.keys
	"""

	def setUp(self):
		self.original_keys_path = Config.paths.keys
		self.tmp_dir = tempfile.TemporaryDirectory()

	def tearDown(self):
		Config.paths.keys = self.original_keys_path
		importlib.reload(Keys)
		self.tmp_dir.cleanup()

	def test_keys_are_loaded_from_configured_path(self):
		keys_file = os.path.join(self.tmp_dir.name, 'custom.keys')
		with open(keys_file, 'w', encoding='utf8') as f:
			f.write(KEYS_CONTENT)

		Config.paths.keys = keys_file
		importlib.reload(Keys)

		self.assertEqual(Keys.keys.get('master_key_00'),
						 '0123456789ABCDEFFEDCBA9876543210')
		# the load ran to completion, so the title kek was derived
		# from master_key_00 instead of left as the zero placeholder
		self.assertNotEqual(Keys.titleKeks[0], '0' * 32)
		self.assertIn(0, Keys.getKeyGens())

	def test_missing_configured_path_error_names_that_path(self):
		missing_file = os.path.join(self.tmp_dir.name, 'missing.keys')
		Config.paths.keys = missing_file

		errors = []
		original_error = Print.error
		Print.error = errors.append
		try:
			importlib.reload(Keys)
		finally:
			Print.error = original_error

		self.assertEqual(Keys.keys, {})
		self.assertTrue(any(missing_file in message for message in errors),
						'startup error should name the configured path, got: %r' % errors)


if __name__ == "__main__":
	unittest.main()

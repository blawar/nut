#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from nut import Hex

_BINARY_DATA = b"binary"

class NutHexTest(unittest.TestCase):
	"""Tests for nut/Config.py
	"""

	def test_buffer_to_hex(self):
		self.assertEqual(Hex.bufferToHex(_BINARY_DATA, 0, len(_BINARY_DATA)), '62 69 6E 61 72 79 ')
		with self.assertRaises(IndexError):
			self.assertEqual(Hex.bufferToHex(_BINARY_DATA, 0, len(_BINARY_DATA)+1), '')

	def test_buffer_to_ascii(self):
		self.assertEqual(Hex.bufferToAscii(_BINARY_DATA, 0, len(_BINARY_DATA)), 'binary')
		unicode_data = "тест".encode("utf-8")
		self.assertEqual(Hex.bufferToAscii(unicode_data, 0, len(unicode_data)), '........')

	def test_dump(self):
		Hex.dump(_BINARY_DATA, size=len(_BINARY_DATA))
		with self.assertRaises(IndexError):
			Hex.dump(_BINARY_DATA)

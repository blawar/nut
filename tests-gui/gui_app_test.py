import sys

from PyQt5.QtWidgets import (QApplication)
from PyQt5.QtTest import QTest

import unittest

from gui.app import App

app = QApplication(sys.argv)

class GuiAppTest(unittest.TestCase):
	"""Tests for gui/app.py
	"""
	def setUp(self):
		self.form = App()

	def test_run(self):
		self.assertEqual(self.form.title, 'NUT 3.0')
		self.form.header.scan.click()

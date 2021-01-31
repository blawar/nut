# -*- coding: utf-8 -*-
import sys
import unittest

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPushButton, QLineEdit

from gui.app import App

class GuiAppTest(unittest.TestCase):
	"""Tests for gui/app.py
	"""
	def setUp(self):
		self.app = QApplication(sys.argv)
		self.form = App()

	def test_run(self):
		self.assertEqual(self.form.title, 'NUT 3.1')
		self.form.header.scan.click()
		self.form.tabs.tabs.setCurrentIndex(0) # files
		self.form.tabs.tabs.setCurrentIndex(1) # filters
		self.form.tabs.tabs.setCurrentIndex(2) # save paths
		self.form.tabs.tabs.setCurrentIndex(3) # local scan paths
		self.form.tabs.tabs.setCurrentIndex(4) # remote scan paths
		self.form.tabs.tabs.setCurrentIndex(5) # users
		self.form.tabs.tabs.setCurrentIndex(6) # options

		scan_path_widget = self.form.tabs.tabs.widget(3) # local scan paths
		print(scan_path_widget.metaObject().className())
		scan_edit = scan_path_widget.findChildren(QLineEdit)[0]
		add_button = scan_path_widget.findChildren(QPushButton)
		self.assertIsNotNone(add_button)

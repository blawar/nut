# -*- coding: utf-8 -*-
import sys
import unittest
import logging

from PyQt5.QtWidgets import (QApplication, QPushButton, QLineEdit, QSlider)

from gui.app import App

OPTIONS_TAB_INDEX = 6

class GuiAppTest(unittest.TestCase):
	"""Tests for gui/app.py
	"""
	def setUp(self):
		self.app = QApplication(sys.argv)
		self.form = App()
		logger = logging.getLogger()
		logger.level = logging.DEBUG

	def test_run(self):
		self.assertEqual(self.form.title, 'NUT 3.3')
		self.form.header.scan.click()
		self.form.tabs.tabs.setCurrentIndex(0) # files
		self.form.tabs.tabs.setCurrentIndex(1) # filters
		self.form.tabs.tabs.setCurrentIndex(2) # save paths
		self.form.tabs.tabs.setCurrentIndex(3) # local scan paths
		self.form.tabs.tabs.setCurrentIndex(4) # remote scan paths
		self.form.tabs.tabs.setCurrentIndex(5) # users
		self.form.tabs.tabs.setCurrentIndex(OPTIONS_TAB_INDEX)

		scan_path_widget = self.form.tabs.tabs.widget(3) # local scan paths
		logging.debug(scan_path_widget.metaObject().className())
		scan_edit = scan_path_widget.findChildren(QLineEdit)[0]
		add_button = scan_path_widget.findChildren(QPushButton)
		self.assertIsNotNone(scan_edit)
		self.assertIsNotNone(add_button)

	def test_options(self):
		tabs = self.form.tabs.tabs
		tabs.setCurrentIndex(OPTIONS_TAB_INDEX)
		sliders = tabs.findChildren(QSlider)
		threads_slider: QSlider = sliders[0]
		compression_slider: QSlider = sliders[1]
		self.assertEqual(threads_slider.minimum(), 1)
		self.assertEqual(threads_slider.maximum(), 8)
		self.assertEqual(compression_slider.minimum(), 0)
		self.assertEqual(compression_slider.maximum(), 22)

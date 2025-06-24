# -*- coding: utf-8 -*-
import sys
import unittest
import logging

from PyQt5.QtWidgets import (QApplication, QPushButton, QLineEdit, QSlider)
from PyQt5.QtTest import QTest
from PyQt5.QtCore import QEvent

from gui.app import App
from gui.panes.options import Threads, Compress
from gui.panes.dirlist import DirectoryLocal

from nut import Config

LOCAL_SCAN_PATHS_TAB_INDEX = 3
OPTIONS_TAB_INDEX = 5

def _find_button_by_text(widget, text):
	for button in widget.findChildren(QPushButton):
		if button.text() == text:
			return button
	return None

class GuiAppTest(unittest.TestCase):
	"""Tests for gui/app.py
	"""
	def setUp(self):
		self.app = QApplication(sys.argv)
		self.form = App()
		logger = logging.getLogger()
		logger.level = logging.DEBUG

		self.paths_before_test = Config.paths.scan
		self.threads_before_test = Config.threads
		self.compression_level_before_test = Config.compression.level

	def tearDown(self):
		Config.paths.scan = self.paths_before_test
		Config.threads = self.threads_before_test
		Config.compression.level = self.compression_level_before_test
		Config.save()

	def test_run(self):
		self.assertEqual(self.form.title, 'NUT 3.3')
		self.form.header.scan.click()
		self.form.tabs.tabs.setCurrentIndex(0) # files
		self.form.tabs.tabs.setCurrentIndex(1) # filters
		self.form.tabs.tabs.setCurrentIndex(2) # save paths
		self.form.tabs.tabs.setCurrentIndex(LOCAL_SCAN_PATHS_TAB_INDEX)
		self.form.tabs.tabs.setCurrentIndex(4) # remote scan paths
		self.form.tabs.tabs.setCurrentIndex(OPTIONS_TAB_INDEX)

	def test_options(self):
		tabs = self.form.tabs.tabs
		tabs.setCurrentIndex(OPTIONS_TAB_INDEX)
		current_tab = tabs.widget(OPTIONS_TAB_INDEX)
		sliders = current_tab.findChildren(QSlider)
		threads_slider: Threads = sliders[0]
		compression_slider: Compress = sliders[1]
		self.assertEqual(threads_slider.minimum(), 1)
		self.assertEqual(threads_slider.maximum(), 8)
		self.assertEqual(compression_slider.minimum(), 0)
		self.assertEqual(compression_slider.maximum(), 22)

		threads_slider.setValue(3)
		threads_slider.save()
		self.assertEqual(Config.threads, threads_slider.value())

		compression_slider.setValue(10)
		compression_slider.save()
		self.assertEqual(Config.compression.level, compression_slider.value())

	def test_dirlist_scan_paths(self):
		tabs = self.form.tabs.tabs
		tabs.setCurrentIndex(LOCAL_SCAN_PATHS_TAB_INDEX)
		current_tab = tabs.widget(LOCAL_SCAN_PATHS_TAB_INDEX)

		edits = current_tab.findChildren(QLineEdit)
		self.assertEqual(len(edits), 1)
		scan_edit = edits[0]
		self.assertIsNotNone(scan_edit)
		logging.debug(scan_edit.text())

		add_button = _find_button_by_text(current_tab, "Add")
		self.assertIsNotNone(add_button)

		edits = current_tab.findChildren(DirectoryLocal)
		self.assertEqual(len(edits), 1)

		add_button.click()

		edits = current_tab.findChildren(DirectoryLocal)
		self.assertEqual(len(edits), 2)

		dir_local: DirectoryLocal = edits[1]
		temp_path = "/tmp"
		dir_local.setValue(temp_path)
		self.assertEqual(dir_local.getValue(), temp_path)
		QApplication.sendEvent(dir_local, QEvent(QEvent.FocusOut))

# -*- coding: utf-8 -*-
import sys
import unittest
import logging

from PyQt5.QtWidgets import (QApplication, QPushButton, QLineEdit, QSlider)
from PyQt5.QtTest import QTest
from PyQt5.QtCore import QEvent

from gui.app import App
from gui.panes.options import Threads, Compress

from nut import Config, Users

USERS_TAB_INDEX = 5
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

	def test_dirlist(self):
		tabs = self.form.tabs.tabs
		tabs.setCurrentIndex(USERS_TAB_INDEX)
		current_tab = tabs.widget(USERS_TAB_INDEX)

		users_before_test = Users.users

		self.assertEqual(len(Users.users), 1)

		edits = current_tab.findChildren(QLineEdit)
		self.assertEqual(len(edits), 2)

		add_button = current_tab.findChild(QPushButton)
		self.assertIsNotNone(add_button)
		self.assertEqual(add_button.text(), "Add")
		add_button.click()

		edits = current_tab.findChildren(QLineEdit)
		self.assertEqual(len(edits), 4)

		self.assertEqual(edits[0].getValue(), "guest")
		self.assertEqual(edits[1].getValue(), "guest")

		QTest.keyClicks(edits[2], "test_user")
		self.assertEqual(edits[2].getValue(), "test_user")
		QApplication.sendEvent(edits[2], QEvent(QEvent.FocusOut))

		QTest.keyClicks(edits[3], "test_password")
		self.assertEqual(edits[3].getValue(), "test_password")
		QApplication.sendEvent(edits[2], QEvent(QEvent.FocusOut))

		edits[2].setValue("test_user1")
		self.assertEqual(edits[2].getValue(), "test_user1")

		self.assertEqual(len(Users.users), 2)

		Users.users = users_before_test
		Users.export()

# -*- coding: utf-8 -*-
import os
import webbrowser

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QWidget, QDesktopWidget, QVBoxLayout, QMessageBox)

import gui.tabs
import gui.panes.files
import gui.panes.options
import gui.panes.format
import gui.panes.filters
import gui.panes.dirlist

from gui.header import Header
from gui.progress import Progress

import nut
from nut import Config, Nsps
import Fs.driver.init
from translator import tr

class App(QWidget):
	def __init__(self):
		super().__init__()
		self.title = 'NUT 3.3'
		self.needsRefresh = False
		self.isInitialized = False
		self.initUI()

	def refresh(self):
		self.needsRefresh = True

	def initUI(self):
		self.isInitialized = False
		self.setWindowTitle(self.title)
		screen = QDesktopWidget().screenGeometry()
		left = int(screen.width() / 4)
		top = int(screen.height() / 4)
		width = int(screen.width() / 2)
		height = int(screen.height() / 2)
		self.setGeometry(left, top, width, height)

		layout = QVBoxLayout()

		self.header = Header(self)
		layout.addLayout(self.header.layout)
		self.files = gui.panes.files.Files()

		self.tabs = gui.tabs.Tabs({
			tr('main.grid.files'): self.files,
			tr('main.grid.filters'): gui.panes.filters.Filters(),
			tr('main.grid.save_paths'): gui.panes.format.Format(),
			tr('main.grid.local_scan_paths'): gui.panes.dirlist.DirList(Config.paths.scan, self.saveScanPaths, rowType=gui.panes.dirlist.DirectoryLocal),
			tr('main.grid.remote_pull_paths'): gui.panes.dirlist.DirList(Config.pullUrls, self.savePullUrls, rowType=gui.panes.dirlist.DirectoryNetwork),
			tr('main.grid.options'): gui.panes.options.Options()
		})
		layout.addWidget(self.tabs)

		self.progress = Progress(self)
		layout.addLayout(self.progress.layout)

		self.setLayout(layout)

		self.isInitialized = True
		self.show()

	def saveScanPaths(self, control):
		if not self.isInitialized:
			return

		result = []
		i = 0
		while i < control.count():
			value = control.getValue(i)

			if value:
				result.append(value)
			i += 1

		Config.update_scan_paths(result, Nsps.files)

	def savePullUrls(self, control):
		if not self.isInitialized:
			return

		result = []
		i = 0
		while i < control.count():
			value = control.getValue(i)

			if value:
				result.append(value)
			i += 1

		Config.pullUrls = result
		Config.save()

	@staticmethod
	def on_decompress():
		nut.decompressAll()

	@staticmethod
	def on_compress():
		nut.compressAll(Config.compression.level)

	def on_organize(self):
		answer = QMessageBox.question(self, tr('main.top_menu.organize'),
			tr('main.dialog.organize_confirmation'),
			QMessageBox.Yes | QMessageBox.No)
		if answer == QMessageBox.Yes:
			nut.organize()

	@pyqtSlot()
	def on_scan(self):
		nut.scan()
		self.files.refresh()

	@staticmethod
	@pyqtSlot()
	def on_pull():
		nut.pull()

	@staticmethod
	@pyqtSlot()
	def on_titledb():
		nut.updateTitleDb(force=True)

	@pyqtSlot()
	def on_gdrive(self):
		if Config.getGdriveCredentialsFile() is None:
			webbrowser.open_new_tab(
				'https://developers.google.com/drive/api/v3/quickstart/go',
			)
			QMessageBox.information(
				self,
				'Google Drive OAuth Setup',
				"You require a credentials.json file to set up Google Drive " +
				"OAuth.  This file can be obtained from " +
				"https://developers.google.com/drive/api/v3/quickstart/go , " +
				"click on the blue button that says 'Enable the Drive API' " +
				"and save the credentials.json to this application's " +
				"directory.",
			)
		else:
			buttonReply = QMessageBox.question(
				self,
				'Google Drive OAuth Setup',
				"Do you you want to setup GDrive OAuth?",
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
			)

			if buttonReply == QMessageBox.Yes:
				try:
					os.unlink('gdrive.token')
				except OSError:
					pass

				try:
					os.unlink('token.pickle')
				except OSError:
					pass

				Fs.driver.gdrive.getGdriveToken(None, None)
				QMessageBox.information(
					self,
					'Google Drive OAuth Setup',
					"OAuth has completed.  Please copy gdrive.token and " +
					"credentials.json to your Nintendo Switch's " +
					"sdmc:/switch/tinfoil/ and/or sdmc:/switch/sx/ " +
					"directories."
				)

	@staticmethod
	def closeEvent(event):
		del event
		# TODO: implement a graceful shutdown of other threads
		os._exit(0) # pylint: disable=protected-access

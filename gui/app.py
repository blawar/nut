# -*- coding: utf-8 -*-
import os
import webbrowser

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QDesktopWidget, QVBoxLayout, QMessageBox, QSizePolicy)

import gui.tabs
import gui.panes.files
import gui.panes.options
import gui.panes.format
import gui.panes.filters
import gui.panes.dirlist

from gui.header import Header
from gui.progress import Progress

import nut
from nut import Config, Users, Nsps
import Fs.driver.init
from translator import tr

class App(QWidget):
	def __init__(self):
		super().__init__()
		screen = QDesktopWidget().screenGeometry()
		self.title = 'NUT 3.1'
		self.left = int(screen.width() / 4)
		self.top = int(screen.height() / 4)
		self.width = int(screen.width() / 2)
		self.height = int(screen.height() / 2)
		self.needsRefresh = False
		self.isInitialized = False
		self.initUI()

	def refresh(self):
		self.needsRefresh = True

	def initUI(self):
		self.isInitialized = False
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.layout = QVBoxLayout()

		self.header = Header(self)
		self.layout.addLayout(self.header.layout)
		self.files = gui.panes.files.Files()

		self.tabs = gui.tabs.Tabs({
			tr('main.grid.files'): self.files,
			tr('main.grid.filters'): gui.panes.filters.Filters(),
			tr('main.grid.save_paths'): gui.panes.format.Format(),
			tr('main.grid.local_scan_paths'): gui.panes.dirlist.DirList(Config.paths.scan, self.saveScanPaths, rowType=gui.panes.dirlist.DirectoryLocal),
			tr('main.grid.remote_pull_paths'): gui.panes.dirlist.DirList(Config.pullUrls, self.savePullUrls, rowType=gui.panes.dirlist.DirectoryNetwork),
			tr('main.grid.users'): gui.panes.dirlist.DirList(list(Users.users.values()), self.saveUsers, rowType=gui.panes.dirlist.User),  # rowType
			tr('main.grid.options'): gui.panes.options.Options()
		})
		self.layout.addWidget(self.tabs)

		self.progress = Progress(self)
		self.layout.addLayout(self.progress.layout)

		self.setLayout(self.layout)

		self.isInitialized = True
		self.show()

	def saveUsers(self, control):
		result = {}
		i = 0
		while i < control.count():
			value = control.getValue(i)

			if value:
				result[value.id] = value
			i += 1

		Users.users = result
		Users.export()

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

	def on_decompress(self):
		nut.decompressAll()

	def on_compress(self):
		nut.compressAll(Config.compression.level)

	def on_organize(self):
		nut.organize()

	@pyqtSlot()
	def on_scan(self):
		nut.scan()
		self.files.refresh()

	@pyqtSlot()
	def on_pull(self):
		nut.pull()

	@pyqtSlot()
	def on_titledb(self):
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
				"and save the credentials.json to t his application's " +
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
				# TODO: Remove bare except
				except BaseException:
					pass

				try:
					os.unlink('token.pickle')
				# TODO: Remove bare except
				except BaseException:
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

	def closeEvent(self, event):
		# TODO: implement a graceful shutdown of other threads
		os._exit(0)

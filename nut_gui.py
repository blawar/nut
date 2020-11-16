#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import socket
import sys
import threading
import time
import webbrowser

import urllib3
import gui
import gui.tabs
import gui.panes.files
import gui.panes.options
import gui.panes.format
import gui.panes.filters
import gui.panes.dirlist
from PyQt5.QtCore import QSortFilterProxyModel, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QHBoxLayout,
							 QHeaderView, QLabel, QLineEdit, QMessageBox,
							 QProgressBar, QPushButton, QTableView,
							 QVBoxLayout, QWidget)

import nut
import Server
from nut import Config, Nsps, Status, Usb, Users
import Fs.driver.init

SIZE_COLUMN_INDEX = 3


def getIpAddress():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
		s.close()
		return ip
	except OSError:
		return None


def formatSpeed(n):
	return str(round(n / 1000 / 1000, 1)) + 'MB/s'


def _format_size(num, suffix='B'):
	if num is None:
		return ''
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)


class Header:
	def __init__(self, app):
		self.layout = QVBoxLayout()

		top = QHBoxLayout()
		bottom = QHBoxLayout()

		self.scan = QPushButton('Scan', app)
		self.scan.setMaximumWidth(100)
		self.scan.clicked.connect(app.on_scan)
		top.addWidget(self.scan)

		btn = QPushButton('Organize Files', app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_organize)
		top.addWidget(btn)

		self.pull = QPushButton('Pull', app)
		self.pull.setMaximumWidth(100)
		self.pull.clicked.connect(app.on_pull)
		top.addWidget(self.pull)

		self.titledb = QPushButton('Update TitleDB', app)
		self.titledb.setMaximumWidth(200)
		self.titledb.clicked.connect(app.on_titledb)
		top.addWidget(self.titledb)

		btn = QPushButton('Decompress NSZ', app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_decompress)
		top.addWidget(btn)

		btn = QPushButton('Compress NSP', app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_compress)
		top.addWidget(btn)

		self.gdrive = QPushButton('Setup GDrive OAuth', app)
		self.gdrive.setMaximumWidth(200)
		self.gdrive.clicked.connect(app.on_gdrive)
		top.addWidget(self.gdrive)

		top.addStretch()

		ipAddr = getIpAddress()

		if ipAddr:
			self.serverInfo = QLabel(
				f"<b>IP:</b>  {ipAddr}  <b>Port:</b>  {Config.server.port}  " +
				f"<b>User:</b>  {Users.first().id}  <b>Password:</b>  " +
				f"{Users.first().password}"
			)
		else:
			self.serverInfo = QLabel("<b>Offline</b>")

		self.serverInfo.setMinimumWidth(200)
		self.serverInfo.setAlignment(Qt.AlignCenter)
		bottom.addWidget(self.serverInfo)
		bottom.addStretch()

		self.usbStatus = QLabel("<b>USB:</b>  " + str(Usb.status))
		self.usbStatus.setMinimumWidth(50)
		self.usbStatus.setAlignment(Qt.AlignCenter)
		bottom.addWidget(self.usbStatus)

		self.timer = QTimer()
		self.timer.setInterval(1000)
		self.timer.timeout.connect(self.tick)
		self.timer.start()

		self.layout.addLayout(top)
		self.layout.addLayout(bottom)

	def tick(self):
		self.usbStatus.setText("<b>USB:</b> " + str(Usb.status))


class Progress:
	def __init__(self, app):
		self.app = app
		self.progress = QProgressBar(app)
		self.text = QLabel()
		self.speed = QLabel()
		self.text.resize(100, 40)
		self.speed.resize(100, 40)

		self.layout = QHBoxLayout()
		self.layout.addWidget(self.text)
		self.layout.addWidget(self.progress)
		self.layout.addWidget(self.speed)

		self.timer = QTimer()
		self.timer.setInterval(250)
		self.timer.timeout.connect(self.tick)
		self.timer.start()

	def resetStatus(self):
		self.progress.setValue(0)
		self.text.setText('')
		self.speed.setText('')

	def tick(self):
		for i in Status.lst:
			if i.isOpen():
				try:
					self.progress.setValue(i.i / i.size * 100)
					self.text.setText(i.desc)
					self.speed.setText(
						formatSpeed(i.a / (time.process_time() - i.ats))
					)
				# TODO: Remove bare except
				except BaseException:
					self.resetStatus()
				break
			else:
				self.resetStatus()
		if len(Status.lst) == 0:
			self.resetStatus()

		if self.app.needsRefresh:
			self.app.needsRefresh = False
			# self.app.refreshTable()


class App(QWidget):
	def __init__(self):
		super().__init__()
		screen = QDesktopWidget().screenGeometry()
		self.title = 'NUT 3.0'
		self.left = int(screen.width() / 4)
		self.top = int(screen.height() / 4)
		self.width = int(screen.width() / 2)
		self.height = int(screen.height() / 2)
		self.needsRefresh = False
		self.initUI()

	def refresh(self):
		self.needsRefresh = True

	def initUI(self):
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.layout = QVBoxLayout()

		self.header = Header(self)
		self.layout.addLayout(self.header.layout)
		self.files = gui.panes.files.Files()

		self.tabs = gui.tabs.Tabs({
			'Home': QWidget(),
			'Files': self.files,
			'Filters': gui.panes.filters.Filters(),
			'Save Paths': gui.panes.format.Format(),
			'Local Scan Paths': gui.panes.dirlist.DirList(Config.paths.scan, self.saveScanPaths, rowType=gui.panes.dirlist.DirectoryLocal),
			'Remote Pull Paths': gui.panes.dirlist.DirList(Config.pullUrls, self.savePullUrls, rowType=gui.panes.dirlist.DirectoryNetwork),
			'Users': gui.panes.dirlist.DirList(list(Users.users.values()), self.saveUsers, rowType=gui.panes.dirlist.User),  # rowType
			'Options': gui.panes.options.Options()
		})
		self.layout.addWidget(self.tabs)

		self.progress = Progress(self)
		self.layout.addLayout(self.progress.layout)

		self.setLayout(self.layout)

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
		result = []
		i = 0
		while i < control.count():
			value = control.getValue(i)

			if value:
				result.append(value)
			i += 1

		Config.update_scan_paths(result, Nsps.files)

	def savePullUrls(self, control):
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
		# self.model.setRowCount(0)
		nut.scan()
		self.files.refresh()
		# self.refreshTable()

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

				server.controller.api.getGdriveToken(None, None)
				QMessageBox.information(
					self,
					'Google Drive OAuth Setup',
					"OAuth has completed.  Please copy gdrive.token and " +
					"credentials.json to your Nintendo Switch's " +
					"sdmc:/switch/tinfoil/ and/or sdmc:/switch/sx/ " +
					"directories."
				)


threadRun = True


def usbThread():
	Usb.daemon()


def nutThread():
	Server.run()
	pass


def initThread(app):
	nut.scan()
	app.refresh()


def run():
	urllib3.disable_warnings()

	print('						,;:;;,')
	print('					   ;;;;;')
	print('			   .=\',	;:;;:,')
	print('			  /_\', "=. \';:;:;')
	print('			  @=:__,  \\,;:;:\'')
	print('				_(\\.=  ;:;;\'')
	print('			   `"_(  _/="`')
	print('				`"\'')

	nut.initTitles()
	nut.initFiles()

	app = QApplication(sys.argv)
	app.setWindowIcon(QIcon('images/logo.jpg'))
	ex = App()

	threads = []
	threads.append(threading.Thread(target=initThread, args=[ex]))
	threads.append(threading.Thread(target=usbThread, args=[]))
	threads.append(threading.Thread(target=nutThread, args=[]))

	for t in threads:
		t.start()

	sys.exit(app.exec_())

	print('fin')


if __name__ == '__main__':
	run()

#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import pathlib
import urllib3
import urllib
import json
# import webbrowser
import Server

import nut
from nut import Nsps

from nut import Config
import time

import Server
import pprint
import random
from nut import Usb
from nut import Users
import threading
from nut import Status
import time
import socket

import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout,QDesktopWidget, QTabWidget, QProgressBar, QLabel,QHBoxLayout, QLineEdit, QPushButton, QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot,Qt,QTimer
from PyQt5 import QtWidgets

def getIpAddress():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ip = s.getsockname()[0]
	s.close()
	return ip

def formatSpeed(n):
	return str(round(n / 1000 / 1000, 1)) + 'MB/s'

class Header:
	def __init__(self, app):
		self.app = app
		self.layout = QHBoxLayout()

		self.textbox = QLineEdit(app)
		self.textbox.setMinimumWidth(25)
		self.textbox.setAlignment(Qt.AlignLeft)
		self.textbox.setText(os.path.abspath(Config.paths.scan[0]))
		self.textbox.textChanged.connect(self.updatePath)
		self.layout.addWidget(self.textbox)

		self.scan = QPushButton('Scan', app)
		self.scan.clicked.connect(app.on_scan)
		self.layout.addWidget(self.scan)

		# self.autolaunchBrowser = QCheckBox("Launch Web Browser?", app)
		# self.autolaunchBrowser.setChecked(Config.autolaunchBrowser)
		# self.autolaunchBrowser.stateChanged.connect(self.onCheck)
		# self.layout.addWidget(self.autolaunchBrowser)

		self.serverInfo = QLabel("<b>IP:</b>  %s  <b>Port:</b>  %s  <b>User:</b>  %s  <b>Password:</b>  %s" % (getIpAddress(), str(Config.server.port), Users.first().id, Users.first().password))
		self.serverInfo.setMinimumWidth(200)
		self.serverInfo.setAlignment(Qt.AlignCenter)
		self.layout.addWidget(self.serverInfo)

		self.usbStatus = QLabel("<b>USB:</b>  " + str(Usb.status))
		self.usbStatus.setMinimumWidth(50)
		self.usbStatus.setAlignment(Qt.AlignCenter)
		self.layout.addWidget(self.usbStatus)

		self.timer = QTimer()
		self.timer.setInterval(1000)
		self.timer.timeout.connect(self.tick)
		self.timer.start()

		Users.export()

	# def onCheck(self, state):
	# 	if state == Qt.Checked:
	# 		Config.autolaunchBrowser = True
	# 	else:
	# 		Config.autolaunchBrowser = False
	# 	Config.save()

	def updatePath(self):
		Config.paths.scan[0] = self.textbox.text()
		Config.save()

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
					self.speed.setText(formatSpeed(i.a / (time.process_time() - i.ats)))
				except:
					self.resetStatus()
				break
			else:
				self.resetStatus()
		if len(Status.lst) == 0:
			self.resetStatus()

		if self.app.needsRefresh:
			self.app.needsRefresh = False
			self.app.refreshTable()

class App(QWidget):
 
	def __init__(self):
		super().__init__()
		self.setWindowIcon(QIcon('public_html/images/logo.jpg'))
		screen = QDesktopWidget().screenGeometry()
		self.title = 'NUT USB / Web Server v2.2'
		self.left = screen.width() / 4
		self.top = screen.height() / 4
		self.width = screen.width() / 2
		self.height = screen.height() / 2
		#self.setWindowState(Qt.WindowMaximized)
		self.needsRefresh = False
		self.initUI()

	def refresh(self):
		self.needsRefresh = True
 
	def initUI(self):
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)
 
		self.createTable()

		self.layout = QVBoxLayout()

		self.header = Header(self)
		self.layout.addLayout(self.header.layout)

		self.layout.addWidget(self.tableWidget)

		self.progress = Progress(self)
		self.layout.addLayout(self.progress.layout)

		self.setLayout(self.layout)
 
		self.show()
 
	def createTable(self):
		self.tableWidget = QTableWidget()
		self.tableWidget.setColumnCount(4)

		headers = [QTableWidgetItem("File"), QTableWidgetItem("Title ID"), QTableWidgetItem("Type"), QTableWidgetItem("Size")]

		i = 0
		for h in headers:
			self.tableWidget.setHorizontalHeaderItem(i, h)
			i = i + 1

		header = self.tableWidget.horizontalHeader()
		i = 0
		for h in headers:
			header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch if i == 0 else QtWidgets.QHeaderView.ResizeToContents)
			i = i + 1

		self.tableWidget.setSortingEnabled(True)

		self.refreshTable()

	@pyqtSlot()
	def on_scan(self):
		self.tableWidget.setRowCount(0)
		nut.scan()
		self.refreshTable()

	@pyqtSlot()
	def refreshTable(self):
		try:
			self.tableWidget.setRowCount(0)
			self.tableWidget.setRowCount(len(Nsps.files))
			i = 0
			for k, f in Nsps.files.items():
				if f.path.endswith('.nsx'):
					continue

				self.tableWidget.setItem(i,0, QTableWidgetItem(f.fileName()))
				self.tableWidget.setItem(i,1, QTableWidgetItem(str(f.titleId)))
				self.tableWidget.setItem(i,2, QTableWidgetItem("UPD" if f.isUpdate() else ("DLC" if f.isDLC() else "BASE")))
				self.tableWidget.setItem(i,3, QTableWidgetItem(str(f.fileSize)))

				i = i + 1

			self.tableWidget.setRowCount(i)
		except BaseException as e:
			print('exception: ' + str(e))
			pass
 
threadRun = True

def usbThread():
	Usb.daemon()

def nutThread():
	Server.run()

def initThread(app):
	nut.scan()
	app.refresh()
	# if Config.autolaunchBrowser:
	# 	webbrowser.open_new_tab('http://' + urllib.parse.quote_plus(Users.first().id) + ':' + urllib.parse.quote_plus(Users.first().password) + '@' + getIpAddress() + ':' + str(Config.server.port))
			
def run():
	urllib3.disable_warnings()


	print('                        ,;:;;,')
	print('                       ;;;;;')
	print('               .=\',    ;:;;:,')
	print('              /_\', "=. \';:;:;')
	print('              @=:__,  \,;:;:\'')
	print('                _(\.=  ;:;;\'')
	print('               `"_(  _/="`')
	print('                `"\'')

	nut.initFiles()

	app = QApplication(sys.argv)
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

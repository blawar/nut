#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import threading

import urllib3

from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QApplication)

import nut
import Server
from gui.app import App
from nut import Usb
from nut import Hook

threadRun = True


def usbThread():
	Usb.daemon()

def nutThread():
	Server.run()

def initThread(app):
	print('initThread start')
	nut.scan()
	app.refresh()
	print('initThread finish')

def run():
	urllib3.disable_warnings()

	print(r'                        ,;:;;,')
	print(r'                       ;;;;;')
	print(r'               .=\',    ;:;;:,')
	print(r'              /_\', "=. \';:;:;')
	print(r'              @=:__,  \,;:;:\'')
	print(r'                _(\.=  ;:;;\'')
	print(r'               `"_(  _/="`')
	print(r'                `"\'')

	nut.initTitles()
	nut.initFiles()

	Hook.init()

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

Hook.call("exit")

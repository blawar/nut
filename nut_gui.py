#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import server
import socket
import urllib3
import threading
import webbrowser

import nut_impl
from nut_impl import usb
from nut_impl import nsps
from nut_impl import users
from nut_impl import config
from nut_impl import status

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSlot


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


class Header:
    def __init__(self, app):
        self.layout = QHBoxLayout()

        self.textbox = QLineEdit(app)
        self.textbox.setMinimumWidth(25)
        self.textbox.setAlignment(Qt.AlignLeft)
        self.textbox.setText(os.path.abspath(config.paths.scan[0]))
        self.layout.addWidget(self.textbox)

        self.savePath = QPushButton('Save path', app)
        self.savePath.clicked.connect(self.updatePath)
        self.layout.addWidget(self.savePath)

        self.scan = QPushButton('Scan', app)
        self.scan.clicked.connect(app.on_scan)
        self.layout.addWidget(self.scan)

        self.gdrive = QPushButton('Setup GDrive OAuth', app)
        self.gdrive.clicked.connect(app.on_gdrive)
        self.layout.addWidget(self.gdrive)

        ipAddr = getIpAddress()

        if ipAddr:
            self.serverInfo = QLabel(
                f"<b>IP:</b>  {ipAddr}  <b>Port:</b>  {config.server.port}  " +
                f"<b>User:</b>  {users.first().id}  <b>Password:</b>  " +
                f"{users.first().password}"
            )
        else:
            self.serverInfo = QLabel("<b>Offline</b>")

        self.serverInfo.setMinimumWidth(200)
        self.serverInfo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.serverInfo)

        self.usbStatus = QLabel("<b>USB:</b>  " + str(usb.status))
        self.usbStatus.setMinimumWidth(50)
        self.usbStatus.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.usbStatus)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def updatePath(self):
        config.update_main_path(self.textbox.text())


    def tick(self):
        self.usbStatus.setText("<b>USB:</b> " + str(usb.status))


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
        for i in status.lst:
            if i.isOpen():
                try:
                    self.progress.setValue(i.i / i.size * 100)
                    self.text.setText(i.desc)
                    self.speed.setText(
                        formatSpeed(i.a / (time.process_time() - i.ats))
                    )
                # TODO: Remove bare except
                except:
                    self.resetStatus()
                break
            else:
                self.resetStatus()
        if len(status.lst) == 0:
            self.resetStatus()

        if self.app.needsRefresh:
            self.app.needsRefresh = False
            self.app.refreshTable()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('images/logo.jpg'))
        screen = QDesktopWidget().screenGeometry()
        self.title = 'NUT USB / Web Server v2.7'
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

        headers = [
            QTableWidgetItem("File"),
            QTableWidgetItem("Title ID"),
            QTableWidgetItem("Type"),
            QTableWidgetItem("Size")
        ]

        i = 0
        for h in headers:
            self.tableWidget.setHorizontalHeaderItem(i, h)
            i = i + 1

        header = self.tableWidget.horizontalHeader()
        i = 0
        for h in headers:
            mode = QHeaderView.Stretch if i == 0 else \
                QHeaderView.ResizeToContents
            header.setSectionResizeMode(i, mode)
            i = i + 1

        self.tableWidget.setSortingEnabled(True)

        self.refreshTable()

    @pyqtSlot()
    def on_scan(self):
        self.tableWidget.setRowCount(0)
        nut_impl.scan()
        self.refreshTable()

    @pyqtSlot()
    def on_gdrive(self):
        if config.getGdriveCredentialsFile() is None:
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
                except:
                    pass

                try:
                    os.unlink('token.pickle')
                # TODO: Remove bare except
                except:
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

    @pyqtSlot()
    def refreshTable(self):
        try:
            self.tableWidget.setRowCount(0)
            self.tableWidget.setRowCount(len(nsps.files))
            i = 0
            for _, f in nsps.files.items():
                if f.path.endswith('.nsx'):
                    continue

                titleType = "UPD" if f.isUpdate() else "DLC" if f.isDLC() \
                    else "BASE"

                self.tableWidget.setItem(
                    i,
                    0,
                    QTableWidgetItem(f.fileName()),
                )
                self.tableWidget.setItem(
                    i,
                    1,
                    QTableWidgetItem(str(f.titleId)),
                )
                self.tableWidget.setItem(
                    i,
                    2,
                    QTableWidgetItem(titleType),
                )
                self.tableWidget.setItem(
                    i,
                    3,
                    QTableWidgetItem(str(f.fileSize)),
                )

                i = i + 1

            self.tableWidget.setRowCount(i)
        except BaseException as e:
            print('exception: ' + str(e))
            pass


threadRun = True


def usbThread():
    usb.daemon()


def nutThread():
    server.run()


def initThread(app):
    nut_impl.scan()
    app.refresh()


def run():
    urllib3.disable_warnings()

    print('                        ,;:;;,')
    print('                       ;;;;;')
    print('               .=\',    ;:;;:,')
    print('              /_\', "=. \';:;:;')
    print('              @=:__,  \\,;:;:\'')
    print('                _(\\.=  ;:;;\'')
    print('               `"_(  _/="`')
    print('                `"\'')

    nut_impl.initFiles()

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

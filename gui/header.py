import socket

from PyQt5.QtCore import (Qt, pyqtSlot, QTimer)
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel)

from nut import Config, Users, Usb
from translator import tr

def _get_ip_address():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
		s.close()
		return ip
	except OSError:
		return None

class Header:
	def __init__(self, app):
		self.layout = QVBoxLayout()

		top = QHBoxLayout()
		bottom = QHBoxLayout()

		self.scan = QPushButton(tr('main.top_menu.scan'), app)
		self.scan.setMaximumWidth(100)
		self.scan.clicked.connect(app.on_scan)
		self.scan.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(self.scan)

		btn = QPushButton(tr('main.top_menu.organize'), app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_organize)
		btn.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(btn)

		self.pull = QPushButton(tr('main.top_menu.pull'), app)
		self.pull.setMaximumWidth(100)
		self.pull.clicked.connect(app.on_pull)
		self.pull.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(self.pull)

		self.titledb = QPushButton(tr('main.top_menu.update_titledb'), app)
		self.titledb.setMaximumWidth(200)
		self.titledb.clicked.connect(app.on_titledb)
		self.titledb.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(self.titledb)

		btn = QPushButton(tr('main.top_menu.decompress_nsz'), app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_decompress)
		btn.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(btn)

		btn = QPushButton(tr("main.top_menu.compress_nsp"), app)
		btn.setMaximumWidth(200)
		btn.clicked.connect(app.on_compress)
		btn.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(btn)

		self.gdrive = QPushButton(tr("main.top_menu.setup_gdrive"), app)
		self.gdrive.setMaximumWidth(200)
		self.gdrive.clicked.connect(app.on_gdrive)
		self.gdrive.setFocusPolicy(Qt.StrongFocus)
		top.addWidget(self.gdrive)

		top.addStretch()

		ipAddr = _get_ip_address()

		if ipAddr:
			self.serverInfo = QLabel(
				f"<b>{tr('main.status.ip')}:</b>  {ipAddr}  <b>{tr('main.status.port')}:</b>  {Config.server.port}  " +
				f"<b>{tr('main.status.user')}:</b>  {Users.first().id}  <b>{tr('main.status.password')}:</b>  " +
				f"{Users.first().password}"
			)
		else:
			self.serverInfo = QLabel("<b>Offline</b>")

		self.serverInfo.setMinimumWidth(200)
		self.serverInfo.setAlignment(Qt.AlignCenter)
		bottom.addWidget(self.serverInfo)
		bottom.addStretch()

		self.usbStatus = QLabel("<b>USB:</b>  " + tr("usb.status." + Usb.status))
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
		self.usbStatus.setText("<b>USB:</b> " + tr("usb.status." + Usb.status))

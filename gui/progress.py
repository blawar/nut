# -*- coding: utf-8 -*-
import time

from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtWidgets import QProgressBar, QLabel, QHBoxLayout

from nut import Status


def _format_speed(n):
	return str(round(n / 1000 / 1000, 1)) + "MB/s"


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
		self.text.setText("")
		self.speed.setText("")

	def tick(self):
		for i in Status.lst:
			if i.isOpen():
				try:
					self.progress.setValue(i.i * 100 // i.size)
					self.text.setText(i.desc)
					self.speed.setText(
						_format_speed(i.a / (time.perf_counter() - i.ats))
					)
				# TODO: Remove bare except
				except BaseException:
					self.resetStatus()
				break
			self.resetStatus()
		if len(Status.lst) == 0:
			self.resetStatus()

		if self.app.needsRefresh:
			self.app.needsRefresh = False
			# self.app.refreshTable()

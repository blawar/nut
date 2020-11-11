import os
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,QFormLayout,QLabel,QLineEdit,QHBoxLayout,QSlider,QGroupBox
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, QRect, Qt
from nut import Nsps, Config

class Threads(QSlider):
	def __init__(self, parent):
		super(QSlider, self).__init__(Qt.Horizontal)
		self.parent = parent
		self.setMinimum(1)
		self.setMaximum(8)
		self.setValue(Config.threads)
		self.valueChanged.connect(self.save)

	def save(self):
		Config.threads = self.value()
		Config.save()

		if self.parent:
			self.parent.save()

class Compress(QSlider):
	def __init__(self, parent):
		super(QSlider, self).__init__(Qt.Horizontal)
		self.parent = parent
		self.setMinimum(0)
		self.setMaximum(22)
		self.setValue(Config.compression.level)
		self.valueChanged.connect(self.save)

	def save(self):
		Config.compression.level = self.value()
		Config.save()

		if self.parent:
			self.parent.save()

class SliderControl(QWidget):
	def __init__(self, type):
		super(QWidget, self).__init__()
		self.type = type
		layout = QHBoxLayout(self)
		self.slider = self.type(self)
		layout.addWidget(self.slider)
		self.label = QLabel(str(self.slider.value()))
		layout.addWidget(self.label)

	def save(self):
		self.label.setText(str(self.slider.value()))


class Options(QWidget):
	def __init__(self):
		super(QWidget, self).__init__()

		layout = QVBoxLayout(self)

		serverGroup = QFormLayout()

		layout.addLayout(serverGroup)

		group = QGroupBox('THREADS')
		groupLayout = QHBoxLayout(group)
		groupLayout.addWidget(SliderControl(type = Threads))
		layout.addWidget(group)

		group = QGroupBox('COMPRESSION LEVEL')
		groupLayout = QHBoxLayout(group)
		groupLayout.addWidget(SliderControl(type = Compress))
		layout.addWidget(group)

		layout.addStretch()


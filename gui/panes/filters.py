import os
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QFormLayout, QLabel, QLineEdit, QHBoxLayout, QCheckBox, QGroupBox, QGridLayout
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, QRect
from nut import Nsps, Config

class ConfCheckbox(QCheckBox):
	def __init__(self, conf):
		super(QCheckBox, self).__init__()
		self.conf = conf
		value = self.get()
		self.setChecked(value)
		self.stateChanged.connect(self.onStateChanged)

	def onStateChanged(self, state):
		self.set(self.isChecked())
		Config.save()

	def get(self):
		try:
			j = Config
			for path in self.conf.split('.'):
				j = getattr(j, path)
			return j
		except BaseException as e:
			return None

	def set(self, value):
		j = Config
		paths = self.conf.split('.')
		last = paths.pop()
		for path in paths:
			j = getattr(j, path)
		setattr(j, last, value)

class RegionEntry(QWidget):
	def __init__(self, region):
		super(QWidget, self).__init__()
		self.region = region.upper()
		layout = QHBoxLayout(self)
		layout.addWidget(QLabel(region))
		self.check = QCheckBox()

		self.check.setChecked(Config.download.hasRegion([region], False))
		self.check.stateChanged.connect(self.onStateChanged)
		layout.addWidget(self.check)
		layout.addStretch()

	def onStateChanged(self, state):
		if self.check.isChecked():
			Config.download.addRegion(self.region)
		else:
			Config.download.removeRegion(self.region)
		Config.save()


class Region(QWidget):
	def __init__(self):
		super(QWidget, self).__init__()

		layout = QGridLayout(self)

		regions = []
		for region, languages in Config.regionLanguages().items():
			regions.append(region)

		regions.sort()

		width = 4
		i = 0
		for region in regions:
			layout.addWidget(RegionEntry(region), i // width, i % width)
			i += 1

class Filters(QWidget):
	def __init__(self):
		super(QWidget, self).__init__()

		layout = QVBoxLayout(self)

		types = QGroupBox('TYPES')

		testGroup = QHBoxLayout(types)

		'''
		testGroup.addRow(QLabel("Base"), QCheckBox())
		testGroup.addRow(QLabel("DLC"), QCheckBox())
		testGroup.addRow(QLabel("Update"), QCheckBox())
		testGroup.addRow(QLabel("Demo"), QCheckBox())
		'''

		testGroup.addWidget(QLabel("Base"))
		testGroup.addWidget(ConfCheckbox('download.base'))
		testGroup.addStretch()

		testGroup.addWidget(QLabel("DLC"))
		testGroup.addWidget(ConfCheckbox('download.DLC'))
		testGroup.addStretch()

		testGroup.addWidget(QLabel("Update"))
		testGroup.addWidget(ConfCheckbox('download.update'))
		testGroup.addStretch()

		testGroup.addWidget(QLabel("Demo"))
		testGroup.addWidget(ConfCheckbox('download.demo'))

		layout.addWidget(types)

		region = QGroupBox('REGION')
		regionLayout = QHBoxLayout(region)
		regionLayout.addWidget(Region())
		layout.addWidget(region)

		layout.addStretch()

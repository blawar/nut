# -*- coding: utf-8 -*-
import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QRect, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QScrollArea, QTableWidget,
                             QTableWidgetItem, QTabWidget, QVBoxLayout,
                             QWidget, QFrame, QScrollArea)

from nut import Config, Nsps


class Edit(QLineEdit):
	def __init__(self, id, type):
		super().__init__()
		self.id = id
		self.type = type

		if type:
			self.key = type.lower() + 'Title' + id
		else:
			self.key = 'title' + id

		self.setText(getattr(Config.paths, self.key))
		# self.textChanged.connect(self.onChange)

	def focusOutEvent(self, event):
		print(f"Edit focusOutEvent: {event}")
		current = getattr(Config.paths, self.key) or ''
		new = self.text()

		if current != new:
			setattr(Config.paths, self.key, new)
			Config.save()

		super(Edit, self).focusOutEvent(event)

	def onChange(self):
		print('changed: ' + self.id)

class Row(QGroupBox):
	def __init__(self, type=''):
		super().__init__((type or 'nsp').upper())
		layout = QFormLayout(self)

		layout.addRow(QLabel('Base'), Edit('Base', type))
		layout.addRow(QLabel('DLC'), Edit('DLC', type))
		layout.addRow(QLabel('Update'), Edit('Update', type))
		layout.addRow(QLabel('Demo'), Edit('Demo', type))
		layout.addRow(QLabel('Demo Update'), Edit('DemoUpdate', type))

		# self.layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

class Format(QWidget):
	def __init__(self):
		super().__init__()

		self.scroll = QScrollArea(self)
		self.scroll.setWidgetResizable(True)
		self.scroll.setFrameShape(QFrame.NoFrame)

		layout = QVBoxLayout(self.scroll)

		'''
		self.titleBase = 'titles/{name}[{id}][v{version}].nsp'
		self.titleDLC = 'titles/DLC/{name}[{id}][v{version}].nsp'
		self.titleUpdate = 'titles/updates/{name}[{id}][v{version}].nsp'
		self.titleDemo = 'titles/demos/{name}[{id}][v{version}].nsp'
		self.titleDemoUpdate = 'titles/demos/updates/{name}[{id}][v{version}].nsp'

		self.nszTitleBase = None
		self.nszTitleDLC = None
		self.nszTitleUpdate = None
		self.nszTitleDemo = None
		self.nszTitleDemoUpdate = None

		self.xciTitleBase = None
		self.xciTitleDLC = None
		self.xciTitleUpdate = None
		self.xciTitleDemo = None
		self.xciTitleDemoUpdate = None

		self.nsxTitleBase = None
		self.nsxTitleDLC = None
		self.nsxTitleUpdate = None
		self.nsxTitleDemo = None
		self.nsxTitleDemoUpdate = None

		testGroup = QFormLayout()

		testGroup.addRow(QLabel("Name:"), QLineEdit())
		testGroup.addRow(QLabel("Email:"), QLineEdit())
		testGroup.addRow(QLabel("Age:"), QLineEdit())
		'''
		layout.addWidget(Row(''))
		layout.addWidget(Row('nsz'))
		layout.addWidget(Row('xci'))
		# layout.addWidget(Row('nsx'))

		widget = QWidget()
		widget.setLayout(layout)
		self.scroll.setWidget(widget)

	def resizeEvent(self, event):
		del event
		self.scroll.setFixedWidth(self.width())
		self.scroll.setFixedHeight(self.height())

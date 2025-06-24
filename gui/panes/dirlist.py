# -*- coding: utf-8 -*-
import urllib.parse

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QPushButton, QVBoxLayout, QWidget, QScrollArea, QFrame)

import Fs.driver
from translator import tr


class Edit(QLineEdit):
	"""Edit UI control
	"""
	def __init__(self, parent):
		super().__init__()
		self.parent = parent

	def getValue(self):
		return self.text()

	def setValue(self, value):
		self.setText(value)

	def focusOutEvent(self, event):
		self.parent.save()

		super().focusOutEvent(event)

class FolderPicker(QDialog):
	"""FolderPicker UI control
	"""
	def __init__(self, url):
		super().__init__()
		self.setWindowTitle("Directory Picker")
		self.url = url

		self.list = QListWidget(self)

		self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		self.layout = QVBoxLayout()
		self.layout.addWidget(self.list)
		self.list.itemDoubleClicked.connect(self.onSelect)
		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.onReject)

		self.layout.addStretch()
		self.layout.addWidget(self.buttonBox)
		self.setLayout(self.layout)

		self.refreshList()

	def onReject(self):
		self.url = None
		self.reject()

	def onSelect(self, item):
		self.url = Fs.driver.join(self.url, item.text())
		self.refreshList()

	def refreshList(self):
		self.list.clear()
		for d in  Fs.driver.openDir(self.url).ls():
			if d.isFile():
				continue
			self.list.addItem(d.baseName())


	def save(self):
		pass

class GdrivePicker(QDialog): # pylint: disable=too-many-instance-attributes
	"""GdrivePicker UI control
	"""
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Directory Picker")
		self.url = None

		settings = QFormLayout()

		schemes = QComboBox(self)
		schemes.addItem('')
		schemes.addItem('ftp')
		schemes.addItem('ftps')
		schemes.addItem('gdrive')
		schemes.addItem('http')
		schemes.addItem('https')
		schemes.addItem('sftp')
		settings.addRow(QLabel('Scheme'), schemes)
		self.schemes = schemes

		self.username = Edit(self)
		settings.addRow(QLabel('Username'), self.username)

		self.password = Edit(self)
		settings.addRow(QLabel('Password'), self.password)

		self.host = Edit(self)
		settings.addRow(QLabel('Host'), self.host)

		self.port = Edit(self)
		settings.addRow(QLabel('Port'), self.port)

		self.path = Edit(self)
		settings.addRow(QLabel('Path'), self.path)

		self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		self.buttonBox.accepted.connect(self.setUrl)
		self.buttonBox.rejected.connect(self.reject)
		self.layout = QVBoxLayout()
		self.layout.addLayout(settings)
		self.layout.addStretch()
		self.layout.addWidget(self.buttonBox)
		self.setLayout(self.layout)

	def save(self):
		pass

	def setUrl(self):
		try:
			scheme = self.schemes.currentText()

			if not scheme:
				return

			if scheme == 'gdrive':
				self.url = 'gdrive:/'
			else:
				if not self.host.getValue():
					return
				self.url = scheme + '://'

				if self.username.getValue():
					self.url += urllib.parse.quote(self.username.getValue(), safe = '')

					if self.password.getValue():
						self.url += ':' + urllib.parse.quote(self.password.getValue(), safe = '')

					self.url += '@'

				self.url += self.host.getValue()

				if self.port.getValue():
					self.url += ':' + self.port.getValue()

				self.url += '/'

			if self.path.getValue():
				self.url = Fs.driver.join(self.url, self.path.getValue())

			self.accept()
		except BaseException: # pylint: disable=broad-except
			self.reject()

class DirectoryLocal(QWidget):
	"""DirectoryLocal UI control
	"""
	def __init__(self, parent):
		super().__init__()
		self.parent = parent

		layout = QHBoxLayout(self)
		self.dirBtn = QPushButton(tr('dirlist.browse'))
		self.dirBtn.setFixedWidth(70)
		self.dirBtn.clicked.connect(self.on_browse)
		self.dirBtn.setFocusPolicy(Qt.StrongFocus)

		self.edit = Edit(self)

		layout.addWidget(self.dirBtn)
		layout.addWidget(self.edit)
		self.layout = layout

	def save(self):
		self.parent.save()

	def on_browse(self):
		value = QFileDialog.getExistingDirectory(self, tr('Select Directory'),\
			self.getValue(), QFileDialog.ShowDirsOnly)

		if value:
			self.setValue(value)

	def getValue(self):
		return self.edit.getValue()

	def setValue(self, value):
		self.edit.setText(value)
		self.parent.save()

	def focusOutEvent(self, event):
		self.parent.save()

		super().focusOutEvent(event)

class DirectoryNetwork(QWidget):
	"""DirectoryNetwork UI control
	"""
	def __init__(self, parent):
		super().__init__()
		self.parent = parent

		layout = QHBoxLayout(self)
		self.dirBtn = QPushButton('browse')
		self.dirBtn.setFixedWidth(70)
		self.dirBtn.clicked.connect(self.on_browse)

		self.edit = Edit(self)

		layout.addWidget(self.dirBtn)
		layout.addWidget(self.edit)
		self.layout = layout

	def save(self):
		self.parent.save()

	def on_browse(self):
		d = GdrivePicker()
		if not d.exec_() or not d.url:
			return

		f = FolderPicker(d.url)

		if not f.exec_() or not f.url:
			return

		self.edit.setValue(f.url)
		self.save()

	def getValue(self):
		return self.edit.getValue()

	def setValue(self, value):
		self.edit.setText(value)

	def focusOutEvent(self, event):
		self.parent.save()

		super().focusOutEvent(event)

class Row(QWidget):
	"""Row UI control
	"""
	def __init__(self, parent, value, rowType=DirectoryLocal):
		super().__init__()
		self.parent = parent
		layout = QHBoxLayout(self)
		self.control = rowType(self)

		if value is not None:
			self.control.setValue(value)

		self.remove = QPushButton('X')
		self.remove.setFixedWidth(50)
		self.remove.clicked.connect(self.on_remove)
		self.remove.setFocusPolicy(Qt.StrongFocus)

		layout.addWidget(self.control)
		layout.addWidget(self.remove)

	def setValue(self, text):
		self.control.setValue(text)

	def getValue(self):
		return self.control.getValue()

	def on_remove(self):
		self.parent.removeWidget(self)

	def save(self):
		self.parent.save()

class DirList(QWidget):
	"""DirList UI control
	"""
	def __init__(self, values, onChange=None, rowType=DirectoryLocal):
		super().__init__()
		self.rowType = rowType

		self.scroll = QScrollArea(self)
		self.scroll.setWidgetResizable(True)
		self.scroll.setFrameShape(QFrame.NoFrame)

		layout = QVBoxLayout(self.scroll)
		self.list = QVBoxLayout()
		self.button = QPushButton('Add')

		self.button.clicked.connect(self.on_click)

		layout.addLayout(self.list)
		layout.addWidget(self.button)
		layout.addStretch()

		widget = QWidget()
		widget.setLayout(layout)
		self.scroll.setWidget(widget)

		self.layout = layout
		self.onChange = onChange

		for value in values:
			self.add(value)

	def resizeEvent(self, _):
		self.scroll.setFixedWidth(self.width())
		self.scroll.setFixedHeight(self.height())

	def on_click(self):
		self.add(None)

	def add(self, value):
		self.list.addWidget(Row(self, value, self.rowType))

	def save(self):
		if self.onChange:
			self.onChange(self)

	def removeWidget(self, widget):
		self.list.removeWidget(widget)
		widget.setParent(None)

		self.save()

	def count(self):
		return self.list.count()

	def itemAt(self, i):
		return self.list.itemAt(i)

	def getValue(self, i):
		return self.itemAt(i).widget().getValue()

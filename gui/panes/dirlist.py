import os
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QFileDialog, QDialog
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from nut import Users

class GdrivePicker(QDialog):
	def __init__(self):
		super(GdrivePicker, self).__init__()

class Edit(QLineEdit):
	def __init__(self, parent):
		super(QLineEdit, self).__init__()
		self.parent = parent

	def getValue(self):
		return self.text()

	def setValue(self, value):
		self.setText(value)

	def focusOutEvent(self, event):
		self.parent.save()

		super(Edit, self).focusOutEvent(event)

class User(QWidget):
	def __init__(self, parent):
		super(User, self).__init__()
		self.parent = parent

		layout = QHBoxLayout(self)
		self.user = Edit(self)
		self.password = Edit(self)

		layout.addWidget(self.user)
		layout.addWidget(self.password)
		self.layout = layout

	def save(self):
		self.parent.save()

	def getValue(self):
		user = Users.User()
		user.id = self.user.getValue()
		user.password = self.password.getValue()
		return user

	def setValue(self, user):
		self.user.setText(user.id)
		self.password.setText(user.password)

	def focusOutEvent(self, event):
		self.parent.save()

		super(Edit, self).focusOutEvent(event)

class Directory(QWidget):
	def __init__(self, parent):
		super(Directory, self).__init__()
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
		value = QFileDialog.getExistingDirectory(self, 'Select Directory', self.getValue(), QFileDialog.ShowDirsOnly)

		if value:
			self.setValue(value)

	def getValue(self):
		return self.edit.getValue()

	def setValue(self, value):
		self.edit.setText(value)

	def focusOutEvent(self, event):
		self.parent.save()

		super(Edit, self).focusOutEvent(event)

class Row(QWidget):
	def __init__(self, parent, value, rowType=Directory):
		super(Row, self).__init__()
		self.parent = parent
		layout = QHBoxLayout(self)
		self.control = rowType(self)

		if value is not None:
			self.control.setValue(value)

		self.close = QPushButton('X')
		self.close.setFixedWidth(50)
		self.close.clicked.connect(self.on_close)
		layout.addWidget(self.control)
		layout.addWidget(self.close)

	def setValue(self, text):
		self.control.setValue(text)

	def getValue(self):
		return self.control.getValue()

	def on_close(self):
		self.parent.removeWidget(self)

	def save(self):
		self.parent.save()

class DirList(QWidget):
	def __init__(self, values=[], onChange=None, rowType=Directory):
		super(DirList, self).__init__()
		self.rowType = rowType

		layout = QVBoxLayout(self)
		self.list = QVBoxLayout()
		self.button = QPushButton('Add')

		self.button.clicked.connect(self.on_click)

		layout.addLayout(self.list)
		layout.addWidget(self.button)
		layout.addStretch()

		self.layout = layout
		self.onChange = onChange

		for value in values:
			self.add(value)

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

import os
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from nut import Nsps

class Files(QTableWidget):
	def __init__(self):
		super(QTableWidget, self).__init__()
		self.setColumnCount(4)

		headers = [QTableWidgetItem("File"), QTableWidgetItem("Title ID"), QTableWidgetItem("Type"), QTableWidgetItem("Size")]

		i = 0
		for h in headers:
			self.setHorizontalHeaderItem(i, h)
			i = i + 1

		header = self.horizontalHeader()
		i = 0
		for h in headers:
			header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch if i == 0 else QtWidgets.QHeaderView.ResizeToContents)
			i = i + 1

		self.refresh()

	def refresh(self):
		self.setRowCount(len(Nsps.files))
		i = 0
		for k, f in Nsps.files.items():
			title = f.title()
			if f.path.endswith('.nsx') or not title.isActive(True):
				continue

			self.setItem(i, 0, QTableWidgetItem(os.path.basename(f.path)))
			self.setItem(i, 1, QTableWidgetItem(str(f.titleId)))
			self.setItem(i, 2, QTableWidgetItem("UPD" if title.isUpdate else ("DLC" if title.isDLC else "BASE")))
			self.setItem(i, 3, QTableWidgetItem(str(f.fileSize or title.size)))
			i = i + 1

		self.setRowCount(i)

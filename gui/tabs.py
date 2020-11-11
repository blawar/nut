import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget,QVBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

class Tabs(QWidget):
	def __init__(self, tabs):
		super(QWidget, self).__init__()
		self.layout = QVBoxLayout(self)
		self.tabs = QTabWidget()

		self.tabs.resize(300,200)

		for name, obj in tabs.items():
			self.tabs.addTab(obj, name)

		self.layout.addWidget(self.tabs)

	@pyqtSlot()
	def on_click(self):
		print("\n")
		for currentQTableWidgetItem in self.tableWidget.selectedItems():
			print(currentQTableWidgetItem.row(), currentQTableWidgetItem.column(), currentQTableWidgetItem.text())

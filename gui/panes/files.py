
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableView

from nut import Nsps
from gui.table_model import TableModel


class Files(QTableView):
	def __init__(self):
		super(QTableView, self).__init__()
		self.model = TableModel(self)
		self.setModel(self.model)

		header = self.horizontalHeader()
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

		self.setSortingEnabled(True)
		self.sortByColumn(0, Qt.AscendingOrder)

		self.refresh()

	def refresh(self):
		self.setUpdatesEnabled(False)
		self.model.update(Nsps.files)
		self.setUpdatesEnabled(True)

import os
from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt

from nut import Print


def _format_size(num, suffix='B'):
	if num is None:
		return ''
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)

class Column(Enum):
	FILENAME = 0
	TITLE_ID = 1
	TITLE_TYPE = 2
	FILE_SIZE = 3

class SortDirection(Enum):
	ASC = 0
	DESC = 1

class TableModel(QAbstractTableModel):
	def __init__(self, parent=None):
		super(TableModel, self).__init__()
		self.datatable = []
		self.column_count = 4
		self.headers = [
			"File", "Title ID", "Type", "Size"
		]
		self.sort_column = 0
		self.sort_order = SortDirection.ASC

	def update(self, dataIn):
		Print.debug('TableModel update start')
		self.datatable = []

		for value in dataIn.values():
			new_item = {}
			new_item[Column.FILENAME] = os.path.basename(value.path)
			new_item[Column.TITLE_ID] = str(value.titleId)
			titleType = "UPD" if value.isUpdate() else "DLC" if value.isDLC() \
					else "BASE"
			new_item[Column.TITLE_TYPE] = titleType
			new_item[Column.FILE_SIZE] = value.fileSize
			self.datatable.append(new_item)

		self._sort()
		Print.debug('TableModel update finished')

	def rowCount(self, parent=QtCore.QModelIndex()):
		return len(self.datatable)

	def columnCount(self, parent=QtCore.QModelIndex()):
		return self.column_count

	def data(self, index, role=Qt.DisplayRole):
		if role == Qt.DisplayRole:
			i = index.row()
			j = index.column()
			row = self.datatable[i]
			if Column(j) == Column.FILE_SIZE:
				return _format_size(row[Column(j)])
			return f"{row[Column(j)]}"
		else:
			return QtCore.QVariant()

	def flags(self, index):
		return Qt.ItemIsEnabled

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return QtCore.QVariant()
		if orientation == Qt.Horizontal:
			return self.headers[section]
		return str(section)

	def _sort(self):
		self.layoutAboutToBeChanged.emit()
		self.datatable.sort(key=lambda item: item[Column(self.sort_column)], \
			reverse=self.sort_order != SortDirection.ASC)
		self.layoutChanged.emit()

	def sort(self, column, order=Qt.AscendingOrder):
		self.sort_column = column
		self.sort_order = SortDirection.ASC if order == Qt.AscendingOrder else SortDirection.DESC
		self._sort()

	def setRowCount(self, row_count):
		if row_count == 0:
			self.datatable = []

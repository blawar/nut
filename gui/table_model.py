# -*- coding: utf-8 -*-
import os
from enum import Enum

from PyQt6 import QtCore
from PyQt6.QtCore import QAbstractTableModel, Qt

import humanize

from nut import Print


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
		del parent
		super().__init__()
		self.datatable = []
		self.column_count = 4
		self.headers = ["File", "Title ID", "Type", "Size"]
		self.sort_column = 0
		self.sort_order = SortDirection.ASC

	def update(self, dataIn):
		Print.debug("TableModel update start")
		self.datatable = []

		for value in dataIn.values():
			new_item = {}
			new_item[Column.FILENAME] = os.path.basename(value.path)
			new_item[Column.TITLE_ID] = str(value.titleId)
			titleType = (
				"UPD" if value.isUpdate() else "DLC" if value.isDLC() else "BASE"
			)
			new_item[Column.TITLE_TYPE] = titleType
			new_item[Column.FILE_SIZE] = value.fileSize
			self.datatable.append(new_item)

		self._sort()
		Print.debug("TableModel update finished")

	def rowCount(self, parent=QtCore.QModelIndex()):
		del parent
		return len(self.datatable)

	def columnCount(self, parent=QtCore.QModelIndex()):
		del parent
		return self.column_count

	def data(self, index, role=Qt.ItemDataRole.DisplayRole):
		if role == Qt.ItemDataRole.DisplayRole:
			i = index.row()
			j = index.column()
			row = self.datatable[i]
			if Column(j) == Column.FILE_SIZE:
				return humanize.naturalsize(row[Column(j)], True)
			return f"{row[Column(j)]}"
		return QtCore.QVariant()

	def flags(self, index):
		del index
		return Qt.ItemFlag.ItemIsEnabled

	def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
		if role != Qt.ItemDataRole.DisplayRole:
			return QtCore.QVariant()
		if orientation == Qt.Orientation.Horizontal:
			return self.headers[section]
		return str(section)

	def _sort(self):
		self.layoutAboutToBeChanged.emit()
		self.datatable.sort(
			key=lambda item: item[Column(self.sort_column)],
			reverse=self.sort_order != SortDirection.ASC,
		)
		self.layoutChanged.emit()

	def sort(self, column, order=Qt.SortOrder.AscendingOrder):
		self.sort_column = column
		self.sort_order = (
			SortDirection.ASC
			if order == Qt.SortOrder.AscendingOrder
			else SortDirection.DESC
		)
		self._sort()

	def setRowCount(self, row_count):
		if row_count == 0:
			self.datatable = []

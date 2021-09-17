# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QGridLayout, QGroupBox, QHBoxLayout,
							 QLabel, QSizePolicy, QVBoxLayout, QWidget, QScrollArea, QFrame)
from qt_range_slider import QtRangeSlider

from nut import Config
from translator import tr


# pylint: disable=fixme
# TODO: move to a separate module
def _format_size(num, suffix='B'):
	if num is None:
		return ''
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return f"{num:3.1f} {unit}{suffix}"
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)

class ConfCheckbox(QCheckBox):
	"""ConfCheckbox
	"""
	def __init__(self, text, conf):
		super().__init__(text)
		self.conf = conf
		value = self.get()
		self.setChecked(value)
		self.stateChanged.connect(self.onStateChanged)

	def onStateChanged(self, state):
		print(f"ConfCheckbox state changed: {state}")
		self.set(self.isChecked())
		Config.save()

	def get(self):
		try:
			j = Config
			for path in self.conf.split('.'):
				j = getattr(j, path)
			return j
		except BaseException: # pylint: disable=broad-except
			return None

	def set(self, value):
		j = Config
		paths = self.conf.split('.')
		last = paths.pop()
		for path in paths:
			j = getattr(j, path)
		setattr(j, last, value)

class RegionEntry(QWidget):
	"""RegionEntry
	"""
	def __init__(self, region):
		super().__init__()
		self.region = region.upper()
		layout = QHBoxLayout(self)
		self.check = QCheckBox(region)

		self.check.setChecked(Config.download.hasRegion([region], False))
		self.check.stateChanged.connect(self.onStateChanged)
		layout.addWidget(self.check)
		layout.addStretch()

	def onStateChanged(self, state):
		print(f"RegionEntry state changed: {state}")
		if self.check.isChecked():
			Config.download.addRegion(self.region)
		else:
			Config.download.removeRegion(self.region)
		Config.save()


class Region(QWidget):
	"""Region
	"""
	def __init__(self):
		super().__init__()

		layout = QGridLayout(self)

		regions = []
		for region, _ in Config.regionLanguages().items():
			regions.append(region)

		regions.sort()

		width = 4
		i = 0
		for region in regions:
			layout.addWidget(RegionEntry(region), i // width, i % width)
			i += 1

class Filters(QWidget):
	"""Filters
	"""
	def __init__(self):
		super().__init__()

		self.MIN_FILE_SIZE = 0
		self.MAX_FILE_SIZE = 30 * 1024**3

		self.scroll = QScrollArea(self)
		self.scroll.setWidgetResizable(True)
		self.scroll.setFrameShape(QFrame.NoFrame)

		layout = QVBoxLayout(self.scroll)

		typesGroup = QGroupBox(tr('filters.types.group'))

		Filters._createTypesGroup(layout, typesGroup)

		Filters._createRegionGroup(layout)

		sizeFilterGroup = QGroupBox(tr('filters.size.group'))
		sizeFilterLayout = QHBoxLayout(sizeFilterGroup)

		minFileSizeFilter = 0
		if Config.download.fileSizeMax is not None:
			minFileSizeFilter = Config.download.fileSizeMin
		maxFileSizeFilter = self.MAX_FILE_SIZE
		if Config.download.fileSizeMax is not None:
			maxFileSizeFilter = Config.download.fileSizeMax

		filterMinSizeLabel = Filters._createLeftLabel(sizeFilterLayout, minFileSizeFilter)

		rangeSlider = self._createRangeSlider(sizeFilterLayout, minFileSizeFilter, maxFileSizeFilter)

		filterMaxSizeLabel = Filters._createRightLabel(sizeFilterLayout, rangeSlider.get_right_thumb_value())

		layout.addWidget(sizeFilterGroup)

		widget = QWidget()
		widget.setLayout(layout)
		self.scroll.setWidget(widget)

		rangeSlider.left_thumb_value_changed.connect((lambda x: \
			Filters._on_left_thumb_value_changed(filterMinSizeLabel, x)))
		rangeSlider.right_thumb_value_changed.connect((lambda x: \
			Filters._on_right_thumb_value_changed(filterMaxSizeLabel, x)))

	def resizeEvent(self, _):
		self.scroll.setFixedWidth(self.width())
		self.scroll.setFixedHeight(self.height())

	@staticmethod
	def _on_left_thumb_value_changed(label, value):
		label.setText(_format_size(value))
		Config.download.fileSizeMin = value
		Config.save()

	@staticmethod
	def _on_right_thumb_value_changed(label, value):
		label.setText(_format_size(value))
		Config.download.fileSizeMax = value
		Config.save()

	@staticmethod
	def _createRegionGroup(layout):
		region = QGroupBox('REGION')
		regionLayout = QHBoxLayout(region)
		regionLayout.addWidget(Region())
		layout.addWidget(region)

	@staticmethod
	def _createTypesGroup(layout, typesGroup):
		typesLayout = QHBoxLayout(typesGroup)

		typesLayout.addWidget(ConfCheckbox(tr('filters.types.base'), 'download.base'))
		typesLayout.addStretch()

		typesLayout.addWidget(ConfCheckbox(tr('filters.types.dlc'), 'download.DLC'))
		typesLayout.addStretch()

		typesLayout.addWidget(ConfCheckbox(tr('filters.types.update'), 'download.update'))
		typesLayout.addStretch()

		typesLayout.addWidget(ConfCheckbox(tr('filters.types.demo'), 'download.demo'))

		layout.addWidget(typesGroup)

	@staticmethod
	def _createLeftLabel(layout, value):
		return Filters._createLabel(layout, value, Qt.AlignRight)

	@staticmethod
	def _createRightLabel(layout, value):
		return Filters._createLabel(layout, value, Qt.AlignLeft)

	def _createRangeSlider(self, layout, minValue, maxValue):
		rangeSlider = QtRangeSlider(self, self.MIN_FILE_SIZE, self.MAX_FILE_SIZE, minValue, maxValue)
		layout.addWidget(rangeSlider)
		return rangeSlider

	@staticmethod
	def _createLabel(layout, value, alignment):
		label = QLabel(f"{_format_size(value)}")
		label.setFixedWidth(80)
		label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		label.setAlignment(alignment)

		layout.addWidget(label)
		return label

from PyQt5.QtCore import QRect, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QBoxLayout, QCheckBox,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMainWindow, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QVBoxLayout, QWidget, QSlider)

from qt_range_slider import QtRangeSlider

from nut import Config
from translator import tr

# TODO: move to a separate module
def _format_size(num, suffix='B'):
	if num is None:
		return ''
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)

class ConfCheckbox(QCheckBox):
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
	def __init__(self):
		super().__init__()

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
		super().__init__()

		layout = QVBoxLayout(self)

		types = QGroupBox(tr('filters.types.group'))

		testGroup = QHBoxLayout(types)

		testGroup.addWidget(ConfCheckbox(tr('filters.types.base'), 'download.base'))
		testGroup.addStretch()

		testGroup.addWidget(ConfCheckbox(tr('filters.types.dlc'), 'download.DLC'))
		testGroup.addStretch()

		testGroup.addWidget(ConfCheckbox(tr('filters.types.update'), 'download.update'))
		testGroup.addStretch()

		testGroup.addWidget(ConfCheckbox(tr('filters.types.demo'), 'download.demo'))

		layout.addWidget(types)

		region = QGroupBox('REGION')
		regionLayout = QHBoxLayout(region)
		regionLayout.addWidget(Region())
		layout.addWidget(region)

		sizeFilterGroup = QGroupBox(tr('filters.size.group'))
		sizeFilterLayout = QHBoxLayout(sizeFilterGroup)
		MIN_FILE_SIZE = 0
		MAX_FILE_SIZE = 30*1024*1024*1024
		minFileSizeFilter = 0
		if Config.download.fileSizeMax is not None:
			minFileSizeFilter = Config.download.fileSizeMin
		maxFileSizeFilter = MAX_FILE_SIZE
		if Config.download.fileSizeMax is not None:
			maxFileSizeFilter = Config.download.fileSizeMax
		filterMinSizeLabel = QLabel(f"{_format_size(minFileSizeFilter)}")
		filterMinSizeLabel.setMinimumWidth(60)
		sizeFilterLayout.addWidget(filterMinSizeLabel)
		barSlider = QtRangeSlider(self, MIN_FILE_SIZE, MAX_FILE_SIZE, minFileSizeFilter, \
			maxFileSizeFilter)
		sizeFilterLayout.addWidget(barSlider)
		filterMaxSizeLabel = QLabel(_format_size(barSlider.get_right_thumb_value()))
		filterMaxSizeLabel.setMinimumWidth(60)
		sizeFilterLayout.addWidget(filterMaxSizeLabel)
		layout.addWidget(sizeFilterGroup)

		barSlider.left_thumb_value_changed.connect((lambda x: filterMinSizeLabel.setText(_format_size(x))))
		barSlider.right_thumb_value_changed.connect((lambda x: filterMaxSizeLabel.setText(_format_size(x))))

		layout.addStretch()

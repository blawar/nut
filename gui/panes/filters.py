from PyQt5.QtCore import QRect, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QBoxLayout, QCheckBox,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMainWindow, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QVBoxLayout, QWidget, QSlider)

from nut import Config
from translator import tr

from gui.bar_slider import BarSlider


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

		rank_group = QGroupBox('Rank filter')
		rank_filter_layout = QHBoxLayout(rank_group)
		filter_min_label = QLabel('0')
		filter_min_label.setMinimumWidth(20)
		rank_filter_layout.addWidget(filter_min_label)
		bar_slider = BarSlider(self)
		rank_filter_layout.addWidget(bar_slider)
		filter_max_label = QLabel(str(bar_slider.get_right_thumb_value()))
		filter_max_label.setMinimumWidth(20)
		rank_filter_layout.addWidget(filter_max_label)
		layout.addWidget(rank_group)

		bar_slider.leftThumbValueChanged.connect(filter_min_label.setNum)
		bar_slider.rightThumbValueChanged.connect(filter_max_label.setNum)

		layout.addStretch()

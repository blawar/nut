# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QHBoxLayout, QSlider, QGroupBox, QCheckBox
from PyQt5.QtCore import Qt
from nut import Config


def _init_slider(slider, min_value, max_value, value):
	slider.setMinimum(min_value)
	slider.setMaximum(max_value)
	slider.setValue(value)
	slider.valueChanged.connect(slider.save)


class Threads(QSlider):
	def __init__(self, parent):
		super().__init__(Qt.Horizontal)
		self.parent = parent
		_init_slider(self, 1, 8, Config.threads)

	def save(self):
		Config.threads = self.value()
		Config.save()

		if self.parent:
			self.parent.save()


class Compress(QSlider):
	def __init__(self, parent):
		super().__init__(Qt.Horizontal)
		self.parent = parent
		_init_slider(self, 0, 22, Config.compression.level)

	def save(self):
		Config.compression.level = self.value()
		Config.save()

		if self.parent:
			self.parent.save()


class SliderControl(QWidget):
	def __init__(self, _type):
		super().__init__()
		layout = QHBoxLayout(self)
		self.slider = _type(self)
		layout.addWidget(self.slider)
		self.label = QLabel(str(self.slider.value()))
		layout.addWidget(self.label)

	def save(self):
		self.label.setText(str(self.slider.value()))


class ConfCheckbox(QCheckBox):
	"""ConfCheckbox
	"""

	def __init__(self, text, conf):
		super().__init__(text)
		self.conf = conf
		value = getattr(Config, text)
		self.setChecked(value)
		self.setText(text.upper().replace('_', ' '))
		self.stateChanged.connect(self.onStateChanged)

	def onStateChanged(self, state):
		print(f"ConfCheckbox state changed: {state}")
		cleaned_text = self.text().lower().replace(' ', '_')
		setattr(Config, cleaned_text, self.isChecked())
		Config.save()


class Options(QWidget):
	def __init__(self):
		super().__init__()

		layout = QVBoxLayout(self)

		serverGroup = QFormLayout()

		layout.addLayout(serverGroup)

		group = QGroupBox('THREADS')
		groupLayout = QHBoxLayout(group)
		groupLayout.addWidget(SliderControl(_type=Threads))
		layout.addWidget(group)

		group = QGroupBox('COMPRESSION LEVEL')
		groupLayout = QHBoxLayout(group)
		groupLayout.addWidget(SliderControl(_type=Compress))
		layout.addWidget(group)

		group = QGroupBox('OTHERS - Must restart to take affect')
		groupLayout = QHBoxLayout(group)
		groupLayout.addWidget(ConfCheckbox('allow_organize', Config.allow_organize))
		groupLayout.addWidget(ConfCheckbox('allow_pull', Config.allow_pull))
		groupLayout.addWidget(ConfCheckbox('allow_decompress', Config.allow_decompress))
		groupLayout.addWidget(ConfCheckbox('allow_compress', Config.allow_compress))
		groupLayout.addWidget(ConfCheckbox('allow_gdrive', Config.allow_gdrive))
		layout.addWidget(group)

		layout.addStretch()

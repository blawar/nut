# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt

class Tabs(QWidget):
	def __init__(self, tabs):
		super().__init__()
		self.layout = QVBoxLayout(self)
		self.tabs = QTabWidget()

		self.tabs.resize(300, 200)

		for name, obj in tabs.items():
			self.tabs.addTab(obj, name)

		self.layout.addWidget(self.tabs)

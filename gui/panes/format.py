# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
	QFormLayout,
	QGroupBox,
	QLabel,
	QLineEdit,
	QScrollArea,
	QVBoxLayout,
	QWidget,
	QFrame,
)

from nut import Config


class Edit(QLineEdit):
	"""Edit class"""

	def __init__(self, id_, type_):
		super().__init__()
		self.id = id_
		self.type = type_

		if type_:
			self.key = type_.lower() + "Title" + id_
		else:
			self.key = "title" + id_

		self.setText(getattr(Config.paths, self.key))
		# self.textChanged.connect(self.onChange)

	def focusOutEvent(self, event):
		print(f"Edit focusOutEvent: {event}")
		current = getattr(Config.paths, self.key) or ""
		new = self.text()

		if current != new:
			setattr(Config.paths, self.key, new)
			Config.save()

		super().focusOutEvent(event)

	def onChange(self):
		print("changed: " + self.id)


class Row(QGroupBox):
	"""Row class"""

	def __init__(self, type_=""):
		super().__init__((type_ or "nsp").upper())
		layout = QFormLayout(self)

		layout.addRow(QLabel("Base"), Edit("Base", type_))
		layout.addRow(QLabel("DLC"), Edit("DLC", type_))
		layout.addRow(QLabel("Update"), Edit("Update", type_))
		layout.addRow(QLabel("Demo"), Edit("Demo", type_))
		layout.addRow(QLabel("Demo Update"), Edit("DemoUpdate", type_))

		# self.layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)


class Format(QWidget):
	"""Format class"""

	def __init__(self):
		super().__init__()

		self.scroll = QScrollArea(self)
		self.scroll.setWidgetResizable(True)
		self.scroll.setFrameShape(QFrame.Shape.NoFrame)

		layout = QVBoxLayout(self.scroll)

		layout.addWidget(Row(""))
		layout.addWidget(Row("nsz"))
		layout.addWidget(Row("xci"))
		# layout.addWidget(Row('nsx'))

		widget = QWidget()
		widget.setLayout(layout)
		self.scroll.setWidget(widget)

	def resizeEvent(self, _):
		self.scroll.setFixedWidth(self.width())
		self.scroll.setFixedHeight(self.height())

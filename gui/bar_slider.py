from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (QWidget, QSizePolicy)
from PyQt5.QtGui import QPainter, QBrush, QColor

class BarSlider(QWidget):
	def __init__(self):
		super().__init__()

		self.setSizePolicy(
			QSizePolicy.MinimumExpanding,
			QSizePolicy.MinimumExpanding
		)

	def sizeHint(self):
		return QSize(40,120)

	def paintEvent(self, e):
		painter = QPainter(self)

		brush = QBrush()
		brush.setColor(QColor('black'))
		brush.setStyle(Qt.SolidPattern)
		rect = QRect(0, 0, painter.device().width(), painter.device().height())
		painter.fillRect(rect, brush)

		pen = painter.pen()
		pen.setColor(QColor('red'))
		painter.setPen(pen)

		font = painter.font()
		font.setFamily('Times')
		font.setPointSize(18)
		painter.setFont(font)

		painter.drawText(25, 25, "{}-->{}<--{}".format(0, 15, 30))
		painter.end()

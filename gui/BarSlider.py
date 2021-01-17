from dataclasses import dataclass

from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QSizePolicy)
from PyQt5.QtGui import QPainter, QBrush, QColor, QPalette


@dataclass
class Thumb:
	"""Thumb class which holds information about a thumb
	"""
	value: int
	rect: QRect
	pressed: bool

class BarSlider(QWidget):
	"""BarSlider is a class which implements a slider with 2 thumbs
	"""
	HEIGHT = 30
	WIDTH = 120
	THUMB_WIDTH = 16
	THUMB_HEIGHT = 16
	TRACK_HEIGHT = 3
	TRACK_COLOR = QColor(0xc7, 0xc7, 0xc7)
	TRACK_FILL_COLOR = QColor(0x01, 0x81, 0xff)
	TRACK_PADDING = THUMB_WIDTH // 2 + 5

	leftThumbValueChanged = pyqtSignal(int)
	rightThumbValueChanged = pyqtSignal(int)

	def __init__(self, parent):
		super().__init__(parent)

		self.setSizePolicy(
			QSizePolicy.MinimumExpanding,
			QSizePolicy.MinimumExpanding
		)

		self._left_value = 0
		self._right_value = 10

		self._left_thumb = Thumb(3, None, False)
		self._right_thumb = Thumb(7, None, False)

		self._canvas_width = None

		parent_palette = parent.palette()
		self._background_color = parent_palette.color(QPalette.Window)
		self._base_color = parent_palette.color(QPalette.Base)
		self._button_color = parent_palette.color(QPalette.Button)
		self._border_color = parent_palette.color(QPalette.Mid)


	def sizeHint(self):
		return QSize(self.HEIGHT, self.WIDTH)

	def paintEvent(self, unused_e):
		del unused_e
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)

		self._canvas_width = painter.device().width()
		canvas_height = painter.device().height()

		self.__drawTrack(self._canvas_width, canvas_height, painter)
		self.__drawTrackFill(self._canvas_width, canvas_height, painter)
		self.__drawLeftThumb(self._canvas_width, canvas_height, painter)
		self.__drawRightThumb(self._canvas_width, canvas_height, painter)

		painter.end()

	def __getTrackYPosition(self, canvas_height):
		return canvas_height // 2 - self.TRACK_HEIGHT // 2


	def __drawTrack(self, canvas_width, canvas_height, painter):
		brush = QBrush()
		brush.setColor(self.TRACK_COLOR)
		brush.setStyle(Qt.SolidPattern)

		rect = QRect(self.TRACK_PADDING, self.__getTrackYPosition(canvas_height), \
			canvas_width - 2 * self.TRACK_PADDING, self.TRACK_HEIGHT)
		painter.fillRect(rect, brush)

	def __drawTrackFill(self, canvas_width, canvas_height, painter):
		brush = QBrush()
		brush.setColor(self.TRACK_FILL_COLOR)
		brush.setStyle(Qt.SolidPattern)

		available_width = canvas_width - 2 * self.TRACK_PADDING
		x1 = self._left_thumb.value / self._right_value * available_width + self.TRACK_PADDING
		x2 = self._right_thumb.value / self._right_value * available_width + self.TRACK_PADDING
		rect = QRect(x1, self.__getTrackYPosition(canvas_height), \
			x2 - x1, self.TRACK_HEIGHT)
		painter.fillRect(rect, brush)

	def __drawThumb(self, x, y, painter):
		brush = QBrush()
		brush.setColor(self._base_color)
		brush.setStyle(Qt.SolidPattern)

		pen = painter.pen()
		pen.setColor(self._border_color)
		painter.setPen(pen)

		painter.setBrush(brush)

		thumb_rect = QRect(x - self.THUMB_WIDTH // 2 + self.TRACK_PADDING, \
			y + self.TRACK_HEIGHT // 2 - self.THUMB_HEIGHT // 2, self.THUMB_WIDTH, self.THUMB_HEIGHT)
		painter.drawEllipse(thumb_rect)
		return thumb_rect

	def __drawRightThumb(self, canvas_width, canvas_height, painter):
		available_width = canvas_width - 2 * self.TRACK_PADDING
		x = self._right_thumb.value / self._right_value * available_width
		y = self.__getTrackYPosition(canvas_height)
		self._right_thumb.rect = self.__drawThumb(x, y, painter)

	def __drawLeftThumb(self, canvas_width, canvas_height, painter):
		available_width = canvas_width - 2 * self.TRACK_PADDING
		x = round(self._left_thumb.value / self._right_value * available_width)
		y = self.__getTrackYPosition(canvas_height)
		self._left_thumb.rect = self.__drawThumb(x, y, painter)

	def setLeftThumbValue(self, value):
		if value < 0 or value > self._right_thumb.value - 1:
			return
		if value == self._left_thumb.value:
			# nothing to update
			return
		self._left_thumb.value = value
		self.leftThumbValueChanged.emit(value)
		self.repaint()

	def setRightThumbValue(self, value):
		if value > self._right_value or value < self._left_thumb.value + 1:
			return
		if value == self._right_thumb.value:
			# nothing to update
			return
		self._right_thumb.value = value
		self.rightThumbValueChanged.emit(value)
		self.repaint()

	def mousePressEvent(self, event):
		if self._left_thumb.rect.contains(event.x(), event.y()):
			self._left_thumb.pressed = True
		if self._right_thumb.rect.contains(event.x(), event.y()):
			self._right_thumb.pressed = True
		super().mousePressEvent(event)

	def mouseReleaseEvent(self, event):
		self._left_thumb.pressed = False
		self._right_thumb.pressed = False
		super().mousePressEvent(event)

	# pylint: disable=no-self-use
	def __getThumbValue(self, x, canvas_width, right_value):
		return round(x / canvas_width * right_value)

	def mouseMoveEvent(self, event):
		if self._left_thumb.pressed:
			new_val = self.__getThumbValue(event.x(), self._canvas_width, self._right_value)
			self.setLeftThumbValue(new_val)
			return

		if self._right_thumb.pressed:
			new_val = self.__getThumbValue(event.x(), self._canvas_width, self._right_value)
			self.setRightThumbValue(new_val)

	def getRightThumbValue(self):
		return self._right_thumb.value

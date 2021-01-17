from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QSizePolicy)
from PyQt5.QtGui import QPainter, QBrush, QColor, QPalette

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
		self._left_thumb_value = 3 #self.left_value
		self._right_thumb_value = 7 # self.right_value

		self._left_thumb_rect = None
		self._right_thumb_rect = None

		parent_palette = parent.palette()
		self._background_color = parent_palette.color(QPalette.Window)
		self._base_color = parent_palette.color(QPalette.Base)
		self._button_color = parent_palette.color(QPalette.Button)
		self._border_color = parent_palette.color(QPalette.Mid)


	def sizeHint(self):
		return QSize(self.HEIGHT, self.WIDTH)

	def paintEvent(self, e):
		self._draw()

	def _draw(self):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)

		canvas_width = painter.device().width()
		canvas_height = painter.device().height()

		self._draw_track(canvas_width, canvas_height, painter)
		self._draw_track_fill(canvas_width, canvas_height, painter)
		self._draw_left_thumb(canvas_width, canvas_height, painter)
		self._draw_right_thumb(canvas_width, canvas_height, painter)

		# pen = painter.pen()
		# pen.setColor(QColor('red'))
		# painter.setPen(pen)

		# font = painter.font()
		# font.setFamily('Times')
		# font.setPointSize(18)
		# painter.setFont(font)

		# painter.drawText(25, 25, "{}-->{}<--{}".format(0, 15, 30))

		painter.end()

	def _get_track_y_position(self, canvas_height):
		return canvas_height // 2 - self.TRACK_HEIGHT // 2


	def _draw_track(self, canvas_width, canvas_height, painter):
		brush = QBrush()
		brush.setColor(self.TRACK_COLOR)
		brush.setStyle(Qt.SolidPattern)

		rect = QRect(0, self._get_track_y_position(canvas_height), canvas_width, self.TRACK_HEIGHT)
		painter.fillRect(rect, brush)

	def _draw_track_fill(self, canvas_width, canvas_height, painter):
		brush = QBrush()
		brush.setColor(self.TRACK_FILL_COLOR)
		brush.setStyle(Qt.SolidPattern)

		x1 = self._left_thumb_value / self._right_value * canvas_width
		x2 = self._right_thumb_value / self._right_value * canvas_width
		rect = QRect(x1, self._get_track_y_position(canvas_height), x2 - x1, self.TRACK_HEIGHT)
		painter.fillRect(rect, brush)

	def _draw_thumb(self, x, y, painter):
		brush = QBrush()
		brush.setColor(self._base_color)
		brush.setStyle(Qt.SolidPattern)

		pen = painter.pen()
		pen.setColor(self._border_color)
		painter.setPen(pen)

		painter.setBrush(brush)

		thumb_rect = QRect(x - self.THUMB_WIDTH // 2, \
			y + self.TRACK_HEIGHT // 2 - self.THUMB_HEIGHT // 2, self.THUMB_WIDTH, self.THUMB_HEIGHT)
		painter.drawEllipse(thumb_rect)
		return thumb_rect

	def _draw_right_thumb(self, canvas_width, canvas_height, painter):
		x = self._right_thumb_value / self._right_value * canvas_width
		y = self._get_track_y_position(canvas_height)
		self._right_thumb_rect = self._draw_thumb(x, y, painter)

	def _draw_left_thumb(self, canvas_width, canvas_height, painter):
		x = self._left_thumb_value / self._right_value * canvas_width
		y = self._get_track_y_position(canvas_height)
		self._left_thumb_rect = self._draw_thumb(x, y, painter)

	def set_left_thumb_value(self, value):
		if value < 0 or value > self._right_thumb_value:
			return
		self._left_thumb_value = value
		self.leftThumbValueChanged.emit(value)
		self.repaint()

	def set_right_thumb_value(self, value):
		if value > self._right_value:
			return
		self._right_thumb_value = value
		self.rightThumbValueChanged.emit(value)
		self.repaint()

	def mousePressEvent(self, event):
		print('mousePressEvent')
		if self._left_thumb_rect.contains(event.x(), event.y()):
			self.set_left_thumb_value(self._left_thumb_value - 1)
		if self._right_thumb_rect.contains(event.x(), event.y()):
			self.set_right_thumb_value(self._right_thumb_value + 1)
		super().mousePressEvent(event)

	def mouseReleaseEvent(self, event):
		print('mouseReleaseEvent')
		super().mousePressEvent(event)

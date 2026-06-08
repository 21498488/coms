from src.instruments.InstrumentTemplate import (
	Status
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

class InstrumentHeaderQt(QWidget):
	def __init__(self, instrument, parent=None):
		super().__init__(parent)

		self.indicator = StatusIndicatorQt(instrument)
		layout = QHBoxLayout(self)
		layout.addWidget(self.indicator)
		layout.addWidget(QLabel(instrument.name))
		layout.addStretch()	

# make sure to call .update() when redraw desired
class StatusIndicatorQt(QWidget):

	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		self.instrument = instrument
		self.setFixedSize(15, 15)

	def paintEvent(self, event):
		painter = QPainter(self)

		match self.instrument.get_status():
			case Status.DISCONNECTED:
				color = QColor(50, 50, 50)
			case Status.INITIALISING:
				color = QColor(255, 255, 0)
			case Status.READY:
				color = QColor(0, 255, 0)
			case Status.BUSY:
				color = QColor(50, 127, 0)
			case Status.ERROR | _:
				color = QColor(255, 0, 0)

		painter.setBrush(color)
		painter.setPen(Qt.black)

		rect = self.rect().adjusted(1, 1, -1, -1)
		painter.drawEllipse(rect)
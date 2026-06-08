from src.instruments.InstrumentTemplate import Status
from src.instrumentsQt.QtWidgets import InstrumentHeaderQt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.instruments.SC210 import SC210
import asyncio

class SC210Qt(SC210):

	def __init__(self, name, address="", database_helper=None):
		self.front_panel = None
		self.settings_tab = None
		self.inputs = []

		#Used to disable GUI elements when program is running
		self.reserved = False

		super().__init__(name, address, database_helper)
		self.create_graphics()

	def disable_gui_inputs(self):
		for widget in self.inputs:
			widget.setDisabled(True)

	def enable_gui_inputs(self):
		for widget in self.inputs:
			widget.setDisabled(False)

	def create_graphics(self):
		self.front_panel = SC210QtFrontPanel(self)
		self.settings_tab = SC210QtSettingsTab(self)

	def set_reserved(self, bool):
		self.reserved = bool
		# Update GUI if required while maintaining status
		self.set_status(self.get_status())

	def set_status(self, status):
		super().set_status(status)
		if self.front_panel is not None:
			self.front_panel.indicator.update()
			self.settings_tab.indicator.update()
			if status == Status.READY and not self.reserved:
				self.enable_gui_inputs()
			else:
				self.disable_gui_inputs()

	# Functions specific to driver

	async def control_position(self, X, Y):
		value = await super().control_position(X, Y)
		pos = self.read_position_X_Y()
		if pos:
			x, y = pos
			self.settings_tab.x_pos.setText(str(x))
			self.settings_tab.y_pos.setText(str(y))
		return value
	
	async def control_position_relative(self, deltaX, deltaY):
		value = await super().control_position_relative(deltaX, deltaY)
		pos = self.read_position_X_Y()
		if pos:
			x, y = pos
			self.settings_tab.x_pos.setText(str(x))
			self.settings_tab.y_pos.setText(str(y))
		return value
	
class SC210QtFrontPanel(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		layout = QVBoxLayout(self)
		self.indicator = InstrumentHeaderQt(instrument)

		param_layout = QGridLayout()
		param_layout.addWidget(QLabel("X Min (µm): "), 0, 0)
		param_layout.addWidget(QLabel(str(instrument.X_MIN)), 0, 1)
		param_layout.addWidget(QLabel("X Max (µm): "), 1, 0)
		param_layout.addWidget(QLabel(str(instrument.X_MAX)), 1, 1)
		param_layout.addWidget(QLabel("Y Min (µm): "), 2, 0)
		param_layout.addWidget(QLabel(str(instrument.Y_MIN)), 2, 1)
		param_layout.addWidget(QLabel("Y Max (µm): "), 3, 0)
		param_layout.addWidget(QLabel(str(instrument.Y_MAX)), 3, 1)

		layout.addWidget(self.indicator)
		layout.addLayout(param_layout)
		layout.addStretch()

class SC210QtSettingsTab(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		self.indicator = InstrumentHeaderQt(instrument)

		manual_control_layout = QGridLayout()

		# Buttons for manual positioning to allign sample
		button_x_neg_small = QPushButton("<")
		button_x_neg_medium = QPushButton("<<")
		button_x_neg_large = QPushButton("<<<")
		manual_control_layout.addWidget(button_x_neg_small, 3, 2)
		manual_control_layout.addWidget(button_x_neg_medium, 3, 1)
		manual_control_layout.addWidget(button_x_neg_large, 3, 0)
		button_x_neg_small.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(-100, 0)))
		button_x_neg_medium.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(-1000, 0)))
		button_x_neg_large.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(-10000, 0)))

		button_x_pos_small = QPushButton(">")
		button_x_pos_medium = QPushButton(">>")
		button_x_pos_large = QPushButton(">>>")
		manual_control_layout.addWidget(button_x_pos_small, 3, 4)
		manual_control_layout.addWidget(button_x_pos_medium, 3, 5)
		manual_control_layout.addWidget(button_x_pos_large, 3, 6)
		button_x_pos_small.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(100, 0)))
		button_x_pos_medium.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(1000, 0)))
		button_x_pos_large.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(10000, 0)))

		button_y_neg_small = QPushButton("v")
		button_y_neg_medium = QPushButton("vv")
		button_y_neg_large = QPushButton("vvv")
		manual_control_layout.addWidget(button_y_neg_small, 4, 3)
		manual_control_layout.addWidget(button_y_neg_medium, 5, 3)
		manual_control_layout.addWidget(button_y_neg_large, 6, 3)
		button_y_neg_small.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, -100)))
		button_y_neg_medium.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, -1000)))
		button_y_neg_large.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, -10000)))

		button_y_pos_small = QPushButton("^")
		button_y_pos_medium = QPushButton("^^")
		button_y_pos_large = QPushButton("^^^")
		manual_control_layout.addWidget(button_y_pos_small, 2, 3)
		manual_control_layout.addWidget(button_y_pos_medium, 1, 3)
		manual_control_layout.addWidget(button_y_pos_large, 0, 3)
		button_y_pos_small.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, 100)))
		button_y_pos_medium.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, 1000)))
		button_y_pos_large.clicked.connect(lambda: asyncio.ensure_future(instrument.control_position_relative(0, 10000)))

		# Display stage positions
		self.x_pos = QLabel(str("Unknown"))
		self.y_pos = QLabel(str("Unknown"))
		manual_control_layout.addWidget(QLabel("X"), 0, 0)
		manual_control_layout.addWidget(QLabel("Y"), 1, 0)
		manual_control_layout.addWidget(self.x_pos, 0, 1)
		manual_control_layout.addWidget(self.y_pos, 1, 1)

		# E-Stop button for emergency stop
		# Not put in inputs as this should never be disabled
		button_e_stop = QPushButton("E-Stop")
		button_e_stop.setStyleSheet("background-color: red")
		button_e_stop.clicked.connect(lambda: instrument.e_stop())

		instrument.inputs =	[button_x_neg_small,
						 button_x_neg_medium,
						 button_x_neg_large,
						 button_x_pos_small,
						 button_x_pos_medium,
						 button_x_pos_large,
						 button_y_neg_small,
						 button_y_neg_medium,
						 button_y_neg_large,
						 button_y_pos_small,
						 button_y_pos_medium,
						 button_y_pos_large]

		if(instrument.get_status() != Status.READY or instrument.reserved):
			instrument.disable_gui_inputs()

		layout = QVBoxLayout(self)
		layout.addWidget(self.indicator)
		layout.addStretch()
		layout.addLayout(manual_control_layout)
		layout.addStretch()
		layout.addWidget(button_e_stop)

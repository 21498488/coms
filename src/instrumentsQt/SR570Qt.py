from src.instruments.InstrumentTemplate import Status
from src.instrumentsQt.QtWidgets import InstrumentHeaderQt
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QVBoxLayout, QWidget

from src.instruments.SR570 import SR570
import asyncio

class SR570Qt(SR570):

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
		self.front_panel = SR570QtFrontPanel(self)
		self.settings_tab = SR570QtSettingsTab(self)

	def set_reserved(self, bool):
		self.reserved = bool
		# Update GUI if required while maintaining status
		self.set_status(self.get_status())
		
	def set_status(self, status):
		super().set_status(status)
		if self.front_panel is not None:
			self.front_panel.indicator.update()
			if status == Status.READY and not self.reserved:
				self.enable_gui_inputs()
			else:
				self.disable_gui_inputs()
		if self.settings_tab is not None:
			self.settings_tab.indicator.update()

	# Functions specific to driver
	
	def set_sensitivity(self, sensitivity):
		value = super().set_sensitivity(sensitivity)
		if value:
			self.front_panel.sensitivity_input.setCurrentIndex(sensitivity)
		return value
	
	async def configure_sensitivity(self, sensitivity):
		value = await self.set_config({"sensitivity": sensitivity})
		if value:
			self.front_panel.sensitivity_input.setCurrentIndex(sensitivity)
		return value

class SR570QtFrontPanel(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		layout = QVBoxLayout(self)
		self.indicator = InstrumentHeaderQt(instrument)

		param_layout = QGridLayout()

		self.sensitivity_input = QComboBox()
		self.sensitivity_input.addItems(instrument.SETTINGS_SENSITIVITY.values())
		self.sensitivity_input.setCurrentIndex(instrument.config["sensitivity"])
		self.sensitivity_input.currentTextChanged.connect(lambda: asyncio.ensure_future(instrument.configure_sensitivity(self.sensitivity_input.currentIndex())))
		param_layout.addWidget(QLabel("Sensitivity"), 0, 0)
		param_layout.addWidget(self.sensitivity_input, 0, 1)

		inputs = [self.sensitivity_input]
		instrument.inputs = instrument.inputs + inputs
		
		if(instrument.get_status() != Status.READY or instrument.reserved):
			instrument.disable_gui_inputs()

		layout.addWidget(self.indicator)
		layout.addLayout(param_layout)
		layout.addStretch()

class SR570QtSettingsTab(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		self.indicator = InstrumentHeaderQt(instrument)

		inputs = []
		instrument.inputs = instrument.inputs + inputs

		if(instrument.get_status() != Status.READY or instrument.reserved):
			instrument.disable_gui_inputs()

		layout = QVBoxLayout(self)
		layout.addWidget(self.indicator)
		layout.addStretch()
		layout.addWidget(QLabel("No functions implemented for this panel"))
		layout.addStretch()

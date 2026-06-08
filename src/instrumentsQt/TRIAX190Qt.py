from src.instruments.InstrumentTemplate import Status
from src.instrumentsQt.QtWidgets import InstrumentHeaderQt
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget
from PySide6.QtGui import QIntValidator

from src.instruments.TRIAX190 import TRIAX190
import asyncio

class TRIAX190Qt(TRIAX190):

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
		self.front_panel = TRIAX190QtFrontPanel(self)
		self.settings_tab = TRIAX190QtSettingsTab(self)

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
	
	async def set_mirror(self, position):
		value = await super().set_mirror(position)
		if value:
			self.front_panel.mirror_input.setCurrentIndex(position)
		return value
	
	async def configure_mirror(self, position):
		value = await self.set_config({"mirror": position})
		if value:
			self.front_panel.mirror_input.setCurrentIndex(position)
		return value

	async def set_slit(self, slit, position):
		value = await super().set_slit(slit, position)
		if value and (slit == 0 or slit == 1):
			self.front_panel.entrance_slit_input.setText(str(position))
		if value and (slit == 2 or slit == 3):
			self.front_panel.exit_slit_input.setText(str(position))
		return value
	
	async def configure_entrance_slit(self, position):
		value = await self.set_config({"entrance slit": position})
		if value:
			self.front_panel.entrance_slit_input.setText(str(position))
		return value

	async def configure_exit_slit(self, position):
		value = await self.set_config({"exit slit": position})
		if value:
			self.front_panel.exit_slit_input.setText(str(position))
		return value

	async def set_wavelength(self, wavelength):
		value = await super().set_wavelength(wavelength)
		if value:
			self.settings_tab.wavelength_input.setText(str(wavelength))
		return value
	
class TRIAX190QtFrontPanel(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		layout = QVBoxLayout(self)
		self.indicator = InstrumentHeaderQt(instrument)

		param_layout = QGridLayout()

		self.exit_slit_input = QLineEdit()
		exit_slit_validator = QIntValidator(instrument.SLIT_MIN,instrument.SLIT_MAX,self.exit_slit_input)
		self.exit_slit_input.setValidator(exit_slit_validator)
		self.exit_slit_input.setText(str(instrument.config["exit slit"]))
		self.exit_slit_input.editingFinished.connect(lambda: asyncio.ensure_future(
			instrument.configure_exit_slit(int(self.exit_slit_input.text()))))
		param_layout.addWidget(QLabel("Exit Slit (0-2000µm)"), 2, 0)
		param_layout.addWidget(self.exit_slit_input, 2, 1)

		self.entrance_slit_input = QLineEdit()
		entrance_slit_validator = QIntValidator(instrument.SLIT_MIN,instrument.SLIT_MAX,self.entrance_slit_input)
		self.entrance_slit_input.setValidator(entrance_slit_validator)
		self.entrance_slit_input.setText(str(instrument.config["entrance slit"]))
		self.entrance_slit_input.editingFinished.connect(lambda: asyncio.ensure_future(
			instrument.configure_entrance_slit(int(self.entrance_slit_input.text()))))
		param_layout.addWidget(QLabel("Entrance Slit (0-2000µm)"), 1, 0)
		param_layout.addWidget(self.entrance_slit_input, 1, 1)

		self.mirror_input = QComboBox()
		self.mirror_input.addItems(instrument.SETTINGS_MIRROR_EXIT.values())
		self.mirror_input.setCurrentIndex(instrument.config["mirror"])
		self.mirror_input.currentTextChanged.connect(lambda: asyncio.ensure_future(
			instrument.configure_mirror(self.mirror_input.currentIndex())))
		param_layout.addWidget(QLabel("Exit Mirror"), 0, 0)
		param_layout.addWidget(self.mirror_input, 0, 1)

		inputs = [self.mirror_input,
			self.entrance_slit_input,
			self.exit_slit_input]
		instrument.inputs = instrument.inputs + inputs

		if(instrument.get_status() != Status.READY or instrument.reserved):
			instrument.disable_gui_inputs()

		layout.addWidget(self.indicator)
		layout.addLayout(param_layout)
		layout.addStretch()

class TRIAX190QtSettingsTab(QWidget):
	
	def __init__(self, instrument, parent=None):
		super().__init__(parent)
		self.indicator = InstrumentHeaderQt(instrument)

		self.wavelength_layout = QHBoxLayout()
		
		self.wavelength_input = QLineEdit()
		wavelength_validator = QIntValidator(instrument.WL_MIN,instrument.WL_MAX,self.wavelength_input)
		self.wavelength_input.setValidator(wavelength_validator)
		self.wavelength_input.setText("0")
		self.wavelength_input.editingFinished.connect(lambda: asyncio.ensure_future(
			instrument.set_wavelength(int(self.wavelength_input.text()))))
		self.wavelength_layout.addWidget(QLabel("Wavelength"))
		self.wavelength_layout.addWidget(self.wavelength_input)

		inputs =	[self.wavelength_input]
		instrument.inputs = instrument.inputs + inputs

		if(instrument.get_status() != Status.READY or instrument.reserved):
			instrument.disable_gui_inputs()

		layout = QVBoxLayout(self)
		layout.addWidget(self.indicator)
		layout.addStretch()
		layout.addLayout(self.wavelength_layout)
		layout.addStretch()

from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPlainTextEdit,
	QPushButton,
	QScrollArea,
	QTabWidget,
	QVBoxLayout,
	QWidget
)
from src.instrumentsQt.QtWidgets import InstrumentHeaderQt
from src.Controller import Controller
from src.instrumentsQt.TRIAX190Qt import TRIAX190Qt
from src.instrumentsQt.SC210Qt import SC210Qt
from src.instrumentsQt.SR830Qt import SR830Qt
from src.instrumentsQt.SR570Qt import SR570Qt
from src.instruments.InstrumentTemplate import Status
from src.RS232Helper import (
	port_by_hwid,
	HUB_PORT_1,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_2,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_3,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_4,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_5,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_6,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_7,  # noqa: F401 <- Disable linter checks for unused import
	HUB_PORT_8  # noqa: F401 <- Disable linter checks for unused import
)

import sys
import asyncio

class ControllerQt(Controller):

	def assign_instruments(self):
		# No device on port 1
		# No device on port 2
		self.translation_stage 	= SC210Qt("Translation Stage",	port_by_hwid(HUB_PORT_3), self.database)
		self.monochromator 		= TRIAX190Qt("Monochromator",	port_by_hwid(HUB_PORT_4), self.database)
		self.preamp_radiometer 	= SR570Qt("Radiometer Pre-Amp",	port_by_hwid(HUB_PORT_5), self.database)
		self.lockin_radiometer	= SR830Qt("Radiometer Lock-In",	port_by_hwid(HUB_PORT_6), self.database)
		self.preamp_detector 	= SR570Qt("Detector Pre-Amp",	port_by_hwid(HUB_PORT_7), self.database)
		self.lockin_detector 	= SR830Qt("Detector Lock-In",	port_by_hwid(HUB_PORT_8), self.database)
		
		self.instruments = [self.translation_stage,
					  self.monochromator,
					  self.preamp_radiometer,
					  self.lockin_radiometer,
					  self.preamp_detector,
					  self.lockin_detector]

	def __init__(self):
		self.front_panel = None
		self.window = None
		self.inputs = []
		super().__init__()
		self.set_reserved(False)
		self.create_graphics()

	def create_graphics(self):
		self.window = ControllerQtWindow(self)
		self.front_panel = MainFrontPanel(self)
		self.window.addPanel(self.front_panel)

		self.set_status_panel()

		for instrument in self.instruments:
			instrument.create_graphics()
			self.window.addPanel(instrument.front_panel)
			if instrument.settings_tab is not None:
				self.window.addTab(instrument.settings_tab, instrument.name)

		self.window.maintab.panels.addStretch()

		return self.window
	
	async def new_job(self):
		# Reserve
		self.set_reserved(True)
		self.reserve_instruments(True)
		self.set_status_panel()

		# Generate tasks
		self.program_generate_tasks()
		self.set_status_panel()
		
		# Run tasks
		await self.program_execute_all_tasks()
		
		# Unreserve
		self.set_reserved(False)
		self.reserve_instruments(False)
		self.set_status_panel()

	async def resume_job(self):
		# Reserve
		self.set_reserved(True)
		self.reserve_instruments(True)
		self.set_status_panel()

		# Run tasks
		await self.program_execute_all_tasks()

		# Unreserve
		self.set_reserved(False)
		self.reserve_instruments(False)
		self.set_status_panel()

	def discard_job(self):
		if self.database is not None:
			self.database.reset_tasks()
		self.reserve_instruments(False)
		self.set_status_panel()
	
	# Add status panel updates
	async def program_execute_task(self, task_id, task_config):
		self.set_status_panel()
		value = await super().program_execute_task(task_id, task_config)
		self.set_status_panel()
		return value

	def e_stop(self):
		print("Controller: E-Stop triggered")
		for instrument in self.instruments:
			instrument.e_stop()
	
	def set_reserved(self, bool):
		self.reserved = bool
		if self.window is not None:
			self.set_status_panel()
		if self.front_panel is not None:
			self.front_panel.update()

	def reserve_instruments(self, bool):
		for instrument in self.instruments:
			instrument.set_reserved(bool)

	# Used just to allow status display in the same way as instruments
	def get_status(self):
		if self.reserved:
			return Status.BUSY
		else:
			return Status.READY
	
	# Call this whenever the top left panel should be updated
	# or when GUI elements need to be enabled/disabled
	def set_status_panel(self):
		tasks_total = self.database.count_tasks()
		tasks_done = tasks_total - self.database.count_undone_tasks()

		self.window.maintab.button_new_job.setDisabled(True)
		self.window.maintab.button_discard_job.setDisabled(True)
		self.window.maintab.button_resume_job.setDisabled(True)

		if tasks_total > 0:
			self.reserve_instruments(True)
			self.window.maintab.status_panel.setText("Job " + self.config["job_name"] + ":\n" + str(tasks_done) + " of " + str(tasks_total) + "\ntasks complete")
			for input in self.front_panel.inputs:
				input.setDisabled(True)
			if not self.reserved:
				self.window.maintab.button_discard_job.setDisabled(False)
				self.window.maintab.button_resume_job.setDisabled(False)
		else:
			self.reserve_instruments(False)
			self.window.maintab.status_panel.setText("No job created")
			if not self.reserved:
				for input in self.front_panel.inputs:
					input.setDisabled(False)
				self.window.maintab.button_new_job.setDisabled(False)

	def set_job_name(self, value):
		print("Controller: Job Name set to " + str(value))
		self.config["job_name"] = value
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.set_status_panel()
		self.front_panel.job_name_input.setText(str(value))

	def set_sample_repeat_count(self, value):
		print("Controller: Sample Repeat Count set to " + str(value))
		self.config["sample_count"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.sample_repeat_count_input.setText(str(value))

	def set_x_start(self, value):
		print("Controller: X Start set to " + str(value))
		self.config["x_start"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.x_start_input.setText(str(value))

	def set_x_step(self, value):
		print("Controller: X Step set to " + str(value))
		self.config["x_step"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.x_step_input.setText(str(value))

	def set_x_end(self, value):
		print("Controller: X End set to " + str(value))
		self.config["x_end"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.x_end_input.setText(str(value))

	def set_y_start(self, value):
		print("Controller: Y Start set to " + str(value))
		self.config["y_start"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.y_start_input.setText(str(value))

	def set_y_step(self, value):
		print("Controller: Y Step set to " + str(value))
		self.config["y_step"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.y_step_input.setText(str(value))

	def set_y_end(self, value):
		print("Controller: Y End set to " + str(value))
		self.config["y_end"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.y_end_input.setText(str(value))

	def set_wl_start(self, value):
		print("Controller: Wavelength Start set to " + str(value))
		self.config["wl_start"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.wl_start_input.setText(str(value))

	def set_wl_step(self, value):
		print("Controller: Wavelength Step set to " + str(value))
		self.config["wl_step"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.wl_step_input.setText(str(value))

	def set_wl_end(self, value):
		print("Controller: Wavelength End set to " + str(value))
		self.config["wl_end"] = int(value)
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		self.front_panel.wl_end_input.setText(str(value))

class ControllerQtWindow(QWidget):

	def __init__(self, controller):
		super().__init__()
		self.setWindowTitle("COMS Controller")
		self.setFixedSize(640, 480) # Target VGA as possibly running on embedded system

		layout = QVBoxLayout(self)
		self.tabs = QTabWidget()

		self.maintab = MainTab(controller)
		self.addTab(self.maintab, "Program Control")
		layout.addWidget(self.tabs)
	
	def addTab(self, tab, name):
		self.tabs.addTab(tab, name)

	def addPanel(self, panel):
		self.maintab.panels.addWidget(panel)

class QtConsole():

	def __init__(self, target):
		self.target = target

	def write(self, text):
		if len(text.strip()) > 0:
			self.target.appendPlainText(text.strip())
			scroll = self.target.verticalScrollBar()
			scroll.setValue(scroll.maximum())
	
	def flush(self):
		pass

class MainTab(QWidget):

	def __init__(self, controller):
		super().__init__()

		# QScrollArea contains QWidget which contains QVBoxLayout
		# Use QScrollArea to bind to parent, modify the layout for the actual panels
		panelScroll = QScrollArea()

		panelScroll.setFixedSize(400, 300)

		# Scroll area will not look correct without this set
		panelScroll.setWidgetResizable(True)

		panelScrollWidget = QWidget()
		self.panels = QVBoxLayout(panelScrollWidget)
		panelScroll.setWidget(panelScrollWidget)

		buttons = QVBoxLayout()
		self.button_new_job = QPushButton("Run new Job")
		self.button_discard_job = QPushButton("Discard current Job")
		self.button_discard_job.setStyleSheet("background-color: orange")
		self.button_resume_job = QPushButton("Resume current Job")
		self.button_e_stop = QPushButton("E-Stop")
		self.button_e_stop.setStyleSheet("background-color: red")
		
		self.button_new_job.clicked.connect(lambda: asyncio.ensure_future(controller.new_job()))
		self.button_discard_job.clicked.connect(lambda: controller.discard_job())
		self.button_resume_job.clicked.connect(lambda: asyncio.ensure_future(controller.resume_job()))
		self.button_e_stop.clicked.connect(lambda: controller.e_stop())

		self.status_panel = QLabel("Default\nStatus\nText")
		self.status_panel.setWordWrap(True)
		self.status_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)

		buttons.addStretch()
		buttons.addWidget(self.status_panel)
		buttons.addStretch()
		buttons.addWidget(self.button_new_job)
		buttons.addWidget(self.button_resume_job)
		buttons.addWidget(self.button_discard_job)
		buttons.addStretch()
		buttons.addWidget(self.button_e_stop)

		console = QPlainTextEdit()
		console.setReadOnly(True)
		console.setFixedSize(595, 100)

		sys.stdout = QtConsole(console)
		sys.stderr = QtConsole(console)

		innerLayout = QHBoxLayout()
		innerLayout.addLayout(buttons)
		innerLayout.addWidget(panelScroll)

		layout = QVBoxLayout(self)
		layout.addLayout(innerLayout)
		layout.addWidget(console)

class MainFrontPanel(QWidget):
	
	def __init__(self, controller, parent=None):
		super().__init__(parent)
		layout = QVBoxLayout(self)
		self.indicator = InstrumentHeaderQt(controller)

		param_layout = QGridLayout()

		# job_name
		self.job_name_input = QLineEdit()
		self.job_name_input.setText((str(controller.config["job_name"])))
		self.job_name_input.editingFinished.connect(lambda: controller.set_job_name(self.job_name_input.text()))
		param_layout.addWidget(QLabel("Job Name"), 0, 0)
		param_layout.addWidget(self.job_name_input, 0, 1)

		# sample_repeat_count
		self.sample_repeat_count_input = QLineEdit()
		sample_repeat_count_validator = QIntValidator(1,999,self.sample_repeat_count_input)
		self.sample_repeat_count_input.setValidator(sample_repeat_count_validator)
		self.sample_repeat_count_input.setText((str(controller.config["sample_count"])))
		self.sample_repeat_count_input.editingFinished.connect(lambda: controller.set_sample_repeat_count(self.sample_repeat_count_input.text()))
		param_layout.addWidget(QLabel("Sample Repeat Count"), 1, 0)
		param_layout.addWidget(self.sample_repeat_count_input, 1, 1)

		sweep_layout = QGridLayout()
		
		sweep_layout.addWidget(QLabel("Start"), 0, 1)
		sweep_layout.addWidget(QLabel("Step"), 0, 2)
		sweep_layout.addWidget(QLabel("End"), 0, 3)

		sweep_layout.addWidget(QLabel("X (µm)"), 1, 0)
		sweep_layout.addWidget(QLabel("Y (µm)"), 2, 0)
		sweep_layout.addWidget(QLabel("λ (nm)"), 3, 0)

		# X_Start
		self.x_start_input = QLineEdit()
		x_start_validator = QIntValidator(-30590,617,self.x_start_input)
		self.x_start_input.setValidator(x_start_validator)
		self.x_start_input.setText((str(controller.config["x_start"])))
		self.x_start_input.editingFinished.connect(lambda: controller.set_x_start(self.x_start_input.text()))
		sweep_layout.addWidget(self.x_start_input, 1, 1)
		
		# X_Step
		self.x_step_input = QLineEdit()
		x_step_validator = QIntValidator(-999999,999999,self.x_step_input)
		self.x_step_input.setValidator(x_step_validator)
		self.x_step_input.setText((str(controller.config["x_step"])))
		self.x_step_input.editingFinished.connect(lambda: controller.set_x_step(self.x_step_input.text()))
		sweep_layout.addWidget(self.x_step_input, 1, 2)

		# X_End
		self.x_end_input = QLineEdit()
		x_end_validator = QIntValidator(-30590,617,self.x_end_input)
		self.x_end_input.setValidator(x_end_validator)
		self.x_end_input.setText((str(controller.config["x_end"])))
		self.x_end_input.editingFinished.connect(lambda: controller.set_x_end(self.x_end_input.text()))
		sweep_layout.addWidget(self.x_end_input, 1, 3)

		# y_Start
		self.y_start_input = QLineEdit()
		y_start_validator = QIntValidator(-1101,30122,self.y_start_input)
		self.y_start_input.setValidator(y_start_validator)
		self.y_start_input.setText((str(controller.config["y_start"])))
		self.y_start_input.editingFinished.connect(lambda: controller.set_y_start(self.y_start_input.text()))
		sweep_layout.addWidget(self.y_start_input, 2, 1)
		
		# y_Step
		self.y_step_input = QLineEdit()
		y_step_validator = QIntValidator(-999999,999999,self.y_step_input)
		self.y_step_input.setValidator(y_step_validator)
		self.y_step_input.setText((str(controller.config["y_step"])))
		self.y_step_input.editingFinished.connect(lambda: controller.set_y_step(self.y_step_input.text()))
		sweep_layout.addWidget(self.y_step_input, 2, 2)

		# y_End
		self.y_end_input = QLineEdit()
		y_end_validator = QIntValidator(-1101,30122,self.y_end_input)
		self.y_end_input.setValidator(y_end_validator)
		self.y_end_input.setText((str(controller.config["y_end"])))
		self.y_end_input.editingFinished.connect(lambda: controller.set_y_end(self.y_end_input.text()))
		sweep_layout.addWidget(self.y_end_input, 2, 3)

		# wl_Start
		self.wl_start_input = QLineEdit()
		wl_start_validator = QIntValidator(0,2600,self.wl_start_input)
		self.wl_start_input.setValidator(wl_start_validator)
		self.wl_start_input.setText((str(controller.config["wl_start"])))
		self.wl_start_input.editingFinished.connect(lambda: controller.set_wl_start(self.wl_start_input.text()))
		sweep_layout.addWidget(self.wl_start_input, 3, 1)
		
		# wl_Step
		self.wl_step_input = QLineEdit()
		wl_step_validator = QIntValidator(-999999,999999,self.wl_step_input)
		self.wl_step_input.setValidator(wl_step_validator)
		self.wl_step_input.setText((str(controller.config["wl_step"])))
		self.wl_step_input.editingFinished.connect(lambda: controller.set_wl_step(self.wl_step_input.text()))
		sweep_layout.addWidget(self.wl_step_input, 3, 2)

		# wl_End
		self.wl_end_input = QLineEdit()
		wl_end_validator = QIntValidator(0,2600,self.wl_end_input)
		self.wl_end_input.setValidator(wl_end_validator)
		self.wl_end_input.setText((str(controller.config["wl_end"])))
		self.wl_end_input.editingFinished.connect(lambda: controller.set_wl_end(self.wl_end_input.text()))
		sweep_layout.addWidget(self.wl_end_input, 3, 3)

		self.inputs = [self.job_name_input,
				 		self.sample_repeat_count_input,
						self.x_start_input,
						self.x_step_input,
						self.x_end_input,
						self.y_start_input,
						self.y_step_input,
						self.y_end_input,
						self.wl_start_input,
						self.wl_step_input,
						self.wl_end_input]

		layout.addWidget(self.indicator)
		layout.addLayout(param_layout)
		layout.addLayout(sweep_layout)
		layout.addStretch()
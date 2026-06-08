from src.instruments.TRIAX190 import TRIAX190
from src.instruments.SC210 import SC210
from src.instruments.SR830 import SR830
from src.instruments.SR570 import SR570
from src.instruments.InstrumentTemplate import Status
from src.DatabaseHelper import DatabaseHelper
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

import asyncio
import datetime
import re

class Controller:

	# Number of time constants to use when sampling lock-in data
	# 3 or 5 are standard choices, depending on accuracy desired
	TIME_CONSTANTS = 3

	# Maximum permittable failed attempts when attempting a task before aborting the program
	MAX_ERRORS = 3

	def __init__(self, database_name="database/coms.db"):
		# Recommended to create a new database for any significant changes to the system
		# to prevent loading older incompatible configs
		self.name = "Controller"

		self.database = DatabaseHelper(database_name)

		if port_by_hwid(HUB_PORT_1) is None:
			raise Exception("CRITICAL ERROR - Could not find Serial HUB device.")

		self.assign_instruments()
		
		# Default config
		self.config = {
			"x_start": -15000,
			"x_step": 10000,
			"x_end": 0,
			"y_start": 15000,
			"y_step": 10000,
			"y_end": 30000,
			"wl_start": 400,
			"wl_step": 100,
			"wl_end": 800,
			"sample_count": 1,
			"job_name": "Default Job"
		}

		# Either overwrite the default config,
		# or set the default config into the database
		stored_config = self.database.get_config(self.name)
		if stored_config is not None:
			self.config = stored_config
		else:
			self.database.set_config(self.name, self.config)

	# Use this function to determine what instruments the controller uses,
	# how they are initialised and the order that they display in the GUI
	def assign_instruments(self):
		# No device on port 1
		# No device on port 2
		self.translation_stage 	= SC210("Translation Stage",	port_by_hwid(HUB_PORT_3), self.database)
		self.monochromator 		= TRIAX190("Monochromator",		port_by_hwid(HUB_PORT_4), self.database)
		self.preamp_radiometer 	= SR570("Radiometer Pre-Amp",	port_by_hwid(HUB_PORT_5), self.database)
		self.lockin_radiometer	= SR830("Radiometer Lock-In",	port_by_hwid(HUB_PORT_6), self.database)
		self.preamp_detector 	= SR570("Detector Pre-Amp",		port_by_hwid(HUB_PORT_7), self.database)
		self.lockin_detector 	= SR830("Detector Lock-In",		port_by_hwid(HUB_PORT_8), self.database)

		# Order here determines order iterated through e.g. for GUI tab construction
		self.instruments = [self.translationStage, self.monochromator, 
					  self.preamp_detector, self.preamp_radiometer,
					  self.lockin_detector, self.lockin_radiometer]
		
	async def start_event_loop(self):
		for instrument in self.instruments:
			asyncio.ensure_future(instrument.start_event_loop())

	async def start_event_loop_and_run(self):
		await self.start_event_loop()
		await self.program_run()

	async def program_run(self):
		if self.database.count_tasks() == 0:
			self.program_generate_tasks()
		return await self.program_execute_all_tasks()

	def program_generate_tasks(self):
		print("Controller: Generating Tasks")
		self.database.reset_tasks()
		data = []

		# Adjustment added to turn [Inclusive, exclusive] behaviour into [Inclusive, inclusive] behaviour
		def adjustment(x):
			if x > 0:
				return 1
			else:
				return -1

		for x in range(self.config["x_start"], self.config["x_end"] + adjustment(self.config["x_step"]), self.config["x_step"]):
			for y in range(self.config["y_start"], self.config["y_end"] + adjustment(self.config["y_step"]), self.config["y_step"]):
				for wl in range(self.config["wl_start"], self.config["wl_end"] + adjustment(self.config["wl_step"]), self.config["wl_step"]):
					# Used to obtain multiple samples for averaging purposes
					for i in range(self.config["sample_count"]):
						data.append({
							"x": x,
							"y": y,
							"wl": wl,
							"count": i
						})

		self.database.add_tasks(data)
		return True

	async def program_execute_all_tasks(self):
		print("Controller: Executing all tasks")

		if self.database.count_tasks() == 0:
			print("Controller: No tasks found in database for controller to execute")
			return False

		while(self.database.count_undone_tasks() > 0):
			task_id, task_config = self.database.get_next_undone_task()
			
			errors = 0
			result = await self.program_execute_task(task_id, task_config)
			while result is False and errors < self.MAX_ERRORS:
				errors += 1
				result = await self.program_execute_task(task_id, task_config)

			if result is False:
				print("Controller: Controller was unable to complete task with id " + str(task_id))
				print("Controller: Please address instrument errors before resuming execution")
				return False
		
		# Output header
		output_header = ("x,y,wavelength_target,wavelength,r_radiometer,r_detector")

		# Regex for filtering filenames to prevent errors
		regex = re.compile("[^a-zA-Z0-9 ]")

		# File output
		filename = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + " " + re.sub(regex, "", self.config["job_name"])
		filepath = "outputs/" + filename
		with open(filepath, "a", encoding='utf-8') as file:
			file.write("Job: " + self.config["job_name"] + "\n")
			file.write("\n")
			file.write("<Configuration>\n")
			for instrument in self.instruments:
				file.write(instrument.str_config() + "\n\n")
			file.write("\n")
			file.write("<Data>\n")
			file.write(output_header + "\n")
			self.database.write_outputs_to_file(file)
		print("Controller: Output written to file " + filepath)

		self.database.reset_tasks()
		return True

	async def program_execute_task(self, task_id, task_config):	

		print("Controller: Executing task " + str(task_id))

		for instrument in self.instruments:
			status = instrument.get_status()
			while status != Status.READY:
				# Allow a chance for any pending initialisiations to begin
				await asyncio.sleep(0.01)
				if status == Status.ERROR:
					print("Controller: Unable to execute task - " + instrument.name + " is errored")
					return False
				elif status == Status.DISCONNECTED:
					# TODO: Implement device re-initialisation
					print("Controller: Unable to execute task - " + instrument.name + " is disconnected")
					return False
				else:
					# Initialising or completing an async task, wait
					await asyncio.sleep(0.1)
					status = instrument.get_status()
		
		if await self.translation_stage.control_position(task_config["x"], task_config["y"]) is False:
			print(self.name + ": Failed to set control_position for " + self.lockin_radiometer.name)
			return False
		
		if await self.monochromator.set_wavelength(task_config["wl"]) is False:
			print(self.name + ": Failed to set wavelength for " + self.lockin_radiometer.name)
			return False

		# allow lock ins to acquire accurate data by waiting a multiple of the largest time constant
		wait = self.TIME_CONSTANTS * max(self.lockin_radiometer.SETTINGS_TIME_CONSTANT[self.lockin_radiometer.config["time constant"]],
								   self.lockin_detector.SETTINGS_TIME_CONSTANT[self.lockin_detector.config["time constant"]])
		
		print("Controller: Waiting for " + str(round(wait, 2)) + " seconds")

		await asyncio.sleep(wait)

		r_radiometer = self.lockin_radiometer.get_R_value()
		if r_radiometer is False:
			print(self.name + ": Failed to obtain data from " + self.lockin_radiometer.name)
			return False

		r_detector = self.lockin_detector.get_R_value()
		if r_detector is False:
			print(self.name + ": Failed to obtain data from " + self.lockin_detector.name)
			return False
	
		wavelength_set = self.monochromator.get_wavelength()	
		if wavelength_set is False:
			print(self.name + ": Failed to obtain data from " + self.monochromator.name)
			return False		
		
		# If any devices errored, reject the data
		# e.g. if an e-stop prevented a control command from properly resolving
		for instrument in self.instruments:
			if instrument.get_status() == Status.ERROR:
				print(self.name + ": Rejecting data as " + instrument.name + " is errored")
				return False

		output = ",".join([str(task_config["x"]),
					 str(task_config["y"]),
					 str(task_config["wl"]),
					 str(wavelength_set),
					 str(r_radiometer),
					 str(r_detector)])

		self.database.set_output(task_id, output)

		return True
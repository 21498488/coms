from src.instruments.InstrumentTemplate import (
	InstrumentTemplate,
	Status
)
import asyncio

class TRIAX190(InstrumentTemplate):

	# nm
	WL_MIN = 0
	WL_MAX = 2600

	SETTINGS_MIRROR_EXIT = {
		0: "FRONT/AXIAL",
		1: "LATERAL/SIDE"
	}

	SLITS = [0, 1, 2, 3]

 	# µm
	SLIT_MIN = 0
	SLIT_MAX = 2000

	SLIT_STEPS_PER_MM = 500

	def __init__(self, name, address="", database_helper=None):
		super().__init__(name, address, database_helper)
		
		# Device Identification
		self.set_status(Status.DISCONNECTED)
		self.name = name
		self.model = "TRIAX190"

		# Configuration management and storage
		if self.config is None:
			self.config = {
				"mirror": 0,
				"entrance slit": 1000,
				"exit slit": 1000
			}
		self.database = database_helper

		# Serial Settings
		# TRIAX190 has autobauding, previous system used 19200 so maintain
		self.address = address
		self.baud = 19200
		self.bytesize = 8
		self.stopbits = 1
		self.prefix = ""
		# Usually \r, but some commands break if you send it, so manually enter with command
		self.terminator = ""
		self.timeout = 0.3

	async def initialise(self):
		# if autobauding, may need to attempt multiple times
		status = self.command(" ", force=True)

		errors = 0
		while not status and errors < 5:
			errors += 1
			await asyncio.sleep(1)
			status = self.command(" ", force=True)

		if not status:
			return False
		
		if status[0] == "*":
			# Auto-baud just completed, no init
			self.command(b'\xf7', size=1, force=True, raw_bytes=True)
			status = self.command(" ", size=1, force=True)

		if status == "B":
			# In boot program
			self.command("O2000\0", read=False, force=True)
			await asyncio.sleep(0.5)
			# Clear response after 500ms
			self.command("", write=False, size=1, force=True)
			status = self.command(" ", force=True)

		if status != "F":
			print(self.name + " was unable to enter the main program. Try restarting the device")
			return False
		
		print(self.name + ": was able to enter main program")

		# Motor init for auto-calibration
		self.command("A", read=False, force=True)
		await asyncio.sleep(100)
		if self.command("", write=False, size=1, force=True) != "o":
			return False
				
		# Command for motor speed setting
		if self.command("B0,1000,4000,250\r", size=1, force=True) != "o":
			return False
		
		# Open shutter
		if self.command("W0\r", size=1, force=True) != "o":
			return False
		
		return True

	async def set_config(self, config):
		no_errors = True
		for key in config.keys():
			match key:
				case "mirror":
					if not await self.set_mirror(config[key]):
						print(self.name + ": Error setting config for key - " + key)
						no_errors = False
					else:
						self.config[key] = config[key]
				case "entrance slit":
					if not await self.set_slit(0, config[key]):
						print(self.name + ": Error setting config for key - " + key)
						no_errors = False
					else:
						self.config[key] = config[key]
				case "exit slit":
					res1 = await self.set_slit(2, config[key])
					res2 = await self.set_slit(3, config[key])
					if not res1 or not res2:
						print(self.name + ": Error setting config for key - " + key)
						no_errors = False
					else:
						self.config[key] = config[key]
				case _:
					print(self.name + ": Error loading config for unsupported key - " + key)
					no_errors = False
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		return no_errors

	def str_config(self):
		return "\n".join([self.name,
					self.model,
					"Exit Mirror: " + str(self.SETTINGS_MIRROR_EXIT[self.config["mirror"]]),
					"Entrance Slit: " + str(self.config["entrance slit"]) + "µm",
					"Exit Slit: " + str(self.config["exit slit"]) + "µm"
					])

	def e_stop(self):
		self.command("L", size=1, force=True)
		self.set_status(Status.ERROR)
		return
	
	async def set_wavelength(self, wavelength):
		if not self.check_motor_stopped():
			return False
		if wavelength < self.WL_MIN or wavelength > self.WL_MAX:
			return False
		if self.command("Z61,1," + str(wavelength) + "\r", size=1) != "o":
			return False
		while not self.check_motor_stopped():
			#Do not allow interrupts while sleeping
			self.set_status(Status.BUSY)
			await asyncio.sleep(0.5)
			# Reset to READY, but only if not set to error
			if self.get_status() == Status.BUSY:
				self.set_status(Status.READY)
			else:
				return False
		if abs(float(self.get_wavelength()) - wavelength) > 2:
			print(self.name + ": Potential motor stall, wavelength significantly different from set point")
			return False
		return True
	
	async def set_mirror(self, position):
		if not self.check_acc_stopped():
			return False
		if position in self.SETTINGS_MIRROR_EXIT.keys():
			match position:
				case 0:
					if self.command("f0\r", size=1) != "o":
						return False
				case 1:
					if self.command("e0\r", size=1) != "o":
						return False
				case _:
					return False
		while not self.check_acc_stopped():
			#Do not allow interrupts while sleeping
			self.set_status(Status.BUSY)
			# 15 second expected response time, so long sleeps
			await asyncio.sleep(1)
			# Reset to READY, but only if not set to error
			if self.get_status() == Status.BUSY:
				self.set_status(Status.READY)
			else:
				return False
		return True

	async def set_slit(self, slit, position):
		if not self.check_motor_stopped():
			return False
		if slit not in self.SLITS:
			return False
		if position < self.SLIT_MIN or position > self.SLIT_MAX:
			return False
		print("pos" + str(position))
		current_steps = self.command("j0," + str(slit) + "\r", until="\r")
		print("cur", str(current_steps))
		if not current_steps:
			return False
		delta_steps = int((position/1000) * self.SLIT_STEPS_PER_MM) - int(current_steps[1:])
		print("del", str(delta_steps))
		if self.command("k0," + str(slit) + "," + str(delta_steps) + "\r", size=1) != "o":
			return False
		while not self.check_motor_stopped():
			#Do not allow interrupts while sleeping
			self.set_status(Status.BUSY)
			await asyncio.sleep(0.5)
			# Reset to READY, but only if not set to error
			if self.get_status() == Status.BUSY:
				self.set_status(Status.READY)
			else:
				return False
		return True
	
	def get_wavelength(self):
		value = self.command("Z62,1\r", until="\r")
		if value:
			return value.strip()[1:]
		else:
			return value
	
	def check_acc_stopped(self):
		return self.command("l", size=2) == "oz"
	
	def check_motor_stopped(self):
		return self.command("E", size=2) == "oz"

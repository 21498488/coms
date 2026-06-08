from src.instruments.InstrumentTemplate import (
	InstrumentTemplate,
	Status
)
import asyncio

class SC210(InstrumentTemplate):

	# Axis 2
	# "- Left/ + Right" from sample holder
	X_MIN = -30590
	X_MAX = 617

	# Axis 1
	# "- Out / + In" from sample holder
	Y_MIN = -1101 #um
	Y_MAX = 30122 #30mm, so units of um

	def __init__(self, name, address="", database_helper=None):
		super().__init__(name, address, database_helper)

		# Device Identification
		self.set_status(Status.DISCONNECTED)
		self.name = name
		self.model = "SC210"

		# Configuration management and storage
		# No config required for SC210
		if self.config is None:
			self.config = {}
		self.database = database_helper

		# Serial Settings
		# SC-210 spec is 9600 8/N/1
		self.address = address
		self.baud = 9600
		self.bytesize = 8
		self.stopbits = 1
		self.prefix = chr(2)
		self.terminator = "\r\n"
		self.timeout = 0.2

	# Check that connected device behaves like a SC-210
	async def initialise(self):
		return (self.command("RDP1/0", force=True)[0] == "C")

	async def set_config(self, config):
		for key in config.keys():
			match key:
				case _:
					print(self.name + ": Error loading config for unsupported key - " + key)
					return False
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		return True

	def str_config(self):
		return "\n".join([self.name,
					self.model])

	def e_stop(self):
		self.command("STP0/1", force=True)
		self.set_status(Status.ERROR)

	# Set default mode as until CRLF
	# For read commands, return data as a split list
	def command(self, command, write=True, read=True, force=False, until="\r\n", size=None, raw_bytes=False):
		if not read:
			return super().command(command, write, read, force, until, size, raw_bytes)
		else:
			data = super().command(command, write, read, force, until, size, raw_bytes)
			if data:
				return data.strip().split("\t")
			else:
				return [False]

	# Returns before operation completed to allow e-stop to occur
	# Use check_stopped to determine if complete
	async def control_position(self, X, Y):
		if not self.check_stopped():
			return False
		if X < self.X_MIN or X > self.X_MAX:
			return False
		if Y < self.Y_MIN or Y > self.Y_MAX:
			return False
		if self.command("MPS1/" + str(Y) + "/2/" + str(X) + "/1")[0] != "C":
			return False
		while not self.check_stopped():
			#Do not allow interrupts while sleeping
			self.set_status(Status.BUSY)
			await asyncio.sleep(0.5)
			# Reset to READY, but only if not set to error
			if self.get_status() == Status.BUSY:
				self.set_status(Status.READY)
			else:
				return False
		x, y = self.read_position_X_Y()
		if X != x or Y != y:
			return False
		return True

	async def control_position_relative(self, deltaX, deltaY):
		if not self.check_stopped():
			return False
		current_position = self.read_position_X_Y()
		if not current_position:
			return False
		x, y = current_position
		# Clamp between MIN and MAX
		x_new = max(self.X_MIN, min(self.X_MAX, x + deltaX))
		y_new = max(self.Y_MIN, min(self.Y_MAX, y + deltaY))
		return await self.control_position(x_new, y_new)
		
	def read_position_X_Y(self):
		x_axis_data = self.command("RDP2/0")
		y_axis_data = self.command("RDP1/0")
		if x_axis_data[0] != "C" or y_axis_data[0] != "C":
			return False
		return (int(x_axis_data[2]), int(y_axis_data[2]))

	def check_stopped(self):
		axis_1_data = self.command("STR1/1")
		axis_2_data = self.command("STR1/2")
		if axis_1_data[0] != "C" or axis_2_data[0] != "C":
			return False
		if axis_1_data[3] == "0" and axis_2_data[3] == "0":
			return True
		else:
			return False
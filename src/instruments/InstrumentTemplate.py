from enum import Enum
import serial

class Status(Enum):
	DISCONNECTED = 0	# Device can be initialised
	INITIALISING = 1	# Device is being initialised
	READY = 2			# Device operational
	BUSY = 3			# Device operational but busy
	ERROR = 4			# Instrument requires manual intervention and should not be used

class InstrumentTemplate:

	# Default settings unless overwritten
	def __init__(self, name="Name not set", address="", database_helper=None):
		# Device Identification
		self.set_status(Status.DISCONNECTED)
		self.name = name
		self.model = "Model Not Set"

		# Configuration management and storage
		self.config = None
		self.database = database_helper

		# Serial Settings
		self.address = address
		self.baud = 9600
		self.bytesize = 8
		self.stopbits = 1
		self.prefix = ""
		self.terminator = ""
		self.timeout = 0.2

		# Override default config if one exists in database
		if self.database is not None:
			database_config = self.database.get_config(self.name)
			if database_config is not None:
				self.config = database_config

	# Called when the controller event loop begins
	# Attempts to initialise the driver
	async def start_event_loop(self):
		if self.get_status() != Status.DISCONNECTED:
			return False
		self.set_status(Status.INITIALISING)
		try:
			self.connection = serial.Serial(self.address, baudrate=self.baud, bytesize=self.bytesize, 
								   stopbits=self.stopbits, timeout=self.timeout)
			self.connection.flushInput()
			self.connection.flushOutput()
		except Exception:
			print(self.name + ": Unable to connect to port " + self.address)
			self.set_status(Status.ERROR)
			return False

		# Run driver-specific code for initialising
		if not await self.initialise():
			print(self.name + ": Could not initialise")
			self.set_status(Status.ERROR)
			return False

		self.set_status(Status.READY)

		# Apply config from database, or use the default config otheriwse
		await self.set_config(self.config)
		
		return True

	# General template for sending serial commands
	# Reading without specifying until or size is not advised
	def command(self, command, write=True, read=True, force=False, until=None, size=None, raw_bytes=False):
		if self.get_status() == Status.READY:
			self.set_status(Status.BUSY)
		elif force:
			pass
		else:
			return False
		try:
			if write:
				if raw_bytes:
					encoded = command
				else:
					encoded = (self.prefix + command + self.terminator).encode("ASCII")
				self.connection.write(encoded)
			if read:
				if until is not None:
					if not raw_bytes:
						data = self.connection.read_until(expected=until).decode("ASCII") 
						if until not in data:
							raise Exception("Serial read timed out while waiting for data terminator")
					else:
						data = self.connection.read_until(expected=until)
				elif size is not None:
					if not raw_bytes:
						data = self.connection.read(size=size).decode("ASCII")
						if len(data) != size:
							raise Exception("Serial read timed out while waiting for specific data length")
					else:
						data = self.connection.read(size=size)
				else:
					if not raw_bytes:
						data = self.connection.read(size=1024).decode("ASCII")
					else:
						data = self.connection.read(size=1024)
			else:
				data = True
			if self.get_status() == Status.BUSY:
				self.set_status(Status.READY)
			return data
		except Exception as error:
			print(error)
			print(self.name + ": ERROR - Failed to send command - " + command)
			self.set_status(Status.ERROR)
			return False

	def initialise(self) -> bool:
		self.set_status(Status.ERROR)
		raise NotImplementedError("initialise not implemented for " + self.name + " " + self.model)

	async def set_config(self, config: dict) -> bool:
		self.set_status(Status.ERROR)
		raise NotImplementedError("set_config not implemented for " + self.name + " " + self.model)

	def get_config(self) -> dict:
		return self.config
	
	def str_config(self) -> str:
		return "\n".join([self.name,
					self.model,
					str(self.config)])
		
	def set_status(self, status: Status) -> bool:
		self.status = status
		return True

	def get_status(self) -> Status:
		return self.status

	def e_stop(self) -> None:
		self.set_status(Status.ERROR)
		raise NotImplementedError("e_stop not implemented for " + self.name + " " + self.model)
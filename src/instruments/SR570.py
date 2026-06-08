from src.instruments.InstrumentTemplate import (
	InstrumentTemplate,
	Status
)

class SR570(InstrumentTemplate):

	SETTINGS_SENSITIVITY = {
		0: "1 pA/V",
		1: "2 pA/V",
		2: "5 pA/V",
		3: "10 pA/V",
		4: "20 pA/V",
		5: "50 pA/V",
		6: "100 pA/V",
		7: "200 pA/V",
		8: "500 pA/V",
		9: "1 nA/V",
		10: "2 nA/V",
		11: "5 nA/V",
		12: "10 nA/V",
		13: "20 nA/V",
		14: "50 nA/V",
		15: "100 nA/V",
		16: "200 nA/V",
		17: "500 nA/V",
		18: "1 μA/V",
		19: "2 μA/V",
		20: "5 μA/V",
		21: "10 μA/V",
		22: "20 μA/V",
		23: "50 μA/V",
		24: "100 μA/V",
		25: "200 μA/V",
		26: "500 μA/V",
		27: "1 mA/V"
	}

	def __init__(self, name, address="", database_helper=None):
		super().__init__(name, address, database_helper)

		# Device Identification
		self.set_status(Status.DISCONNECTED)
		self.name = name
		self.model = "SR570"

		# Configuration management and storage
		if self.config is None:
			self.config = {
				"sensitivity": 13
			}
		self.database = database_helper

		# Serial Settings
		# SR570 spec is 9600 8/N/2
		self.address = address
		self.baud = 9600
		self.bytesize = 8
		self.stopbits = 2
		self.prefix = ""
		self.terminator = "\r\n"
		self.timeout = 0.2

	# Write-only device with no init required
	async def initialise(self):
		return True

	async def set_config(self, config):
		no_errors = True
		for key in config.keys():
			match key:
				case "sensitivity":
					if not self.set_sensitivity(config[key]):
						print(self.name + ": Error setting config for key - " + str(key))
						no_errors = False
					else:
						self.config[key] = config[key]
				case _:
					print(self.name + ": Error loading config for unsupported key - " + str(key))
					no_errors = False
		if self.database is not None:
			self.database.set_config(self.name, self.config)
		return no_errors

	def str_config(self):
		return "\n".join([self.name,
					self.model,
					"Sensitivity: " + str(self.SETTINGS_SENSITIVITY[self.config["sensitivity"]])
					])

	def e_stop(self):
		self.set_status(Status.ERROR)
		return
	
	# Write-only device
	def command(self, command, write=True, read=False, force=False, until=None, size=None, raw_bytes=False):
		return super().command(command, write, read, force, until, size, raw_bytes)
	
	def set_sensitivity(self, sensitivity):
		if sensitivity in self.SETTINGS_SENSITIVITY.keys():
			return self.command("SENS " + str(sensitivity))
		print(self.name + ": Invalid Sensitivity " + str(sensitivity))
		return False
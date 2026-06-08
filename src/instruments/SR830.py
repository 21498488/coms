from src.instruments.InstrumentTemplate import (
	InstrumentTemplate,
	Status
)

class SR830(InstrumentTemplate):

	SETTINGS_SENSITIVITY = {
		0: "2 nV/fA",
		1: "5 nV/fA",
		2: "10 nV/fA",
		3: "20 nV/fA",
		4: "50 nV/fA",
		5: "100 nV/fA",
		6: "200 nV/fA",
		7: "500 nV/fA",
		8: "1 μV/pA",
		9: "2 μV/pA",
		10: "5 μV/pA",
		11: "10 μV/pA",
		12: "20 μV/pA",
		13: "50 μV/pA",
		14: "100 μV/pA",
		15: "200 μV/pA",
		16: "500 μV/pA",
		17: "1 mV/nA",
		18: "2 mV/nA",
		19: "5 mV/nA",
		20: "10 mV/nA",
		21: "20 mV/nA",
		22: "50 mV/nA",
		23: "100 mV/nA",
		24: "200 mV/nA",
		25: "500 mV/nA",
		26: "1 V/μA"
	}

	# Settings 14 and above not valid
	# for harmonic ref frequency > 200 Hz
	SETTINGS_TIME_CONSTANT = {
		0: 0.00001,
		1: 0.00003,
		2: 0.0001,
		3: 0.0003,
		4: 0.001,
		5: 0.003,
		6: 0.01,
		7: 0.03,
		8: 0.1,
		9: 0.3,
		10: 1,
		11: 3,
		12: 10,
		13: 30#,
		#14: 100,
		#15: 300,
		#16: 1000,
		#17: 3000,
		#18: 10000,
		#19: 30000
	}

	SETTINGS_SLOPE = {
		0: "6 dB/oct",
		1: "12 dB/oct",
		2: "18 dB/oct",
		3: "24 dB/oct"
	}

	def __init__(self, name, address="", database_helper=None):
		super().__init__(name, address, database_helper)

		# Device Identification
		self.set_status(Status.DISCONNECTED)
		self.name = name
		self.model = "SR830"

		# Configuration management and storage
		if self.config is None:
			self.config = {
				"sensitivity": 23,
				"time constant": 9,
				"slope": 1
			}
		self.database = database_helper

		# Serial Settings
		# SR830 spec is programmable
		# Manually set to be consistent with SR570 i.e. 9600 8/N/2
		self.address = address
		self.baud = 9600
		self.bytesize = 8
		self.stopbits = 2
		self.prefix = ""
		self.terminator = "\n"
		self.timeout = 0.2

	async def initialise(self):
		ident = self.command("*IDN?", force=True)
		if not ident:
			print(self.name + ": Could not confirm is SR830 device")
			return False
		if "SR830" not in ident:
			print(self.name + ": Could not confirm is SR830 device")
			return False
		return self.command("OUTX0", force=True)

	async def set_config(self, config):
		no_errors = True
		for key in config.keys():
			match key:
				case "sensitivity":
					if not self.set_sensitivity(config[key]):
						print(self.name + ": Error setting config for key - " + key)
						no_errors = False
					else:
						self.config[key] = config[key]
				case "time constant":
					if not self.set_time_constant(config[key]):
						print(self.name + ": Error setting config for key - " + key)
						no_errors = False
					else:
						self.config[key] = config[key]
				case "slope":
					if not self.set_slope(config[key]):
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
					"Sensitivity: " + str(self.SETTINGS_SENSITIVITY[self.config["sensitivity"]]),
					"Time Constant: " + str(self.SETTINGS_TIME_CONSTANT[self.config["time constant"]]),
					"Slope: " + str(self.SETTINGS_SLOPE[self.config["slope"]])
					])
	
	def e_stop(self):
		self.set_status(Status.ERROR)
		return
	
	# CR terminates responses
	# Auto-determine read mode by presence of ? in the command
	def command(self, command, write=True, read=True, force=False, until="\r", size=None, raw_bytes=False):
		if "?" in command:
			return super().command(command, write, True, force, until, size, raw_bytes)
		else:
			return super().command(command, write, False, force, until, size, raw_bytes)

	def get_X_Y_R_Theta_values(self):
		string = self.command("SNAP?1,2,3,4")
		if string:
			return tuple(string.strip().split(","))
		else:
			return string
	
	# return R value in volts, as ASCII string e.g. "-1.3020"
	def get_R_value(self):
		value = self.command("OUTP?3")
		if value:
			return value.strip()
		else:
			return value
	
	def set_sensitivity(self, sensitivity):
		if sensitivity in self.SETTINGS_SENSITIVITY.keys():
			return self.command("SENS " + str(sensitivity))
		print(self.name + ": Invalid Sensitivity " + str(sensitivity))
		return False

	def get_sensitivity(self):
		value = self.command("SENS?")
		if value:
			return value.strip()
		else:
			return value
	
	def set_time_constant(self, time_constant):
		if time_constant in self.SETTINGS_TIME_CONSTANT.keys():
			return self.command("OFLT" + str(time_constant))
		print(self.name + ": Invalid Time Constant " + str(time_constant))
		return False

	def get_time_constant(self):
		value = self.command("OFLT?")
		if value:
			return value.strip()
		else:
			return value

	def set_slope(self, slope):
		if slope in self.SETTINGS_SLOPE.keys():
			return self.command("OFSL" + str(slope))
		print(self.name + ": Invalid slope " + str(slope))
		return False
	
	def get_slope(self):
		value = self.command("OFSL?")
		if value:
			return value.strip()
		else:
			return value
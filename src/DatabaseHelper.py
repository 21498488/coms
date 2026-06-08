import sqlite3
import json

class DatabaseHelper:

	def __init__(self, filename="database/debug.db"):
		self.database = sqlite3.connect(filename)
		self.cursor = self.database.cursor()
		self.initialise_tables()

	def initialise_tables(self) -> None:
		#SQlite automatically makes INTEGER PRIMARY KEYs autoincrementing
		self.cursor.execute(
			"""CREATE TABLE IF NOT EXISTS tasks (
				id INTEGER PRIMARY KEY,
				sweep_json TEXT,
				output TEXT
			);"""
		)
		self.cursor.execute(
			"""CREATE TABLE IF NOT EXISTS configs (
				name TEXT PRIMARY KEY,
				config_json TEXT
			);"""
		)
		self.database.commit()

	def reset_tables(self) -> None:
		self.cursor.execute("DROP TABLE IF EXISTS tasks;")
		self.cursor.execute("DROP TABLE IF EXISTS configs;")
		self.database.commit()

	def add_tasks(self, data_list) -> None:
		self.cursor.executemany(
			"""INSERT INTO tasks(sweep_json)
				VALUES (?);""", ((json.dumps(data),) for data in data_list))
		self.database.commit()

	def get_next_undone_task(self) -> tuple:
		self.cursor.execute(
			"""SELECT * FROM tasks
				WHERE output IS NULL
				LIMIT 1;""")
		self.database.commit()
		row = self.cursor.fetchone()
		if row is None:
			return None
		else:
			taskId, config, _ = row
			return (taskId, json.loads(config))
		
	def count_tasks(self) -> int:
		self.cursor.execute(
			"""SELECT COUNT(*) FROM tasks;""")
		self.database.commit()
		n, = self.cursor.fetchone()
		return n

	def count_undone_tasks(self) -> int:
		self.cursor.execute(
			"""SELECT COUNT(*) FROM tasks
			WHERE output IS NULL;""")
		self.database.commit()
		n, = self.cursor.fetchone()
		return n

	def set_output(self, id, data) -> None:
		self.cursor.execute(
			"""UPDATE tasks
			SET output = ?
			WHERE id = ?;""", (data, id))
		self.database.commit()

	def reset_tasks(self) -> None:
		self.cursor.execute(
			"""DELETE FROM tasks;"""
		)
		self.database.commit()
	
	def get_config(self, deviceName) -> dict:
		self.cursor.execute(
			"""SELECT * FROM configs
				WHERE name = ?;""", (deviceName,))
		self.database.commit()
		row = self.cursor.fetchone()
		if row is None:
			return None
		else:
			_, config = row
			return json.loads(config)

	def set_config(self, deviceName, config) -> None:
		self.cursor.execute(
			"""REPLACE INTO configs
				VALUES (?, ?);""", (deviceName, json.dumps(config)))
		self.database.commit()
	
	def write_outputs_to_file(self, file) -> None:
		self.cursor.execute(
			"""SELECT output FROM tasks;""")
		self.database.commit()
		row = self.cursor.fetchone()
		while row is not None:
			output, = row
			file.write(output + "\n")
			row = self.cursor.fetchone()
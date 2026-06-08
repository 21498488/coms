from src.Controller import Controller
from src.ControllerQt import ControllerQt

from PySide6.QtWidgets import QApplication
import PySide6.QtAsyncio as QtAsyncio

import sys
import argparse
import asyncio

def main() -> int:
	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-g", "--graphical", help="Run the controller with a GUI", action='store_true')
	group.add_argument("-c", "--cli", help="Run the controller without a GUI, resuming prior job or using prior settings for a new job", action='store_true')

	args = parser.parse_args()

	if(not (args.graphical or args.cli)):
		parser.print_help()
		return -1

	if(args.graphical):
		app = QApplication()
		app.setStyle("Fusion")
		control = ControllerQt()
		control.window.show()
		QtAsyncio.run(control.start_event_loop())

	if(args.cli):
		control = Controller()
		asyncio.run(control.start_event_loop_and_run())

	return -1

if __name__ == '__main__':
	sys.exit(main())


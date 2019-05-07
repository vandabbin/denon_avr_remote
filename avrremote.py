#!/usr/bin/env python3.7
# BarryTheButcher Copyright (C) 2019
# Licensed under GPL version 3

import argparse, sys, socket, re
from time import sleep

# Default IP
# ex.
# default_ip = "192.168.0.100"
default_ip = ""
# Default Port
default_port = "23"

# AV Control Class
class AVRController:
	# Initialize AVControl Object
	def __init__(self, args):
		self.address = args.address
		self.port = args.port
		self.command = args.command
		self.val = args.val
		#self.prefixes = ['PW', 'MV', 'MU', 'SI']

	def validateIP(self): # Text for valid IPv4 Address
		a = self.address.split('.')
		if len(a) != 4:
			return False
		for x in a:
			if not x.isdigit():
				return False
			i = int(x)
			if i < 0 or i > 255:
				return False
		return True

	def validate_connection_info(self, interactive=False):
		if self.address == "":
			print("IP Address is not set")
			if interactive:
				self.address = input("Enter IP Address: ")
				return self.validate_connection_info(True)
		elif self.port == "":
			print("Port is not set")
			if interactive:
				self.port = input("Enter Port: ")
				return self.validate_connection_info(True)
		elif not self.validateIP():
			print("IP Address is invalid")
			if interactive:
				self.address = input("Enter IP Address: ")
				return self.validate_connection_info(True)
		elif not self.port.isdigit():
			print("Port is invalid")
			if interactive:
				self.port = input("Enter Port: ")
				return self.validate_connection_info(True)
		else: return True

		return False

	def connect(self): 
		# Initialize Socket Stream
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		try:
			# Connect Socket Stream
			s.connect((self.address, int(self.port)))
			return (True, s)
		except Exception as e:
			print(e)

		return (False, None)

	def disconnect(self, s):
		try:
			# Close Socket Stream
			s.shutdown(socket.SHUT_RDWR)
			s.close()
			return True
		except Exception as e:
			print(e)

		return False

	def send_command(self, command, s, receive_only=False):
		try:
			if not receive_only: # Send Command and Receive response
				resp=''
				# Send command until response prefix is the same as command prefix
				# unless response is MVMAX which is always the wrong response in this
				# scenario.
				# I would like to handle the responses from the Receiver better
				# however I don't know enough about the receiver's communications
				# to implement a better method. If someone else does please let me
				# know!!
				while resp[:2] != command[:2] or resp[:5] == "MVMAX":
					# Send Command through Socket Stream
					s.send(command.encode("utf-8"))
					resp = str(s.recv(64), 'utf-8')
				return resp
			# Receive response without sending command
			return str(s.recv(64), 'utf-8')
		except Exception as e:
			print(e)

		return "error"
	
	def execute_power_command(self, command, status_cmd, s):
		# Send status command and receive response
		resp = self.send_command(status_cmd, s)
		if command != "status" and command != resp:
			# Handle Toggle Command
			if command == "toggle":
				if resp == "PWSTANDBY\r":
					command = "PWON\r"
				elif resp == "PWON\r":
					command = "PWSTANDBY\r"
			# Send Command
			self.send_command(command, s)
			# Receive status response
			resp = self.send_command(status_cmd, s)
		return resp
			
	def execute_volume_command(self, command, status_cmd, s):
		# Send status command and receive response
		resp = self.send_command(status_cmd, s)
		# Receive second status response containing max volume
		maxVolume = self.send_command(None, s, True) 
		if command != "status":
			power_state = self.send_command("PW?\r", s) # Recieve Power State
			if power_state == "PWON\r": # Send command if power state is on 
				if command != resp: # and command is not equal to response
					resp = self.send_command(command, s)
			else: resp = power_state # Power state is STANDBY so return w/o sending command
		return resp

	def execute_mute_command(self, command, status_cmd, s):
		# Send status command and receive response
		resp = self.send_command(status_cmd, s)
		if command != "status":
			power_state = self.send_command("PW?\r", s) # Recieve Power State
			if power_state == "PWON\r": # Send command if power state is on
				if resp == "MUON\r": # Mute is on
					resp = self.send_command("MUOFF\r", s) # Toggle it off
				elif resp == "MUOFF\r": # Mute is off
					resp = self.send_command("MUON\r", s) # Toggle it on
			else: resp = "PWSTANDBY\r" # Power state is STANDBY w/o sending command
		return resp

	def execute_source_command(self, command, status_cmd, s):
		# Send status command and receive response
		resp = self.send_command(status_cmd, s)
		if command != "status":
			power_state = self.send_command("PW?\r", s) # Receive Power State
			if power_state == "PWON\r": # Send command if power state is on
				if command != resp: # and command is not equal to response
					resp = self.send_command(command, s)
			else: resp = "PWSTANDBY\r" # Power state is STANDBY w/o sending command
		return resp
					
	def execute_command(self, command, s): # Send command w/o processing (for testing)
		return self.send_command(command, s)
	
	def parse_command(self, s):
		# Parse Power Commands
		if self.command == "power":
			msg = "Power State:"
			status_cmd = "PW?\r"
			if self.val == "status": cmd = self.val
			elif self.val == "toggle": cmd = self.val
			elif self.val == "on": cmd = "PWON\r"
			elif self.val == "off": cmd = "PWSTANDBY\r"
			resp = self.execute_power_command(cmd, status_cmd, s)
		# Parse Volume Commands
		elif self.command == "volume":
			msg = "Volume Level:"
			status_cmd = "MV?\r"
			if self.val == "status": cmd = self.val
			elif self.val == "up": cmd = "MVUP\r"
			elif self.val == "down": cmd = "MVDOWN\r"
			else:
				self.val = int(self.val)
				cmd = "MV%02d\r" % self.val
			resp = self.execute_volume_command(cmd, status_cmd, s)
		# Parse Mute Commands ( A bit different because of the toggle )
		elif self.command == "mute":
			msg = "Mute State:"
			status_cmd = "MU?\r"
			if self.val == "status": cmd = self.val
			else: cmd = "mute_toggle"
			resp = self.execute_mute_command(cmd, status_cmd, s)
		# Parse Source Commands
		elif self.command == "source":
			msg = "Source Input:"
			status_cmd = "SI?\r"
			if self.val == "status": cmd = self.val
			elif self.val == "bluetooth": cmd = "SIBT\r"
			elif self.val == "tuner": cmd = "SITUNER\r"
			elif self.val == "aux": cmd = "SIAUX1\r"
			elif self.val == "iradio": cmd = "SIIRADIO\r"
			elif self.val == "mplayer": cmd = "SIMPLAY\r"
			elif self.val == "game": cmd = "SIGAME\r"
			elif self.val == "dvd": cmd = "SIDVD\r"
			elif self.val == "bluray": cmd = "SIBD\r"
			elif self.val == "favorites": cmd = "SIFAVORITES\r"
			elif self.val == "sirius": cmd = "SISIRUIUSXM\r"
			elif self.val == "pandora": cmd = "SIPANDORA\r"
			elif self.val == "ipod": cmd = "SIUSB/IPOD\r"
			resp = self.execute_source_command(cmd, status_cmd, s)
		# Parse Custom Commands
		elif self.command == "command":
			msg=""
			cmd = "%s\r" % self.val
			resp = self.execute_command(cmd, s)

		return (resp, msg)

	# Formate message and response for output to stdout
	def parse_response(self, resp, msg): 
		resp = resp.rstrip()
		resp = resp[2:]
		if self.command == "volume":
			if len(resp) == 3:
				resp = "%s.%s" % (resp[:2], resp[2:])
		elif self.command == "source":
			if resp == "BT": resp = "Bluetooth"
			elif resp == "TUNER": resp = "Tuner"
			elif resp == "AUX1": resp = "Aux"
			elif resp == "IRADIO": resp = "Internet Radio"
			elif resp == "MPLAY": resp = "Media Player"
			elif resp == "GAME": resp = "Game"
			elif resp == "DVD": resp = "DVD"
			elif resp == "BD": resp = "BluRay"
			elif resp == "FAVORITES": resp = "Favorites"
			elif resp == "SIRIUSXM": resp = "Sirius XM"
			elif resp == "PANDORA": resp = "Pandora"
			elif resp == "USB/IPOD": resp = "iPod"
		return "%s %s" % (msg, resp)

	def run(self):
		# Check if IP Address is valid and Port is set
		valid = False
		try:
			if sys.stdin.isatty():
				while not valid:
					valid = self.validate_connection_info(True)
			else:
				valid = self.validate_connection_info()
		except KeyboardInterrupt:
			print('')

		if valid:
			print("Denon AVR Remote")
			# Connect to Receiver
			connected,sock = self.connect()
			if not connected:
				print("There was a problem connecting to the receiver.")
			else:
				# Parse and Execute Command
				resp,msg = self.parse_command(sock)
				disconnected = self.disconnect(sock) # Disconnect from receiver
				# Print message and parsed response
				print("[%s] %s" % (self.address, self.parse_response(resp, msg)))

# Set Default Subparser
def set_default_subparser(self, name, args=None):
	"""
	default subparser selection. Call after setup, just before parse_args()
	name: is the name of the subparser to call by default
	args: if set is the argument list handed to parse_args()
	
	, tested with 2.7, 3.2, 3.3, 3.4, 3.6
	it works with 2.6 assuming argparse is installed
	"""
	subparser_found = False
	existing_default = False # check if default parser previously defined
	for arg in sys.argv[1:]:
		if arg in ['-h', '--help']:  # global help if no subparser
			break
		if arg in ['-v', '--version']: # version if no subparser
			break
	else:
		for x in self._subparsers._actions:
			if not isinstance(x, argparse._SubParsersAction):
				continue
			for sp_name in x._name_parser_map.keys():
				if sp_name in sys.argv[1:]:
					subparser_found = True
				if sp_name == name: # check existance of default parser
					existing_default = True
		if not subparser_found:
		# If the default subparser is not among the existing ones,
		# create a new parser.
		# As this is called just before 'parse_args', the default
		# parser created here will not pollute the help output.
	
			if not existing_default:
				for x in self._subparsers._actions:
					if not isinstance(x, argparse._SubParsersAction):
						continue
					x.add_parser(name)
					break # this works OK, but should I check further?
	
			# insert default in first position, this implies no
			# global options without a sub_parsers specified
			if args is None:
				sys.argv.insert(1, name)
			else:
				args.insert(0, name)

# Start Of Program
# Set up ArgParser
argparse.ArgumentParser.set_default_subparser = set_default_subparser
parser = argparse.ArgumentParser(prog="avremote", description='Denon AVR Remote', add_help=False)
parser.add_argument('--help', '-h', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')
parser.add_argument('--version', '-v', action='version', version='%(prog)s v0.1beta BarryTheButcher Copyright \xa9 2019')
parser.add_argument('--address', '-a', action='store', dest='address', default=default_ip, help='IP Address of the AVR to connect to.')
parser.add_argument('--port', '-p', action='store', dest='port', default=default_port, help='Port to connect on')
subparser = parser.add_subparsers(dest='command')
subparser_cmd = subparser.add_parser('power')
subparser_cmd.add_argument('val', action='store', default='status', const='status', nargs='?', choices=['status', 'on', 'off', 'toggle'])
subparser_cmd = subparser.add_parser('volume')
volume_choices = list(range(91))
x=0
while x < len(volume_choices):
	volume_choices[x] = str(volume_choices[x])
	x += 1
volume_choices.insert(0, 'down')
volume_choices.insert(0, 'up')
volume_choices.insert(0, 'status')
subparser_cmd.add_argument('val', action='store', default='status', const='status', nargs='?', choices=volume_choices, metavar='status, up, down, [0-90]')
subparser_cmd = subparser.add_parser('mute')
subparser_cmd.add_argument('val', action='store', default='toggle', const='toggle', nargs='?', choices=['status', 'toggle'])
subparser_cmd = subparser.add_parser('source')
subparser_cmd.add_argument('val', action='store', default='status', const='status', nargs='?', choices=['status', 'bluetooth', 'tuner', 'aux', 'iradio', 'mplayer', 'game', 'dvd', 'bluray', 'favorites', 'siriusxm', 'pandora', 'ipod'])
subparser_cmd = subparser.add_parser('command')
subparser_cmd.add_argument('val', action='store', nargs='?')
parser.set_default_subparser('power') # Set Power as the default Subparser
args = parser.parse_args()

if args.command is None or args.val is None:
	print('Error Parsing Arguments')
	exit(1)

controller = AVRController(args)
# Run Controller
controller.run()

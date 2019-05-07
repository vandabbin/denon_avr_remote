#!/usr/bin/env python3
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

# AVR Control Class
class AVRController:
	# Initialize AVControl Object
	def __init__(self, args):
		self.address = args.address
		self.port = args.port
		self.cmd = args.cmd
		self.val = args.val

		# Command Dictionaries
		self.prefixes = {'power': 'PW',
				'volume': 'MV',
				'mute': 'MU',
				'source': 'SI'}

		self.commands = {'status': 'status',
				'toggle': 'toggle',
				'on': 'PWON\r',
				'off': 'PWSTANDBY\r',
				'up': 'MVUP\r',
				'down': 'MVDOWN\r',
				'mute on': 'MUON\r',
				'mute off': 'MUOFF\r',
				'bluetooth': 'SIBT\r',
				'tuner': 'SITUNER\r',
				'aux': 'SIAUX1\r',
				'iradio': 'SIIRADIO\r',
				'mplayer': 'SIMPLAY\r',
				'game': 'SIGAME\r',
				'dvd': 'SIDVD\r',
				'bluray': 'SIBD\r',
				'favorites': 'SIFAVORITES\r',
				'sirius': 'SISIRIUSXM\r',
				'pandora': 'SIPANDORA\r',
				'ipod': 'SIUSB/IPOD'}

		self.status_cmds = {'power': 'PW?\r',
				'volume': 'MV?\r',
				'mute': 'MU?\r',
				'source': 'SI?\r'}

		# Source Input Names Dictionary
		self.src_names = {'BT': 'Bluetooth',
				'Tuner': 'Tuner',
				'AUX1': 'Aux',
				'IRADIO': 'Internet Radio',
				'MPLAY': 'Media Player',
				'GAME': 'Game',
				'DVD': 'DVD',
				'BD': 'BluRay',
				'FAVORITES': 'Favorites',
				'SIRIUSXM': 'Sirius XM',
				'USB/IPOD': 'iPod'}

	def validateIP(self): # Test for valid IPv4 Address
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

	def send_command(self, s, cmd, receive_only=False):
		try:
			if not receive_only: # Send Command and Receive response
				"""
				Send command until response prefix is the same as command prefix
				unless response is MVMAX which is always the wrong response in this
				scenario.
				I would like to handle the responses from the Receiver better
				however I don't know enough about the receiver's communications
				to implement a better method. If someone else does please let me
				know!!
				"""
				resp=''
				while resp[:2] != cmd[:2] or resp[:5] == "MVMAX":
					# Send Command through Socket Stream
					s.send(cmd.encode("utf-8"))
					resp = str(s.recv(64), 'utf-8')
				return resp
			# Receive response without sending command
			return str(s.recv(64), 'utf-8')
		except Exception as e:
			print(e)

		return "error"
	
	def execute_power_command(self, s, cmd, status_cmd):
		# Send status command and receive response
		resp = self.send_command(s, status_cmd)

		if cmd != "status" and cmd != resp:
			# Handle Toggle Command
			if cmd == "toggle":
				if resp == self.commands['off']:
					cmd = self.commands['on']
				else: cmd = self.commands['off']
			# Send Command
			self.send_command(s, cmd)
			# Receive status response
			return self.send_command(s, status_cmd)

		return resp
			
	def execute_volume_command(self, s, cmd, status_cmd):
		# Send status command and receive response
		resp = self.send_command(s, status_cmd)
		# Receive second status response containing max volume
		maxVolume = self.send_command(s, None, True) 

		if cmd != "status":
			power_state = self.send_command(s, self.status_cmds['power']) # Recieve Power State
			if power_state == self.commands['on']: # Send command if power state is on 
				if cmd != resp: # and command is not equal to response
					return self.send_command(s, cmd)
			else: resp = power_state # Power state is STANDBY so return w/o sending command

		return resp

	def execute_mute_command(self, s, cmd, status_cmd):
		# Send status command and receive response
		resp = self.send_command(s, status_cmd)

		if cmd != "status":
			power_state = self.send_command(s, self.status_cmds['power']) # Recieve Power State
			if power_state == self.commands['on']: # Send command if power state is on
				if resp == self.commands['mute on']: # Mute is on
					return self.send_command(s, self.commands['mute off']) # Toggle it off
				else: return self.send_command(s, self.commands['mute on']) # Toggle it on
			else: resp = power_state # Power state is STANDBY so return w/o sending command

		return resp

	def execute_source_command(self, s, cmd, status_cmd):
		# Send status command and receive response
		resp = self.send_command(s, status_cmd)

		if cmd != "status":
			power_state = self.send_command(s, self.status_cmds['power']) # Receive Power State
			if power_state == self.commands['on']: # Send command if power state is on
				if cmd != resp: # and command is not equal to response
					return self.send_command(s, cmd)
			else: resp = power_state # Power state is STANDBY so return w/o sending command

		return resp
					
	def execute_command(self, s, cmd): # Send command w/o processing (for testing)
		return self.send_command(s, cmd)
	
	def parse_command(self, s):
		# Parse Power Commands
		if self.cmd == "power":
			return (self.execute_power_command(s, self.commands[self.val], self.status_cmds[self.cmd]), "Power State:")

		# Parse Volume Commands
		elif self.cmd == "volume":
			if self.val in self.commands:
				cmd = self.commands[self.val]
			else:
				self.val = int(self.val)
				cmd = "%s%02d\r" % (self.prefixes[self.cmd], self.val)
			return (self.execute_volume_command(s, cmd, self.status_cmds[self.cmd]), "Volume Level:")

		# Parse Mute Commands
		elif self.cmd == "mute":
			return (self.execute_mute_command(s, self.commands[self.val], self.status_cmds[self.cmd]), "Mute State:")

		# Parse Source Commands
		elif self.cmd == "source":
			return (self.execute_source_command(s, self.commands[self.val], self.status_cmds[self.cmd]), "Sourcce Input:")
		# Parse Custom Commands
		elif self.cmd == "command":
			return (self.execute_command("%s\r" % self.val, s), "")

	# Formate message and response for output to stdout
	def parse_response(self, resp, msg): 
		resp = resp[2:].rstrip()
		if self.cmd == "volume":
			if len(resp) == 3:
				resp = "%s.%s" % (resp[:2], resp[2:])
		elif self.cmd == "source":
			if resp in self.src_names:
				resp = self.src_names[resp]
		if resp == "STANDBY":
			msg = "Power State:"
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
				# Print message with parsed response
				print("[%s] %s" % (self.address, self.parse_response(resp, msg)))

# Set Default Subparser
def set_default_subparser(self, name, args=None):
	"""
	default subparser selection. Call after setup, just before parse_args()
	name: is the name of the subparser to call by default
	args: if set is the argument list handed to parse_args()
	
	, tested with 2.7, 3.2, 3.3, 3.4, 3.6, 3.7
	it works with 2.6 assuming argparse is installed
	"""
	subparser_found = False
	for arg in sys.argv[1:]:
		if arg in ['-h', '--help']:  # global help if no subparser
			break
		if arg in ['-v', '--version']: # version if no subparser
			break
		if arg in ['-a', '--address']: # address requires subparser to be specified
			break
		if arg in ['-p', '--port']: # port requires subparser to be specified
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
			# insert default in first position, this implies no
			# global options without a sub_parsers specified
			if args is None:
				sys.argv.insert(1, name)
			else:
				args.insert(0, name)

# Start Of Program
# Set up ArgParser
argparse.ArgumentParser.set_default_subparser = set_default_subparser
parser = argparse.ArgumentParser(prog="avremote",
				description='Denon AVR Remote',
				add_help=False)
parser.add_argument('--help',
			'-h',
			action='help',
			default=argparse.SUPPRESS,
			help='Show this help message and exit.')

parser.add_argument('--version',
			'-v',
			action='version',
			version='%(prog)s v0.1beta BarryTheButcher Copyright \xa9 2019')

parser.add_argument('--address',
			'-a',
			action='store',
			dest='address',
			default=default_ip,
			help='IP Address of the AVR to connect to.')

parser.add_argument('--port',
			'-p',
			action='store',
			dest='port',
			default=default_port,
			help='Port to connect on')

subparser = parser.add_subparsers(dest='cmd')
subparser_cmd = subparser.add_parser('power')
subparser_cmd.add_argument('val',
			action='store',
			default='status',
			const='status',
			nargs='?',
			choices=['status',
				'on',
				'off',
				'toggle'])

subparser_cmd = subparser.add_parser('volume')
volume_choices = list(range(91))

x=0
while x < len(volume_choices):
	volume_choices[x] = str(volume_choices[x])
	x += 1

volume_choices.insert(0, 'down')
volume_choices.insert(0, 'up')
volume_choices.insert(0, 'status')

subparser_cmd.add_argument('val',
			action='store',
			default='status',
			const='status',
			nargs='?',
			choices=volume_choices,
			metavar='status, up, down, [0-90]')

subparser_cmd = subparser.add_parser('mute')
subparser_cmd.add_argument('val',
			action='store',
			default='toggle',
			const='toggle',
			nargs='?',
			choices=['status',
				'toggle'])

subparser_cmd = subparser.add_parser('source')
subparser_cmd.add_argument('val',
			action='store',
			default='status',
			const='status',
			nargs='?',
			choices=['status',
				'bluetooth',
				'tuner',
				'aux',
				'iradio',
				'mplayer',
				'game',
				'dvd',
				'bluray',
				'favorites',
				'siriusxm',
				'pandora',
				'ipod'])

subparser_cmd = subparser.add_parser('command')
subparser_cmd.add_argument('val',
			action='store',
			nargs='?')

parser.set_default_subparser('power') # Set Power as the default Subparser
args = parser.parse_args()

if args.cmd is None or args.val is None:
	print('Error Parsing Arguments')
	exit(1)

controller = AVRController(args)
# Run Controller
controller.run()

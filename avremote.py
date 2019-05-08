#!/usr/bin/env python3
# Denon AVR Remote for CLI
# BarryTheButcher Copyright (C) 2019
# Licensed under GPL version 3

import sys
import socket
import argparse
from time import sleep

# Default IP
# ex.
# default_ip = '192.168.0.100'
default_ip = ''
# Default Port
default_port = '23'


# AVR Control Class
class AVRController:

    def __init__(self, args):
        """
        Initialize AVRController Object
        args: is a Namespace object containing the following attributes
            address: is the IPv4 address of the AVR
            port: is the port to communicate on.
            cmd: is the type of command to perform
            val: is the command action to be performed.
        """
        self.ADDRESS = args.address
        self.PORT = args.port
        self.CMD = args.cmd
        self.VAL = args.val

        # Command Dictionaries
        self.PREFIXES = {'power': 'PW',
                         'volume': 'MV',
                         'mute': 'MU',
                         'source': 'SI'}

        self.COMMANDS = {'status': 'status',
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

        self.STATUS_CMDS = {'power': 'PW?\r',
                            'volume': 'MV?\r',
                            'mute': 'MU?\r',
                            'source': 'SI?\r'}

        # Source Input Names Dictionary
        self.SRC_NAMES = {'BT': 'Bluetooth',
                          'TUNER': 'Tuner',
                          'AUX1': 'Aux',
                          'IRADIO': 'Internet Radio',
                          'MPLAY': 'Media Player',
                          'GAME': 'Game',
                          'DVD': 'DVD',
                          'BD': 'BluRay',
                          'FAVORITES': 'Favorites',
                          'SIRIUSXM': 'Sirius XM',
                          'USB/IPOD': 'iPod'}

    def validate_ip(self):
        """
        Test if self.ADDRESS is a valid IPv4 address
        and return True/False.
        """
        a = self.ADDRESS.split('.')
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
        """
        Test that necessary connection data is present and
        return True/False. If it isn't and script is being
        run interactively, then ask for it.
        interactive: if set then script is being run interactively.
        """
        if self.ADDRESS == '':
            print('IP Address is not set')
            if interactive:
                self.ADDRESS = input('Enter IP Address: ')
                return self.validate_connection_info(True)
        elif self.PORT == '':
            print('Port is not set')
            if interactive:
                self.PORT = input('Enter Port: ')
                return self.validate_connection_info(True)
        elif not self.validate_ip():
            print('IP Address is invalid')
            if interactive:
                self.ADDRESS = input('Enter IP Address: ')
                return self.validate_connection_info(True)
        elif not self.PORT.isdigit():
            print('Port is invalid')
            if interactive:
                self.PORT = input('Enter Port: ')
                return self.validate_connection_info(True)
        else:
            return True
        return False

    def connect(self):
        """
        Create a socket connection and try to connect to it.
        Return a tuple containing the connection result and
        socket object.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((self.ADDRESS, int(self.PORT)))
        except Exception as e:
            print(e)
        else:
            return (True, sock)
        return (False, None)

    def disconnect(self, sock):
        """
        Shutdown and close socket connection then return True/False.
        """
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except Exception as e:
            print(e)
        else:
            return True
        return False

    def send_command(self, sock, cmd):
        """
        Try to send command via socket and return True/False.
        """
        try:
            sock.send(cmd.encode('utf-8'))
        except Exception as e:
            print(e)
        else:
            return True
        return False

    def receive_status(self, sock, cmd, receive_only=False):
        """
        Try to send a status command and return the response.
        """
        resp=''
        try:
            if not receive_only:
                while resp[:2] != cmd[:2] or resp[:5] == 'MVMAX':
                    sock.send(cmd.encode('utf-8'))
                    resp = str(sock.recv(16), 'utf-8')
            else:
                resp = str(sock.recv(16), 'utf-8')
        except Exception as e:
            print(e)
        else:
            return resp
        return 'Error'

    def send_power_command(self, sock, cmd, status_cmd):
        """
        Send a power command and return the response.
        """
        resp = self.receive_status(sock, status_cmd)
        if cmd != 'status' and cmd != resp:
            if cmd == 'toggle': # Handle Toggle Command
                if resp == self.COMMANDS['off']:
                    cmd = self.COMMANDS['on']
                else:
                    cmd = self.COMMANDS['off']
            if self.send_command(sock, cmd): # Send Command
                return self.receive_status(sock, status_cmd)
            else:
                return 'Error'
        return resp

    def send_volume_command(self, sock, cmd, status_cmd):
        """
        Send a volume command and return the response.
        """
        resp = self.receive_status(sock, status_cmd)
        maxVolume = self.receive_status(sock, None, True)
        if cmd != 'status' or resp == 'Error':
            power_state = self.receive_status(sock, self.STATUS_CMDS['power'])
            if power_state == self.COMMANDS['on']:
                if cmd != resp:
                    if self.send_command(sock, cmd):
                        return self.receive_status(sock, status_cmd)
                    else:
                        return 'Error'
            else:
                resp = power_state
        return resp

    def send_mute_command(self, sock, cmd, status_cmd):
        """
        Send a mute command and return the response.
        """
        resp = self.receive_status(sock, status_cmd)
        if cmd != 'status' or resp == 'Error':
            power_state = self.receive_status(sock, self.STATUS_CMDS['power'])
            if power_state == self.COMMANDS['on']:
                if resp == self.COMMANDS['mute on']:
                    cmd = 'mute off'
                else:
                    cmd = 'mute on'
                if self.send_command(sock, self.COMMANDS[cmd]):
                    return self.receive_status(sock, status_cmd)
                else:
                    return 'Error'
            else:
                resp = power_state
        return resp

    def send_source_command(self, sock, cmd, status_cmd):
        """
        Send a source command and return the response.
        """
        resp = self.receive_status(sock, status_cmd)
        if cmd != 'status' or resp == 'Error':
            power_state = self.receive_status(sock, self.STATUS_CMDS['power'])
            if power_state == self.COMMANDS['on']:
                if cmd != resp:
                    if self.send_command(sock, cmd):
                        return self.receive_status(sock, status_cmd)
                    else:
                        return 'Error'
            else:
                resp = power_state
        return resp

    def parse_command(self, sock):
        """
        Parse self.CMD and send command.
        Returns a tuple of message label and response.
        """
        # Parse Power Commands
        if self.CMD == 'power':
            return ('Power State:',
                    self.send_power_command(
                        sock,
                        self.COMMANDS[self.VAL],
                        self.STATUS_CMDS[self.CMD]))

        # Parse Volume Commands
        elif self.CMD == 'volume':
            if self.VAL in self.COMMANDS:
                cmd = self.COMMANDS[self.VAL]
            else:
                self.VAL = int(self.VAL)
                cmd = '%s%02d\r' % (self.PREFIXES[self.CMD], self.VAL)
            return ('Volume Level:',
                    self.send_volume_command(
                        sock,
                        cmd,
                        self.STATUS_CMDS[self.CMD]))

        # Parse Mute Commands
        elif self.CMD == 'mute':
            return ('Mute State:',
                    self.send_mute_command(
                        sock,
                        self.COMMANDS[self.VAL],
                        self.STATUS_CMDS[self.CMD]))

        # Parse Source Commands
        elif self.CMD == 'source':
            return ('Source Input:',
                    self.send_source_command(
                        sock,
                        self.COMMANDS[self.VAL],
                        self.STATUS_CMDS[self.CMD]))

    def parse_response(self, resp, msg):
        """
        Format message label and response for output to stdout
        and return string.
        """
        if resp == 'Error':
            return resp

        x = resp.rstrip().split('\r')
        if len(x) > 1:
            for i in x:
                if i in self.COMMANDS:
                    resp = i[2:]
                    break
        else:
            resp = x[0][2:]

        if self.CMD == 'volume':
            if len(resp) == 3:
                resp = '%s.%s' % (resp[:2], resp[2:])
        elif self.CMD == 'source':
            if resp in self.SRC_NAMES:
                resp = self.SRC_NAMES[resp]
        if resp == 'STANDBY':
            msg = 'Power State:'
        return '[%s] %s %s' % (self.ADDRESS, msg, resp)

    def run(self):
        """
        Start the controller.
        """
        valid = False
        try:
            if sys.stdin.isatty(): # Check if running interactively
                while not valid:
                    valid = self.validate_connection_info(True)
            else:
                valid = self.validate_connection_info()
            if valid:
                #print('Denon AVR Remote')
                # Connect to Receiver
                connected,sock = self.connect()
                if connected:
                    # Parse and Execute Command
                    msg,resp = self.parse_command(sock)
                    disconnected = self.disconnect(sock) # Disconnect from receiver
                    # Print message with parsed response
                    print(self.parse_response(resp, msg))
                else:
                    print('There was a problem connecting to the receiver.')
        except KeyboardInterrupt:
            print('')
            exit(1)


def set_default_subparser(self, name, args=None):
    """
    Default subparser selection. Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    Tested with 2.7, 3.2, 3.3, 3.4, 3.6, 3.7
    It works with 2.6 assuming argparse is installed
    """
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
        if arg in ['-v', '--version']: # version if no subparser
            break
        if arg in ['-a', '--address']: # address requires subparser
            break
        if arg in ['-p', '--port']: # port requires subparser
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
            # Insert default in first position, this implies no
            # global options without a sub_parsers specified
            if args is None:
                sys.argv.insert(1, name)
            else:
                args.insert(0, name)

# Start Of Program
# Set up ArgParser
argparse.ArgumentParser.set_default_subparser = set_default_subparser
parser = argparse.ArgumentParser(prog='avremote',
                                 description='Denon AVR Remote',
                                 add_help=False)
parser.add_argument(
    '--help', '-h',
    action='help',
    default=argparse.SUPPRESS,
    help='Show this help message and exit.')

parser.add_argument(
    '--version', '-v',
    action='version',
    version='%(prog)s v0.1beta BarryTheButcher Copyright \xa9 2019')

parser.add_argument(
    '--address', '-a',
    action='store',
    dest='address',
    default=default_ip,
    help='IP Address of the AVR to connect to.')

parser.add_argument(
    '--port', '-p',
    action='store',
    dest='port',
    default=default_port,
    help='Port to connect on')

subparser = parser.add_subparsers(dest='cmd')
subparser_cmd = subparser.add_parser('power')
subparser_cmd.add_argument(
    'val',
    type=str.lower,
    action='store',
    default='status',
    const='status',
    nargs='?',
    choices=['status', 'on', 'off', 'toggle'])

subparser_cmd = subparser.add_parser('volume')
volume_choices = list(range(91))

x=0
while x < len(volume_choices):
    volume_choices[x] = str(volume_choices[x])
    x += 1

volume_choices.insert(0, 'down')
volume_choices.insert(0, 'up')
volume_choices.insert(0, 'status')

subparser_cmd.add_argument(
    'val',
    type=str.lower,
    action='store',
    default='status',
    const='status',
    nargs='?',
    choices=volume_choices,
    metavar='status, up, down, [0-90]')

subparser_cmd = subparser.add_parser('mute')
subparser_cmd.add_argument(
    'val',
    type=str.lower,
    action='store',
    default='toggle',
    const='toggle',
    nargs='?',
    choices=['status', 'toggle'])

subparser_cmd = subparser.add_parser('source')
subparser_cmd.add_argument(
    'val',
    type=str.lower,
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

# Set power as the default subparser and parse args
parser.set_default_subparser('power')
args = parser.parse_args()

if args.cmd is None or args.val is None:
    print('Error Parsing Arguments')
    exit(1)

controller = AVRController(args)
# Run Controller
controller.run()

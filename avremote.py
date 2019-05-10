#!/usr/bin/env python3
# Denon AVR Remote for CLI
# Copyright (C) 2019  Barry Van Deerlin
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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


class AVRController:

    def __init__(self, args):
        '''
        Initialize AVRController Object.
        args: is a Namespace object containing the following attributes:
            address: is the IPv4 address of the AVR.
            port: is the port to communicate on.
            cmd: is the type of command to perform.
            action: is the command action to be performed.
        '''
        self.ADDRESS = args.address
        self.PORT = args.port
        self.CMD = args.cmd
        self.ACTION = args.action

        # Command Dictionaries
        self.PREFIXES = {'power': 'PW',
                         'volume': 'MV',
                         'mute': 'MU',
                         'source': 'SI'}

        self.CODES = {'status': 'status',
                      'toggle': 'toggle',
                      'on': 'PWON',
                      'off': 'PWSTANDBY',
                      'up': 'MVUP',
                      'down': 'MVDOWN',
                      'm_on': 'MUON',
                      'm_off': 'MUOFF',
                      'bluetooth': 'SIBT',
                      'tuner': 'SITUNER',
                      'aux': 'SIAUX1',
                      'iradio': 'SIIRADIO',
                      'mplayer': 'SIMPLAY',
                      'game': 'SIGAME',
                      'dvd': 'SIDVD',
                      'bluray': 'SIBD',
                      'favorites': 'SIFAVORITES',
                      'sirius': 'SISIRIUSXM',
                      'pandora': 'SIPANDORA',
                      'ipod': 'SIUSB/IPOD'}

        self.SCODES = {'power': 'PW?',
                       'volume': 'MV?',
                       'mute': 'MU?',
                       'source': 'SI?'}

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

        # Message Labels
        self.LABELS = {'power': 'Power State:',
                       'volume': 'Volume Level:',
                       'mute': 'Mute State:',
                       'source': 'Source Input:'}

        # Functions for sending commands
        self.SEND = {'power': self.send_power_command,
                     'volume': self.send_volume_command,
                     'mute': self.send_mute_command,
                     'source': self.send_source_command}

        # Error Messages
        self.ERRORS = {'1': 'Error while connecting to the receiver',
                       '2': 'Error while receiving status',
                       '3': 'Error while sending command'}

    def validate_ip(self):
        '''
        Test if self.ADDRESS is a valid IPv4 address
        and return True/False.
        '''
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
        '''
        Test that necessary connection data is present and
        return True/False. If it isn't and script is being
        run interactively, then ask for it.
        interactive: if set then script is being run interactively.
        '''
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
        return True

    def connect(self):
        '''
        Create a socket connection and try to connect to it.
        Return socket object unless an exception is thrown.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((self.ADDRESS, int(self.PORT)))
        except Exception as e:
            print(e)
        else:
            return sock

    def disconnect(self, sock):
        '''
        Shutdown and close socket connection.
        '''
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

    def send_command(self, sock, cmd):
        '''
        Try to send command via socket and return True/False.
        '''
        try:
            sock.send('{0}\r'.format(cmd).encode('utf-8'))
        except Exception as e:
            print(e)
        else:
            return True
        return False

    def recv_status(self, sock, cmd, receive_only=False):
        '''
        Try to send a status command and return the response.
        '''
        resp=''
        try:
            if not receive_only:
                while resp[:2] != cmd[:2] or resp[:5] == 'MVMAX':
                    sock.send('{0}\r'.format(cmd).encode('utf-8'))
                    resp = str(sock.recv(16), 'utf-8')
            else:
                resp = str(sock.recv(16), 'utf-8')
        except Exception as e:
            print(e)
        else:
            return resp.rstrip()
        return self.ERRORS['2']

    def split(self, r):
        '''
        Split a response at carriage returns and return
        the correct one
        '''
        x = r.split('\r')
        if len(x) > 1:
            for i in x:
                if i in self.CODES.values():
                    return i
        return r

    def toggle(self, status, a, b):
        '''
        Compare status to a and return b if status equals a
        '''
        if status == a:
            return b
        return a

    def send_power_command(self, sock, cmd, status_cmd):
        '''
        Send a power command and return the response.
        '''
        resp = self.split(self.recv_status(sock, status_cmd))
        if cmd != 'status' and cmd != resp:
            if cmd == 'toggle': # Toggle power on or off
                cmd = self.toggle(resp,
                                  self.CODES['on'],
                                  self.CODES['off'])
            if self.send_command(sock, cmd): # Send Command
                return self.split(self.recv_status(sock, status_cmd))
            else:
                return self.ERRORS['3']
        return resp

    def send_volume_command(self, sock, cmd, status_cmd):
        '''
        Send a volume command and return the response.
        '''
        resp = self.split(self.recv_status(sock, status_cmd))
        maxVolume = self.recv_status(sock, None, True)
        if cmd != 'status' or resp == self.ERRORS['2']:
            power_state = self.recv_status(sock, self.SCODES['power'])
            if power_state == self.CODES['on']:
                if cmd != resp:
                    if self.send_command(sock, cmd):
                        return self.split(self.recv_status(sock, status_cmd))
                    else:
                        return self.ERRORS['3']
            else:
                return power_state
        return resp

    def send_mute_command(self, sock, cmd, status_cmd):
        '''
        Send a mute command and return the response.
        '''
        resp = self.split(self.recv_status(sock, status_cmd))
        if cmd != 'status' or resp == self.ERRORS['2']:
            power_state = self.recv_status(sock, self.SCODES['power'])
            if power_state == self.CODES['on']:
                # Toggle mute on or off
                cmd = self.toggle(resp,
                                  self.CODES['m_on'],
                                  self.CODES['m_off'])
                if self.send_command(sock, cmd):
                    return self.split(self.recv_status(sock, status_cmd))
                else:
                    return self.ERRORS['3']
            else:
                return power_state
        return resp

    def send_source_command(self, sock, cmd, status_cmd):
        '''
        Send a source command and return the response.
        '''
        resp = self.split(self.recv_status(sock, status_cmd))
        if cmd != 'status' or resp == self.ERRORS['2']:
            power_state = self.recv_status(sock, self.SCODES['power'])
            if power_state == self.CODES['on']:
                if cmd != resp:
                    if self.send_command(sock, cmd):
                        return self.split(self.recv_status(sock, status_cmd))
                    else:
                        return self.ERRORS['3']
            else:
                return power_state
        return resp

    def parse_command(self, sock):
        '''
        Parse self.CMD and send command.
        Returns a tuple of message label and response.
        '''
        if self.ACTION not in self.CODES:
            cmd = '%s%02d' % (self.PREFIXES[self.CMD], int(self.ACTION))
            return (self.LABELS[self.CMD],
                    self.SEND[self.CMD](sock,
                                        cmd,
                                        self.SCODES[self.CMD]))
        return (self.LABELS[self.CMD],
                self.SEND[self.CMD](sock,
                                    self.CODES[self.ACTION],
                                    self.SCODES[self.CMD]))

    def parse_response(self, resp, msg):
        '''
        Format message label and response for output to stdout
        and return string.
        '''
        if resp in self.ERRORS:
            return '[%s] %s' % (self.ADDRESS, resp)

        resp = resp[2:]
        if self.CMD == 'volume':
            if len(resp) == 3:
                resp = '%d.%d' % (int(resp[:2]), int(resp[2:]))
            elif resp.isdigit():
                resp = int(resp)
        elif self.CMD == 'source':
            if resp in self.SRC_NAMES:
                resp = self.SRC_NAMES[resp]
        if resp == 'STANDBY':
            msg = self.LABELS['power']
        return '[%s] %s %s' % (self.ADDRESS, msg, resp)

    def main(self):
        '''
        Start the controller.
        '''
        #if self.CMD is None or self.ACTION is None:
        #    print(self.ERRORS['1'])
        #    sys.exit(1)

        valid = False
        try:
            if sys.stdin.isatty(): # Check if running interactively
                while not valid:
                    valid = self.validate_connection_info(True)
            else:
                valid = self.validate_connection_info()
            if valid:
                #print('Denon AVR Remote')
                # Connect to receiver
                sock = self.connect()
                if sock is not None:
                    # Parse and execute command
                    msg,resp = self.parse_command(sock)
                    self.disconnect(sock)
                    # Print message with parsed response
                    print(self.parse_response(resp, msg))
                else:
                    print('[%s] %s' % (sock, self.ERRORS['1']))
        except KeyboardInterrupt:
            print('')
            sys.exit(1)


def set_default_subparser(self, name, args=None):
    '''
    Default subparser selection.
    Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    Tested with 2.7, 3.2, 3.3, 3.4, 3.6, 3.7
    It works with 2.6 assuming argparse is installed
    '''
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
                if sp_name == name: # Check existance of default parser
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
    version='%(prog)s v0.1beta Copyright (C) 2019 Barry Van Deerlin')

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
    'action',
    type=str.lower,
    action='store',
    default='status',
    const='status',
    nargs='?',
    choices=['status', 'on', 'off', 'toggle'])

subparser_cmd = subparser.add_parser('volume')
volume_choices = list(range(91))
for i, choice in enumerate(volume_choices):
    volume_choices[i] = str(choice)

volume_choices.insert(0, 'down')
volume_choices.insert(0, 'up')
volume_choices.insert(0, 'status')

subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default='status',
    const='status',
    nargs='?',
    choices=volume_choices,
    metavar='status, up, down, [0-90]')

subparser_cmd = subparser.add_parser('mute')
subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default='toggle',
    const='toggle',
    nargs='?',
    choices=['status', 'toggle'])

subparser_cmd = subparser.add_parser('source')
subparser_cmd.add_argument(
    'action',
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

if args.cmd is None or args.action is None:
            print('Error while parsing arguments')
            sys.exit(1)

# Initialize Controller
controller = AVRController(args)
# Run Controller
controller.main()

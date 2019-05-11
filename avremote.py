#!/usr/bin/env python3
# vim: set foldenable:foldmethod=marker:sts=4:ts=8:sw=4:
# License Info                                                           {{{1
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

# Module Imports                                                         {{{1
import sys
import socket
import argparse
from time import sleep

# Default Connection Info                                                {{{1
# ex.
# default_ip = '192.168.0.100'
default_ip = ''
default_port = '23'

# Default Commands                                                       {{{1
default_subparser = 'power'
default_power_cmd = 'status'
default_volume_cmd = 'status'
default_mute_cmd = 'toggle'
default_source_cmd = 'status'
default_mode_cmd = 'status'

# Denon Class                                                            {{{1
class Denon:

    #### Dictionaries ####                                               {{{2
    # Command Codes                                                      {{{3
    codes = {'status': 'status',
             'toggle': 'toggle',
             'on': 'PWON',
             'off': 'PWSTANDBY',
             'up': 'MVUP',
             'down': 'MVDOWN',
             'mute': 'MUON',
             'unmute': 'MUOFF',
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
             'ipod': 'SIUSB/IPOD',
             'dolby': 'MSDOLBY DIGITAL',
             'stereo': 'MSSTEREO',
             'mstereo': 'MSMCH STEREO',
             'direct': 'MSDIRECT',
             'rock': 'MSROCK ARENA',
             'jazz': 'MSJAZZ CLUB'}

    # Status Command Codes                                               {{{3
    scodes = {'power': 'PW?',
              'volume': 'MV?',
              'mute': 'MU?',
              'source': 'SI?',
              'mode': 'MS?'}

    # Source Input Names                                                 {{{3
    src_names = {'BT': 'Bluetooth',
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

    # Sound Mode Names                                                   {{{3
    mode_names = {'DOLBY SURROUND': 'Dolby',
                  'STEREO': 'Stereo',
                  'MCH STEREO': 'MStereo',
                  'DIRECT': 'Direct',
                  'ROCK ARENA': 'Rock',
                  'JAZZ CLUB': 'Jazz'}

    # Message Labels                                                     {{{3
    labels = {'power': 'Power State:',
              'volume': 'Volume Level:',
              'mute': 'Mute State:',
              'source': 'Source Input:',
              'mode': 'Sound Mode:'}

    # Error Messages                                                     {{{3
    errors = {1: 'Error while parsing arguments',
              2: 'Error while connecting to the receiver',
              3: 'Error while receiving status',
              4: 'Error while sending command'}

    # Initialize Denon Object                                            {{{2
    def __init__(self, args):
        '''
        Initialize Denon Object.
        args: is a Namespace object derived from Argparse
        containing the following attributes:
            address: is the IPv4 address of the AVR.
            port: is the port to communicate on.
            cmd: is the type of command to perform.
            action: is the command action to be performed.
        '''
        # Connection and Requested Command information
        self.address = args.address
        self.port = args.port
        self.cmd = args.cmd
        self.action = args.action

    # Validate IP address                                                {{{2
    def validate_ip(self):
        '''
        Test if self.address is a valid IPv4 address
        and return True/False.
        '''
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

    # Validate connection information                                    {{{2
    def validate_connection_info(self, interactive=False):
        '''
        Test that necessary connection data is present and
        return True/False. If it isn't and script is being
        run interactively, then ask for it.
        interactive: if set then script is being run interactively.
        '''
        if self.address == '':
            print('IP Address is not set')
            if interactive:
                self.address = input('Enter IP Address: ')
                return self.validate_connection_info(True)
        elif self.port == '':
            print('Port is not set')
            if interactive:
                self.port = input('Enter Port: ')
                return self.validate_connection_info(True)
        elif not self.validate_ip():
            print('IP Address is invalid')
            if interactive:
                self.address = input('Enter IP Address: ')
                return self.validate_connection_info(True)
        elif not self.port.isdigit():
            print('Port is invalid')
            if interactive:
                self.port = input('Enter Port: ')
                return self.validate_connection_info(True)
        return True

    # Connect to receiver                                                {{{2
    def connect(self):
        '''
        Create a socket connection and try to connect to it.
        Return socket object unless an exception is thrown.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((self.address, int(self.port)))
        except Exception as e:
            print(e)
        else:
            return sock

    # Disconnect from receiver                                           {{{2
    def disconnect(self, sock):
        '''Shutdown and close socket connection.'''
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except Exception as e:
            print(e)

    # Send command code (low level)                                      {{{2
    def send(self, sock, cmd):
        '''Try to send command via socket and return True/False.'''
        try:
            sock.send('{}\r'.format(cmd).encode('utf-8'))
        except Exception as e:
            print(e)
        else:
            return True
        return False

    # Receive status command response (low level)                        {{{2
    def recv_status(self, sock, cmd, receive_only=False):
        '''Try to send a status command and return the response.'''
        resp=''
        try:
            if not receive_only:
                while resp[:2] != cmd[:2] or resp[:5] == 'MVMAX':
                    sock.send('{}\r'.format(cmd).encode('utf-8'))
                    resp = str(sock.recv(32), 'utf-8')
            else:
                resp = str(sock.recv(32), 'utf-8')
        except Exception as e:
            print(e)
        else:
            return self.split(resp)
        return self.errors[3]

    # Split a response by carriage return                                {{{2
    def split(self, r):
        '''Split a response at carriage returns and return the correct one'''
        x = r.rstrip().split('\r')
        if len(x) > 1:
            for i in x:
                if i in self.codes.values():
                    return i
        return x[0]

    # Toggle between 2 commands                                          {{{2
    def toggle(self, status, a, b):
        '''Compare status to a and return b if status equals a'''
        if status == a:
            return b
        return a

    # Send command (uses send and recv_status)                           {{{2
    def send_command(self, sock, cmd, status_cmd):
        '''Send a command to receiver and return response.'''
        resp = self.recv_status(sock, status_cmd)
        if cmd != 'status' and cmd != resp and resp != self.errors[3]:
            pwr_cmd = False
            mute_cmd = False
            if status_cmd[:2] == "PW":
                pwr_cmd = True
                toggle_types = ['on', 'off']
                power_state = resp
            elif status_cmd[:2] == "MU":
                mute_cmd = True
                toggle_types = ['mute', 'unmute']
                power_state = self.recv_status(sock, self.scodes['power'])
            else:
                power_state = self.recv_status(sock, self.scodes['power'])

            if pwr_cmd or mute_cmd:
                if cmd == 'toggle':
                    cmd  = self.toggle(resp,
                                       self.codes[toggle_types[0]],
                                       self.codes[toggle_types[1]])

            if pwr_cmd or power_state == self.codes['on']:
                if self.send(sock, cmd):
                    return self.recv_status(sock, status_cmd)
                else:
                    return self.errors[4]
            else:
                return power_state
        return resp

    # Parse command                                                      {{{2
    def parse_command(self, sock):
        '''
        Parse self.cmd and send command.
        Returns a tuple of message label and response.
        '''
        if self.action not in self.codes:
            cmd = '{}{:02}'.format(self.scodes[self.cmd][:2],
                                   int(self.action))
            return (self.labels[self.cmd],
                    self.send_command(sock,
                                      cmd,
                                      self.scodes[self.cmd]))
        return (self.labels[self.cmd],
                self.send_command(sock,
                                  self.codes[self.action],
                                  self.scodes[self.cmd]))

    # Parse response                                                     {{{2
    def parse_response(self, msg, resp):
        '''
        Format message label and response for output to stdout
        and return the formatted string.
        '''
        if resp in self.errors.values():
            print('[{}] {}'.format(self.address, resp))
            sys.exit(1)

        resp = resp[2:]
        if self.cmd == 'volume':
            if len(resp) == 3:
                resp = '{}.{}'.format(int(resp[:2]), int(resp[2:]))
            elif resp.isdigit():
                resp = int(resp)
        elif self.cmd == 'source':
            if resp in self.src_names:
                resp = self.src_names[resp]
        elif self.cmd == 'mode':
            if resp in self.mode_names:
                resp = self.mode_names[resp]
            else:
                resp = resp.lower().capitalize()
        if resp == 'STANDBY':
            msg = self.labels['power']
        return '[{}] {} {}'.format(self.address, msg, resp)

    # Main method of Denon Class                                         {{{2
    def main(self):
        '''Start the controller instance.'''
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
                    # Print message with parsed response
                    print(self.parse_response(*self.parse_command(sock)))
                    self.disconnect(sock)
                else:
                    print('[{}] {}'.format(sock, self.errors[2]))
                    sys.exit(1)
        except KeyboardInterrupt:
            print('')
            sys.exit(130)


# Set Default Subparser                                                  {{{1
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


# Set up ArgParser                                                       {{{1
argparse.ArgumentParser.set_default_subparser = set_default_subparser
parser = argparse.ArgumentParser(prog='avremote',
                                 description='Denon AVR Remote',
                                 add_help=False)

# Add help argument                                                      {{{2
parser.add_argument(
    '--help', '-h',
    action='help',
    default=argparse.SUPPRESS,
    help='Show this help message and exit.')

# Add version argument                                                   {{{2
parser.add_argument(
    '--version', '-v',
    action='version',
    version='%(prog)s v0.1beta Copyright (C) 2019 Barry Van Deerlin')

# Add IP address argument                                                {{{2
parser.add_argument(
    '--address', '-a',
    action='store',
    dest='address',
    default=default_ip,
    help='IP Address of the AVR to connect to.')

# Add port argument                                                      {{{2
parser.add_argument(
    '--port', '-p',
    action='store',
    dest='port',
    default=default_port,
    help='Port to connect on')

# Add subparsers                                                         {{{2
subparser = parser.add_subparsers(dest='cmd')
# Add power subparser                                                    {{{3
subparser_cmd = subparser.add_parser('power')
subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default=default_power_cmd,
    nargs='?',
    choices=['status', 'on', 'off', 'toggle'])

# Add volume subparser                                                   {{{3
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
    default=default_volume_cmd,
    nargs='?',
    choices=volume_choices,
    metavar='{status, up, down, [0-90]}')

# Add mute subparser                                                     {{{3
subparser_cmd = subparser.add_parser('mute')
subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default=default_mute_cmd,
    nargs='?',
    choices=['status', 'toggle'])

# Add source subparser                                                   {{{3
subparser_cmd = subparser.add_parser('source')
subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default=default_source_cmd,
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

# Add mode subparser                                                     {{{3
subparser_cmd = subparser.add_parser('mode')
subparser_cmd.add_argument(
    'action',
    type=str.lower,
    action='store',
    default=default_mode_cmd,
    nargs='?',
    choices=['status',
             'dolby',
             'stereo',
             'mstereo',
             'direct',
             'rock',
             'jazz'])

# Set power as the default subparser and parse args                      {{{2
parser.set_default_subparser(default_subparser)
args = parser.parse_args()
if args.cmd is None or args.action is None:
            print(Denon.errors[1])
            parser.print_help()
            sys.exit(2)

# Initialize and Run Controller                                          {{{1
controller = Denon(args)
controller.main()

# denon_avr_remote
CLI Remote for Denon AVRs

This script has been tested with Denon AVR-S710W and may not be compatible with other receivers

If you test it with another receiver and it works let me know!

This is a very early version and it doesn't handle the connection as efficiently as I would like.
I plan to improve this in the future.

This script allows you to control a Denon Audio Video Receiver from the command line.

If you do not wish to enter an ip address every time you send a command then open the script in a text editor
and change default_ip to your receiver's IP Address.

```
# Default IP
# ex.
# default_ip = "192.168.0.100"
default_ip = ""
```

```
Command List:
	power [-h] (status, on, off, toggle)
	volume [-h] (status, up, down, [0-90])
	mute [-h] (status, toggle)
	source [-h] status
	            bluetooth
		    tuner
		    aux
		    iradio
		    mplayer
		    game
		    dvd
		    bluray
		    favorites
		    siriusxm
		    pandora
		    ipod
```

How to use:

```
# Template:
$ script primary_command secondary_command

# Examples: (All examples in this block perform the same task)
# Standard Usage
# If default_ip or default_port are not set in script then it
# will interactively ask for them
$ ./avremote.py power status

# Usage when default_ip and default_port ARE NOT set in script
# and you want to run script non-interactively. Or if you want to
# use a different ip or port from the defaults.
$ ./avremote.py -a 192.168.0.100 -p 23 power status

# The default secondary command for all primary commands is status
$ ./avremote.py power

# The default primary command if no commands are given is power
# -a and -p functionality do not work with this method of invoking
# the script. You must include the primary command if you wish to use them.
$ ./avremote.py
```



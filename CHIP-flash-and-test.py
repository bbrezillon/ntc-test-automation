#!/usr/bin/python2

import os
import pexpect
import subprocess
import datetime
import sys
import psutil
import time
import argparse
from ConfigParser import ConfigParser

parser = argparse.ArgumentParser(description="Images builder and flasher for CHIPs")
parser.add_argument("-c", "--conf-file", type=argparse.FileType("r"), default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "boards.conf"))

RELAY_IP = "192.168.1.210"
RELAY_PORT = 17494
power_cmd = "command_relay.py %s %d " % (RELAY_IP, RELAY_PORT)
fastboot_cmd = "fastboot -i 0x1f3a "

args = parser.parse_args()

config_parser = ConfigParser()
config_parser.readfp(args.conf_file)

class Device(object):
	def __init__(self, name, console, relay, random_powercuts):
		self.name = name
		self.console = console
		self.relay = relay
		self.random_powercuts = random_powercuts

devices = []

for section in config_parser.sections():
	name = section
	if config_parser.has_option(section, "console"):
		console = config_parser.get(section, "console")
	else:
		print "%s must have a `console` setting"
		sys.exit(-1)
	if config_parser.has_option(section, "relay"):
		relay = config_parser.getint(section, "relay")
	else:
		print "%s must have a `relay` setting"
		sys.exit(-1)
	if config_parser.has_option(section, "random-powercuts"):
		random_powercuts = config_parser.getboolean(section, "random-powercuts")
	else:
		random_powercuts = True
	devices.append(Device(name, console, relay, random_powercuts))

print "Checking pids file..."
if os.path.exists("pids"):
	print "Creating archives directory..."
	directory = str(datetime.datetime.today()).replace(":", "-").replace(" ", "_")
	os.spawnvp(os.P_WAIT, 'mkdir', ("mkdir %s" % directory).split())
	print "Killing all minicom, random-powercut and log_parser instances..."
	with open("pids", "r") as pid_file:
		i = 0
		while True:
			line = pid_file.readline().strip()
			if not line:
				break
			if i % 3 == 1:
				if not os.spawnvp(os.P_WAIT, 'screen', ("screen -X -S serial%s quit" % line).split()):
					print "Killing screen serial%s. Please wait..." % line
					time.sleep(5)

				print "Saving %s.log..." % line
				os.spawnvp(os.P_WAIT, 'mv', ("mv %s.log %s/" % (line, directory)).split())
				i += 1
				continue
			i += 1
			try:
				pid = int(line)
			except ValueError:
				continue
			if not pid:
				break
			try:
				psutil.Process(pid).kill()
				print "pid %d killed" % pid
			except psutil.NoSuchProcess:
				pass
else:
	print "No pids file, continue..."

# Create images
print "Creating images..."
os.spawnlp(os.P_WAIT, 'create-images.sh', 'create-images.sh')

for device in devices:
	print "Entering device %s bootloader..." % device.name
	# Enter fastboot mode on board
	serial = pexpect.spawn("picocom -b 115200 %s" % device.console, timeout=60)
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s off" % device.relay).split()) 
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s on" % device.relay).split()) 
	serial.expect(["Hit any key to stop autoboot"])
	serial.sendline('b')
	serial.expect(["=>"])
	serial.sendline("nand scrub.part -y UBI")
	serial.expect(["=>"])
	serial.sendline("fastboot 0")

	# Flash with fastboot
	print "Flashing device %s..." % device.name
	print "Erasing uboot partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "erase uboot").split())
	print "Writing uboot partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "flash uboot images/uboot.bin").split())
	# We don't need to erase the UBI partition (it has been scrubbed earlier)
	#print "Erasing UBI partition..."
	#os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "erase UBI").split())
	print "Writing UBI partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "flash UBI images/chip.ubi.sparse").split())
	serial.close()

	# plug off board
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s off" % device.relay).split()) 

print "Creating all minicom, random-powercut and log_parser instances..."
with open("pids", "w") as pid_file:
	for device in devices:
		pid = os.spawnvp(os.P_NOWAIT, 'log_parser.py', ("log_parser.py %s.log %s %s %d" % (device.name, device.relay, RELAY_IP, RELAY_PORT)).split())
		pid_file.write("%d\n" % pid)
		pid = os.spawnvp(os.P_NOWAIT, 'screen', ("screen -md -S serial%s minicom -D %s -b 115200 -C %s.log" % (device.name, device.console, device.name)).split())
		pid_file.write("%s\n" % device.name)
		os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s on" % device.relay).split()) 
		if not device.random_powercuts:
			pid_file.write("No random-powercut\n")
		else:
			pid = os.spawnvp(os.P_NOWAIT, 'random-powercut.sh', ("random-powercut.sh %s %s %d" % (device.relay, RELAY_IP, RELAY_PORT)).split())
			pid_file.write("%d\n" % pid)

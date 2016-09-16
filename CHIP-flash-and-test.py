#!/usr/bin/python2

import os
import pexpect
import subprocess
import datetime
import sys
import psutil
import time

RELAY_IP = "192.168.1.210"
RELAY_PORT = 17494
power_cmd = "command_relay.py %s %d " % (RELAY_IP, RELAY_PORT)
fastboot_cmd = "fastboot -i 0x1f3a "

for device in sys.argv[1:]:
	if len(device.split(":")) not in [3,4]:
		print "ARGS should be of kind: 'console:relay_port:log_name[:random_powercut?]'"
		sys.exit(-1)

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

for device in sys.argv[1:]:
	print "Entering device %s bootloader..." % device
	dev = device.split(":")
	# Enter fastboot mode on board
	serial = pexpect.spawn("picocom -b 115200 %s" % dev[0])
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s off" % dev[1]).split()) 
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s on" % dev[1]).split()) 
	serial.expect(["Hit any key to stop autoboot"])
	serial.sendline('b')
	serial.expect(["=>"])
	serial.sendline("fastboot 0")

	# Flash with fastboot
	print "Flashing device %s..." % device
	print "Erasing uboot partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "erase uboot").split())
	print "Writing uboot partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "flash uboot images/uboot.bin").split())
	print "Erasing UBI partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "erase UBI").split())
	print "Writing UBI partition..."
	os.spawnvp(os.P_WAIT, 'fastboot', (fastboot_cmd + "flash UBI images/chip.ubi.sparse").split())
	serial.close()

	# plug off board
	os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s off" % dev[1]).split()) 

print "Creating all minicom, random-powercut and log_parser instances..."
with open("pids", "w") as pid_file:
	for device in sys.argv[1:]:
		dev = device.split(":")
		pid = os.spawnvp(os.P_NOWAIT, 'log_parser.py', ("log_parser.py %s.log %s %s %d" % (dev[2], dev[1], RELAY_IP, RELAY_PORT)).split())
		pid_file.write("%d\n" % pid)
		pid = os.spawnvp(os.P_NOWAIT, 'screen', ("screen -md -S serial%s minicom -D %s -b 115200 -C %s.log" % (dev[2], dev[0], dev[2])).split())
		pid_file.write("%s\n" % dev[2])
		os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + "%s on" % dev[1]).split()) 
		if len(dev) == 4 and dev[3] == 'no':
			pid_file.write("No random-powercut\n")
		else:
			pid = os.spawnvp(os.P_NOWAIT, 'random-powercut.sh', ("random-powercut.sh %s %s %d" % (dev[1], RELAY_IP, RELAY_PORT)).split())
			pid_file.write("%d\n" % pid)

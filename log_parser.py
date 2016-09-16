#!/usr/bin/python2

import sys
import argparse
import pexpect
import select
import re
import smtplib
import os

from email.mime.text import MIMEText

#FIXME: Known bug: last line not seen

parser = argparse.ArgumentParser(description='Log parser')

parser.add_argument('FILE', help='path to the log to parse')
parser.add_argument('RELAY', type=int, help="relay port associated to the board whose log is being parsed")
parser.add_argument('RELAY_IP', help="IP address of the relays")
parser.add_argument('RELAY_PORT', type=int, help="port of the relays")

args = parser.parse_args()

power_cmd = "command_relay.py %s %d %d" % (args.RELAY_IP, args.RELAY_PORT, args.RELAY)

server = smtplib.SMTP('', '')
server.ehlo()
server.starttls()
server.login('', '')

recipients = [""]
me = ""

def send_mail(line, filename, reboot=False):
	content = "An error occured on device %s:\n%s" % (filename, line)
	if reboot:
		content += "\nThe device is being rebooted."
	msg = MIMEText(content)
	msg['Subject'] = "Error on device %s" % filename
	msg['To'] = ", ".join(recipients)
	msg['From'] = me
	server.sendmail(me, recipients, msg.as_string())

#Timeout in milli seconds before board is declared dead
timeout = 60 * 1000 * 10

reboot_templates = ['send stop command failed']
matching_templates = ['UBI.*err', 'Oops']
matching_res = []
reboot_res = []
for matching_template in matching_templates:
	matching_res.append(re.compile(matching_template))

for reboot_template in reboot_templates:
	reboot_res.append(re.compile(reboot_template))

serial = pexpect.spawn("tail -F %s" % args.FILE)
poll = select.poll()
poll.register(serial, select.POLLIN)

while True:
	poll_ok = poll.poll(timeout)
	if not poll_ok:
		print "Timeout detected for log %s" % args.FILE
		#what to do for timeout?
		continue

	try:
		line = serial.readline()
	except pexpect.TIMEOUT:
		print "Timeout detected for log %s" % args.FILE
		#what to do for timeout?
		continue
	for matching_re in matching_res:
		match = matching_re.search(line)
		if match:
			send_mail(line, args.FILE)
			break
	if match:
		continue
	for reboot_re in reboot_res:
		match = reboot_re.search(line)
		if match:
			os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + " off").split())
			os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + " on").split())
			send_mail(line, args.FILE, True)
			break


server.quit()
sys.exit(0)

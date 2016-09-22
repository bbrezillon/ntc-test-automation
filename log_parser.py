#!/usr/bin/python2

import sys
import argparse
import pexpect
import select
import re
import smtplib
import os
import time
import smtp_credentials

from email.mime.text import MIMEText

#FIXME: Known bug: last line not seen

parser = argparse.ArgumentParser(description='Log parser')

parser.add_argument('FILE', help='path to the log to parse')
parser.add_argument('RELAY', type=int, help="relay port associated to the board whose log is being parsed")
parser.add_argument('RELAY_IP', help="IP address of the relays")
parser.add_argument('RELAY_PORT', type=int, help="port of the relays")

args = parser.parse_args()

power_cmd = "command_relay.py %s %d %d" % (args.RELAY_IP, args.RELAY_PORT, args.RELAY)


recipients = smtp_credentials.recipients
me = smtp_credentials.mail

def send_mail(status, filename, line="", reboot=False):
	content = "%s occured on device %s:\n%s" % (status, filename, line)
	if reboot:
		content += "\nThe device is being rebooted."
	msg = MIMEText(content)
	msg['Subject'] = "%s on device %s" % (status, filename)
	msg['To'] = ", ".join(recipients)
	msg['From'] = me
	server = smtplib.SMTP(smtp_credentials.server, smtp_credentials.port)
	server.ehlo()
	server.starttls()
	server.login(smtp_credentials.login, smtp_credentials.password)
	server.sendmail(me, recipients, msg.as_string())
	server.quit()

def timeout_detected(filename):
	if not first_freeze:
		return
	if time.mktime(time.gmtime()) >= freeze_timeout + last_line:
		send_mail("timeout of %ds" % freeze_timeout, filename)

#Timeout in milli seconds before serial is considered frozen
timeout = 60 * 1000 * 10

#Timeout in seconds before board is declared crashed
freeze_timeout = 60 * 30
last_line = time.mktime(time.gmtime())
first_freeze = True
first_err = True

board_rebooted_re = re.compile('Hit any key to stop autoboot')
reboot_templates = ['send stop command failed', 'Oops']
matching_templates = ['UBI.*err']
matching_res = []
reboot_res = []
for matching_template in matching_templates:
	matching_res.append(re.compile(matching_template))

for reboot_template in reboot_templates:
	reboot_res.append(re.compile(reboot_template))

serial = pexpect.spawn("tail -F %s" % args.FILE, timeout=freeze_timeout)
poll = select.poll()
poll.register(serial, select.POLLIN)

while True:
	poll_ok = poll.poll(timeout)
	if not poll_ok:
		timeout_detected(args.FILE)
		first_freeze = False
		continue

	try:
		line = serial.readline()
	except pexpect.TIMEOUT:
		timeout_detected(args.FILE)
		first_freeze = False
		continue

	last_line = time.mktime(time.gmtime())
	if board_rebooted_re.search(line):
		first_freeze = True
		first_err = True
	for matching_re in matching_res:
		match = matching_re.search(line)
		if match:
			if first_err:
				send_mail("error", args.FILE, line)
			first_err = False
			break
	if match:
		continue
	for reboot_re in reboot_res:
		match = reboot_re.search(line)
		if match:
			os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + " off").split())
			os.spawnvp(os.P_WAIT, 'command_relay.py', (power_cmd + " on").split())
			send_mail("error", args.FILE, line, True)
			break


sys.exit(0)

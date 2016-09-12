#!/usr/bin/python2

import sys
import argparse
import pexpect
import select
import re
import smtplib

from email.mime.text import MIMEText

#FIXME: Known bug: last line not seen

parser = argparse.ArgumentParser(description='Log parser')

parser.add_argument('FILE', help='path to the log to parse')

args = parser.parse_args()

server = smtplib.SMTP('', '')
server.ehlo()
server.starttls()
server.login('', '')

recipients = [""]
me = ""

def send_mail(line, filename):
	msg = MIMEText("An error occured on device %s:\n%s" % (filename, line))
	msg['Subject'] = "Error on device %s" % filename
	msg['To'] = ", ".join(recipients)
	msg['From'] = me
	server.sendmail(me, recipients, msg.as_string())

#Timeout in milli seconds before board is declared dead
timeout = 60 * 1000 * 10

matching_templates = ['ubi.*error']
matching_res = []
for matching_template in matching_templates:
	matching_res.append(re.compile(matching_template))

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

server.quit()
sys.exit(0)

#!/usr/bin/python2

import socket
import sys
import argparse

parser = argparse.ArgumentParser(description='Command relays from Devantech ETH008 via TCP/IP.')

parser.add_argument('HOST', help='IP address of the controlling board (Devantech ETH008)')
parser.add_argument('PORT', type=int, help='port on which the controlling board is listening TCP/IP')
parser.add_argument('--password', default=None, help='password to access TCP/IP commands on controlling board')
parser.add_argument('RELAY', type=int, choices=range(1,9), help='relay to control')
parser.add_argument('COMMAND', choices=['on', 'off'], help='command to send to the relay')

args = parser.parse_args()

def exit(code):
    s.close()
    sys.exit(code)

try:
    s = socket.create_connection((args.HOST,args.PORT))
except:
    print('Failed to connect to %s on port %s' % (args.HOST, args.PORT))
    sys.exit(1)

if args.password is not None:
    try:
        msg = '\x79' + args.password
        ans = s.sendall(msg)
    except:
        print('Failed to send password')
        exit(1)
    if ans is not None:
        print('Failed to send password')
        exit(1)
    ans = s.recv(1)
    if ans == '\x01':
        print('Successfully authenticated')
    else:
        print('Failed to authenticate')
        exit(1)

try:
    if args.COMMAND == 'on':
        msg = '\x20'
    else:
        msg = '\x21'
    msg += chr(args.RELAY)  
    msg += '\x00'
    ans = s.sendall(msg)
except Error as e:
    print(e)
    print('Failed to send command "%s" to relay %d' % (args.COMMAND, args.RELAY))
    exit(1)
if ans is not None:
    print('Failed to send command "%s" to relay %d' % (args.COMMAND, args.RELAY))
    exit(1)

ans = s.recv(1)
if ans == '\x00':
    print('Command "%s" on relay %d executed successfully' % (args.COMMAND, args.RELAY))
else:
    print('Command "%s" on relay %d failed' % (args.COMMAND, args.RELAY))

if args.password is not None:
    try:
        ans = s.sendall('\x7B')
    except:
        print('Failed to logout')
        exit(1)
    if ans is not None:
        print('Failed to logout')
        exit(1)

s.close()
sys.exit(0)

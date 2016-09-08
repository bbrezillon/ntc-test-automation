#!/bin/bash

RELAY=$1
RELAY_IP=$2
RELAY_PORT=$3

command_relay.py $RELAY_IP $RELAY_PORT $RELAY on

while [ true ]; do
	echo "rnd = $RANDOM"
	WAIT=$(((RANDOM%600)+60))
	echo "waiting $WAIT secs before power-cut"
	sleep $WAIT
	
	command_relay.py $RELAY_IP $RELAY_PORT $RELAY off
	sleep 5
	command_relay.py $RELAY_IP $RELAY_PORT $RELAY on
done

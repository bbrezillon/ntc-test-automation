#!/bin/bash

RELAY=$1
RELAY_IP=$2
RELAY_PORT=$3
MIN_TIME=$4
MAX_TIME=$5

if [ "x$MIN_TIME" = "x" ]; then
	MIN_TIME=300
fi

if [ "x$MAX_TIME" = "x" ]; then
	MAX_TIME=900
fi

command_relay.py $RELAY_IP $RELAY_PORT $RELAY on

while [ true ]; do
	echo "rnd = $RANDOM"
	WAIT=$(((RANDOM%(MAX_TIME-MIN_TIME))+MIN_TIME))
	echo "waiting $WAIT secs before power-cut"
	sleep $WAIT
	
	command_relay.py $RELAY_IP $RELAY_PORT $RELAY off
	sleep 5
	command_relay.py $RELAY_IP $RELAY_PORT $RELAY on
done

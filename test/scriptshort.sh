#!/bin/bash
while true
do 
	# Echo current date to stdout
	echo 'stdout'
	# Echo 'error!' to stderr
	echo 'virhe!' >&2
	sleep 3
done
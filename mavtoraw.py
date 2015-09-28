'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.

mavue.py
This is the main file. 

Usage: mavue.py [options]

Options:
  -h, --help            show this help message and exit
  --baudrate=BAUDRATE   master port baud rate
  --device=DEVICE       serial device
  --dialect=DIALECT     Mavlink dialect
  --logfile=LOGFILE_RAW
                        output log file
  --notimestamps=NOTIMESTAMPS
                        logfile format
  --source-system=SOURCE_SYSTEM
                        MAVLink source system for this GCS

After startup, the message inspector window will show a tree of all received messages. 
To plot values, click "add plot" and drag and drop message contents onto the plot window, or onto the "x" or "y" button of an existing plot item.
Message streams can be activated/deactivated by clicking the checkbox in front of them. 
Double-clicking the frequency allows to edit the message stream frequency (only supported on the MAVRIC autopilot).
MAVlink parameters can be edited by double-clicking on the value behind the parameter message. 
'''

#!/usr/bin/python



import sys
import mavlink_receiver
import pickle
import time

#import mavutil


if __name__ == '__main__':
	mavlinkReceiver=mavlink_receiver.MAVlinkReceiver(threading=False)

	#mavForwarder = mavutil.mavlink_connection(device="udp:localhost:14549", source_system=1,  write=True)
	#mavForwarder.last_address=('127.0.0.1', 14550)
	log_counter=1

	while True:
		msg = mavlinkReceiver.master.recv_msg()
		if msg!=None and msg.__class__.__name__!="MAVLink_bad_data":
			contents=[(fn, getattr(msg, fn)) for fn in msg.get_fieldnames()]
			print str(msg._header.srcSystem)+":"+ str(msg._header.srcComponent)+"):", msg.__class__.__name__,contents
			#try:
			#	mavForwarder.mav.send(msg)
			#except:
			#	print "error forwarding"
			if msg.__class__.__name__=="MAVLink_statustext_message" and msg._header.srcComponent==10 and getattr(msg,  "text").startswith("adding task LED"):
				if mavlinkReceiver.opts.logfile_raw!="":
					new_log=mavlinkReceiver.opts.logfile_raw + "%04d" % log_counter
					log_counter+=1
					print "New powerup detected - starting new output logfile:", new_log
					oldfile=mavlinkReceiver.master.logfile_raw
					mavlinkReceiver.master.logfile_raw=open(new_log,  'w',  0)


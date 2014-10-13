#!/usr/bin/env python

'''
test mavlink messages
'''

import sys, struct, time, os
from curses import ascii
from googleearth_server import *

# allow import from the parent directory, where mavlink.py is
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pymavlink'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '.'))

import  mavutil
from pymavlink import pymavlink

from optparse import OptionParser

class MAVlinkReceiver:
    def __init__(self):
        parser = OptionParser("mavue.py [options]")

        parser.add_option("--baudrate", dest="baudrate", type='int',
                  help="master port baud rate", default=115200)
        parser.add_option("--device", dest="device", default="", help="serial device")
        parser.add_option("--dialect", dest="dialect", default="dbgextensions", help="Mavlink dialect")
        parser.add_option("--logfile", dest="logfile_raw", default="", help="output log file")
        parser.add_option("--notimestamps", dest="notimestamps", default="true", help="logfile format")
        parser.add_option("--source-system", dest='SOURCE_SYSTEM', type='int',
                  default=255, help='MAVLink source system for this GCS')
        (opts, args) = parser.parse_args()
        self.opts=opts
        self.serialPorts=self.scanForSerials()
        print "auto-detected serial ports:"
        for s in self.serialPorts:
            print s.device
        if opts.device=="":
            if len(self.serialPorts)==0:
                opts.device="udp:localhost:14550"
            else:
                opts.device=self.serialPorts[0].device
            print "auto-selected input device: ", opts.device
        #      if opts.device is None:
        #         print("You must specify a serial device")
        #         sys.exit(1)

        self.master=None
        # create a mavlink serial instance
        print ""
        print "Initialising as system ",   opts.SOURCE_SYSTEM,  "on device",  opts.device,  "(baud=",  opts.baudrate,  ")"
        print "with MAVlink dialect '",  opts.dialect, "'"
        print ""
        self.master = mavutil.mavlink_connection(opts.device, baud=opts.baudrate, source_system=opts.SOURCE_SYSTEM,  write=True,  dialect=opts.dialect,  notimestamps=opts.notimestamps)
        
        #open log file for data logging
        if opts.logfile_raw!="":
            self.master.logfile_raw=open(opts.logfile_raw,  'w',  0)
            
            
        self.msg=None;
        self.messages=dict();
 
        self.earthserver=None
        #self.earthserver=GoogleEarthServer()
        if self.earthserver!=None:
            self.earthserver.run()
        
        self.requestAllStreams()

    def reopenDevice(self, device):
        print ""
        print "Initialising as system ",   self.opts.SOURCE_SYSTEM,  "on device",  self.opts.device,  "(baud=",  self.opts.baudrate,  ")"
        print "with MAVlink dialect '",  self.opts.dialect, "'"
        print ""
        self.master = mavutil.mavlink_connection(device, baud=self.opts.baudrate, source_system=self.opts.SOURCE_SYSTEM,  write=True,  dialect=self.opts.dialect,  notimestamps=self.opts.notimestamps)

    def requestStream(self,  stream,  active,  frequency=0):
        if self.master==None:
            return
        # request activation/deactivation of stream. If frequency is 0, it won't be changed.
        reqMsg=pymavlink.MAVLink_request_data_stream_message(target_system=stream.get_srcSystem(), target_component=stream.get_srcComponent(), req_stream_id=stream.get_msgId(), req_message_rate=frequency, start_stop=active)

        self.master.write(reqMsg.pack(pymavlink.MAVLink(file=0,  srcSystem=self.master.source_system)))

        if active:
            print "System ", stream.get_srcSystem(), stream.get_srcComponent(),": activating stream",   stream.get_msgId(),  frequency
        else:
            print "System ", stream.get_srcSystem(), stream.get_srcComponent(),": deactivating stream",  stream.get_msgId()

    def requestAllStreams(self):
        if self.master==None:
            return
        print "Requesting all streams from ",  self.master.target_system
        reqMsg=pymavlink.MAVLink_request_data_stream_message(target_system=self.master.target_system, target_component=self.master.target_component, req_stream_id=255, req_message_rate=0, start_stop=0)

        self.master.write(reqMsg.pack(pymavlink.MAVLink(file=0,  srcSystem=self.master.source_system)))
        print "Requesting all parameters",  self.master.target_system
        self.master.param_fetch_all()

        
    def wait_message(self):
        if self.master==None:
            return "", None

        '''wait for a heartbeat so we know the target system IDs'''
        
        
        msg = self.master.recv_msg()
        
        # tag message with this instance of the receiver:
        msg_key=""
        if msg!=None and msg.__class__.__name__!="MAVLink_bad_data":
            msg.mavlinkReceiver=self
            
            msg_key="%s:%s"%(msg.get_srcSystem(),  msg.__class__.__name__)
            self.messages[msg.__class__.__name__]=msg
            self.msg=msg

            #update google earth server:
            if self.earthserver!=None:
                if msg.__class__.__name__=="MAVLink_attitude_message":
                    pitch=getattr(msg, "pitch")
                    roll=getattr(msg, "roll")
                    yaw=getattr(msg, "yaw")
                    self.earthserver.update(tilt=pitch,  roll=roll,  heading=yaw)

                if msg.__class__.__name__=="MAVLink_global_position_int_message":
                    self.earthserver.update(longitude=getattr(msg,  "lon")/10000000.0,  latitude=getattr(msg,  "lat")/10000000.0,  altitude=getattr(msg,  "alt")/1000.0)
                    None;

            if msg.__class__.__name__=="MAVLink_statustext_message":
                print("STATUS ("+str(msg._header.srcSystem)+":"+ str(msg._header.srcComponent)+"): "+getattr(msg,  "text") +"\n")

            msg.key=msg_key
            return msg_key,  msg;
        return "", None;

    def scanForSerials(self):
        return mavutil.auto_detect_serial(['*ttyUSB*',  '*ttyACM*'])

#rcv=MAVlinkReceiver();
# wait for the heartbeat msg to find the system ID
#while True:
#   rcv.wait_message()
#   for m in rcv.messages.keys():
#      print m, rcv.messages[m].get_fieldnames()  


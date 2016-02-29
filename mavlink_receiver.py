#!/usr/bin/env python

'''
test mavlink messages
'''

import sys, time, os
#from curses import ascii
from multiprocessing import   Queue
from threading import Thread
import traceback

from Queue import Empty

# allow import from the parent directory, where mavlink.py is
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pymavlink'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '.'))

#import  mavutil
from pymavlink import mavutil

#from optparse import OptionParser
import argparse

class MAVlinkReceiver:
    def __init__(self, threading=True):
        parser =  argparse.ArgumentParser("mavue.py [options]")

        parser.add_argument("--baudrate", dest="baudrate", type=int,
                  help="master port baud rate", default=115200)
        parser.add_argument("--device", dest="device", default="", help="serial device")
        parser.add_argument("--dialect", dest="dialect", default="auv", help="Mavlink dialect")
        parser.add_argument("--logfile", dest="logfile_raw", default="", help="output log file")
        parser.add_argument("--notimestamps", dest="notimestamps", default="true", help="logfile format")
        parser.add_argument("--source-system", dest='SOURCE_SYSTEM', type=int,
                  default=255, help='MAVLink source system for this GCS')
        (opts, args) = parser.parse_known_args()
        self.opts=opts
        self.serialPorts=self.scanForSerials()
        self.threading=threading
        self.severity = ["EMERGENCY",  "ALERT",  "CRITICAL",  "ERROR",  "WARNING",  "NOTICE",  "INFO",  "DEBUG_0",  "DEBUG_1",  "DEBUG_2",  "DEBUG_3"]
        
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
        self.reopenDevice(opts.device)
        
        #open log file for data logging
        if opts.logfile_raw!="":
            self.master.logfile_raw=open(opts.logfile_raw,  'w',  0)

        self.msg=None;
        self.messages=dict();

        if threading:
            self.messageQueue=Queue()
            self.receiveThread=Thread(target=self.messageReceiveThread)
            self.receiveThread.setDaemon(True)
            self.receiveThread.start()

        self.requestAllStreams()

    def reopenDevice(self, device):
        if self.master is not None:
            self.master.close()
            self.master = None
        try:
            print ""
            print "Initialising as system ",   self.opts.SOURCE_SYSTEM,  "on device",  self.opts.device,  "(baud=",  self.opts.baudrate,  ")"
            print "with MAVlink dialect '",  self.opts.dialect, "'"
            print ""
            self.master = mavutil.mavlink_connection(device, baud=self.opts.baudrate, source_system=self.opts.SOURCE_SYSTEM,  write=True,  dialect=self.opts.dialect,  notimestamps=self.opts.notimestamps)
            self.opts.device = device
        except:
            print "Can't open serial device",  device
            traceback.print_exc()
            self.master = None
    def requestStream(self,  stream,  active,  frequency=0):
        if self.master==None:
            return
        # request activation/deactivation of stream. If frequency is 0, it won't be changed.
        reqMsg=mavutil.mavlink.MAVLink_request_data_stream_message(target_system=stream.get_srcSystem(), target_component=stream.get_srcComponent(), req_stream_id=stream.get_msgId(), req_message_rate=frequency, start_stop=active)

        self.master.write(reqMsg.pack(mavutil.mavlink.MAVLink(file=0,  srcSystem=self.master.source_system)))

        if active:
            print "System ", stream.get_srcSystem(), stream.get_srcComponent(),": activating stream",   stream.get_msgId(),  frequency
        else:
            print "System ", stream.get_srcSystem(), stream.get_srcComponent(),": deactivating stream",  stream.get_msgId()

    def requestAllStreams(self):
        if self.master==None:
            return
        print "Requesting all streams from ",  self.master.target_system,  self.master.target_component
        reqMsg=mavutil.mavlink.MAVLink_request_data_stream_message(target_system=self.master.target_system, target_component=0, req_stream_id=255, req_message_rate=0, start_stop=0)
        self.master.write(reqMsg.pack(mavutil.mavlink.MAVLink(file=0,  srcSystem=self.master.source_system)))

        #time.sleep(0.1)
        print "Requesting all parameters",  self.master.target_system,  self.master.target_component
        self.master.param_fetch_all()

    def sendArmCommand(self):
        #self.master.set_mode(mavutil.mavlink.MAV_MODE_MANUAL_ARMED)
        self.master.mav.set_mode_send(self.master.target_system, mavutil.mavlink.MAV_MODE_MANUAL_ARMED, 0)

    def sendStandbyCommand(self):
        self.master.mav.set_mode_send(self.master.target_system, mavutil.mavlink.MAV_STATE_STANDBY, 0)

    def messageReceiveThread(self):
        while True:
            msg = self.master.recv_msg()
            if msg!=None and msg.__class__.__name__!="MAVLink_bad_data":
               self.messageQueue.put(msg)
            time.sleep(0.0001)


    def messagesAvailable(self):
        return not self.threading or not self.messageQueue.empty()

    def wait_message(self):
        msg = None
        if self.master==None:
            return "", None

        if self.threading:
            try:
                msg=self.messageQueue.get(True,  0.01)
            except Empty:
                return "", None;
        else:
            import serial
            try:
                msg = self.master.recv_msg()
            except serial.SerialException:
                self.reopenDevice(self.opts.device)
                print "Serial connection closed."
        # tag message with this instance of the receiver:
        msg_key=""
        if msg!=None and msg.__class__.__name__!="MAVLink_bad_data":
            msg.mavlinkReceiver=self

            msg_key="%s/%s:%s"%(msg.get_srcSystem(), msg.get_srcComponent(),  msg.__class__.__name__)
            self.messages[msg.__class__.__name__]=msg
            self.msg=msg

            if msg.__class__.__name__.startswith("MAVLink_raw_data_stream"):
                msg_key="%s:%s:%s"%(msg.get_srcSystem(),  msg.__class__.__name__, msg.stream_id)
                block_size=len(msg.values)
                #assemble multi-packet blocks if packets_per_block is greater than 0:
                if msg.packets_per_block>0:
                    all_values=[0 for x in range(0, msg.packets_per_block*block_size)]

                    if msg_key in self.messages:
                        all_values=self.messages[msg_key].values

                    for i in range(0, block_size):
                        all_values[i+ msg.packet_id*block_size]=msg.values[i]

                    msg.values=all_values

                self.messages[msg_key]=msg
                #if msg.packet_id!=msg.packets_per_block-1: # return empty if message not complete yet
                #    return "", None; 

            if msg.__class__.__name__=="MAVLink_statustext_message":
                print(self.severity[getattr(msg,  "severity")]+" "+str(msg._header.srcSystem)+":"+ str(msg._header.srcComponent)+"): "+getattr(msg,  "text") +"\n")

            msg.key=msg_key
            return msg_key,  msg;
        return "", None;

    def scanForSerials(self):
        print "detecting serial ports..."
        return mavutil.auto_detect_serial(['*ttyUSB*',  '*ttyACM*', '*tty.usb*'])


if __name__ == '__main__':
    rcv=MAVlinkReceiver();
    log_counter=1
    # wait for the heartbeat msg to find the system ID
    while True:
        msg_key, msg=rcv.wait_message()
        if msg_key!='':
        #	print msg_key
        #if msg.__class__.__name__=="MAVLink_global_position_int_message":
        #    print getattr(msg,  "lon")/10000000.0,  getattr(msg,  "lat")/10000000.0,  getattr(msg,  "alt")/1000.0
            if msg.__class__.__name__=="MAVLink_statustext_message" and msg._header.srcComponent==10 and getattr(msg,  "text").startswith("adding task LED"):
                if rcv.opts.logfile_raw!="":
                    new_log=rcv.opts.logfile_raw + "%04d" % log_counter
                    log_counter+=1
                    print "New powerup detected - starting new output logfile:", new_log
                    oldfile=rcv.master.logfile_raw
                    rcv.master.logfile_raw=open(new_log,  'w',  0)


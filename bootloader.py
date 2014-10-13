from pyqtgraph.Qt import QtGui, QtCore
from gui_elements import *

from pymavlink.dialects.v10 import dbgextensions as mb
from pymavlink import pymavlink


class Bootloader(QtGui.QDialog):
    def __init__(self,  parent,  mavlinkReceiver):
        QtGui.QDialog.__init__(self)
        self.setWindowTitle("Bootloader")
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        self.mavlinkReceiver=mavlinkReceiver
        self.parent=parent
        self.messageCounter=0

        self.actionButtons=HorizontalBar(parent=self)
        self.actionButtons.add(QtGui.QPushButton("Discover"),  "clicked()",  self.discoverDevices)
        self.actionButtons.add(QtGui.QPushButton("Get Info"),  "clicked()",  self.getDeviceInfo)
        self.actionButtons.add(QtGui.QPushButton("Erase Flash"),  "clicked()",  self.dummyAction)
        self.actionButtons.add(QtGui.QPushButton("Read Flash"),  "clicked()",  self.dummyAction)
        self.actionButtons.add(QtGui.QPushButton("Write Flash"),  "clicked()",  self.dummyAction)
        self.actionButtons.add(QtGui.QPushButton("Reset"),  "clicked()",  self.sendResetCommand)
        self.layout.addWidget(self.actionButtons)
        

    def dummyAction(self):
        None;
        
    def discoverDevices(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255,  self.messageCounter,   mb.BOOT_INITIATE_SESSION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def getDeviceInfo(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255,  self.messageCounter,   mb.BOOT_GET_PROCESSOR_INFORMATION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1


    def sendResetCommand(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255, self.messageCounter, mb.BOOT_RESET, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

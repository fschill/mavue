from pyqtgraph.Qt import QtGui, QtCore
from gui_elements import *
from abstractparameters import *

from pymavlink.dialects.v10 import dbgextensions as mb
from pymavlink import pymavlink
from plugins import Plugin
import intelhex

from multiprocessing import Process,  Queue
import time

class DeviceActions(ItemWithParameters,  Plugin):
    def __init__(self,  name=None,  mavlinkInterface=None,  sysid=255,  compid=255,  boardname="",    **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.messageCounter=0
        self.mavlinkReceiver=mavlinkInterface
    
        self.sysid=sysid
        self.compid=compid
        self.hexFile=None
        
        if name==None:
            self.name=TextParameter(parent=self, name="Description", value="(%i:%i) %s"%(sysid,  compid,  boardname))
        else:
            self.name=TextParameter(parent=self, name="Description", value=name,  editable=False)
        
        self.processorInfo=dict()
        self.processorInfo[mb.BOOT_PROCESSOR_MODEL]=TextParameter(parent=self, name="Processor Model", value=0,  editable=False,  formatString="{:02X}")
        self.processorInfo[mb.BOOT_PROCESSOR_ID]=TextParameter(parent=self, name="Processor ID", value=0,  editable=False,   formatString=" {:02X}")
        self.processorInfo[mb.BOOT_PAGE_SIZE]=TextParameter(parent=self, name="Flash page size", value=0,  editable=False,  formatString="{:d}")
        self.processorInfo[mb.BOOT_FLASH_SIZE]=TextParameter(parent=self, name="Flash size", value=0,  editable=False,  formatString="{:d}")
        self.processorInfo[mb.BOOT_RAM_SIZE]=TextParameter(parent=self, name="RAM size", value=0,  editable=False,  formatString="{:d}")
        
        self.getInfo=ActionParameter(parent=self,  name='Get Info',  callback=self.getDeviceInfo)
        self.flashFile=FileParameter(parent=self,  name="HEX file",  fileSelectionPattern="HEX files (*.hex)",  callback=self.openHexFile)
        self.readFlash=ActionParameter(parent=self,  name='Read Flash',  callback=self.readFlash)
        self.writeFlash=ActionParameter(parent=self,  name='Write Flash',  callback=self.writeFlash)
        self.transferProgress=ProgressParameter(parent=self,  name='Transfer',  min=0,  max=100,  value=0)
        self.verifyFlash=ActionParameter(parent=self,  name='Verify Flash',  callback=self.verifyFlash)
        self.reset=ActionParameter(parent=self,  name='Reset',  callback=self.sendResetCommand)

        self.parameters=[self.name,  
                                    self.getInfo,  
                                    self.processorInfo[mb.BOOT_PROCESSOR_MODEL],  
                                    self.processorInfo[mb.BOOT_PROCESSOR_ID], 
                                    self.processorInfo[mb.BOOT_PAGE_SIZE], 
                                    self.processorInfo[mb.BOOT_FLASH_SIZE], 
                                    self.processorInfo[mb.BOOT_RAM_SIZE], 
                                    self.flashFile, 
                                    self.readFlash,  
                                    self.writeFlash, 
                                    self.verifyFlash,
                                    self.transferProgress, 
                                    self.reset]
                                    
        #set flash file for testing:
        self.flashFile.updateValue("/home/felix/Hydromea/AUV_Software/Bootloader/Debug/MavBoot.hex")
        
        
    # this method will be called for each MavBoot message
    def run(self,  message):
        if message.__class__.__name__.startswith("MAVLink_bootloader_cmd_message"):
            #print(message.command,  message.param_address,  message.param_length)
            #remove ACK flag from command
            base_command=message.command & 0x3f
            if base_command in self.processorInfo.keys():
                print ("updating processor info",  self.processorInfo[base_command].name)
                self.processorInfo[base_command].updateValue(message.param_address)
            if base_command==mb.BOOT_WRITE_TO_BUFFER:
                self.ack_msg_queue.put(message)

        if message.__class__.__name__.startswith("MAVLink_bootloader_data_message"):
            print(message.command,  message.base_address,  message.data_length,  message.data)
            #remove ACK flag from command
            base_command=message.command & 0x3f
            if base_command in self.processorInfo.keys():
                print ("updating processor info",  self.processorInfo[base_command].name)
                self.processorInfo[base_command].updateValue(message.data[:message.data_length])


    def getDeviceInfo(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter,   mb.BOOT_GET_PROCESSOR_INFORMATION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def openHexFile(self,  fileParameter):
        None

    def readFlash(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter,   mb.BOOT_READ_MEMORY, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def writeFlash(self):    
        filename=self.flashFile.value
        
        if filename!=None and len(filename)>0:
            try:
                self.hexFile=open(filename)
            except:
                print "file not found!"
                return
            self.hexObject=intelhex.IntelHex(self.hexFile)
            print ("successfully opened "+filename)
            print   (self.hexObject.maxaddr()-self.hexObject.minaddr())/1024,  "kbytes"

        self.ack_msg_queue=Queue()
        self.transferThread=Thread(target=self.writeFlashThread)
        self.transferThread.start()
        #self.writeFlashThread()

    # thread for memory transfers, connected to received ACK messages via a queue
    def writeFlashThread(self):
        startAddress=self.hexObject.minaddr()
        endAddress=self.hexObject.maxaddr()
        pageSize=int(self.processorInfo[mb.BOOT_PAGE_SIZE].value)
        
        binsize=endAddress-startAddress
        
        startTime=time.time()
        data=range(0,  32)
        print "%0.2X - %0.2X" %(self.hexObject.minaddr(),  self.hexObject.maxaddr()),  pageSize
        addr=startAddress
        while addr<endAddress:
            # break up page into 32 byte blocks
            pageCounter=0
            sentMessages=[]
            while pageCounter<pageSize/32 and addr<endAddress:
                length=min(32,  endAddress-addr)
                msg = mb.MAVLink_bootloader_data_message(self.sysid, self.compid,   self.messageCounter,  mb.BOOT_WRITE_TO_BUFFER,  addr,  length, data)
                self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
                
                # append transmitted message IDs to list for checking the acknowledgements
                sentMessages.append(self.messageCounter)
                self.messageCounter+=1
                pageCounter+=1
                addr+=32
                # check if we received all acknowledgements
                while len(sentMessages)>0:
                    # wait for acknowledgement with a timeout of 0.5 seconds
                    try:
                        receivedAck=self.ack_msg_queue.get(True,  0.5)
                    except:
                        print "Bootloader not responding! aborting transfer"
                        self.transferProgress.updateValue(value=startAddress,  min=startAddress,  max=endAddress)
                        return
                    recId=receivedAck.session_message_counter
                    if recId in sentMessages:
                        sentMessages.remove(recId)
                    else:
                        print "received out-of-order session_message_counter! Aborting."
                        self.transferProgress.updateValue(value=startAddress,  min=startAddress,  max=endAddress)
                        return
                
            #update progress bar
            self.transferProgress.updateValue(value=addr+length,  min=startAddress,  max=endAddress)
        finishTime=time.time()

        print "transfer complete." ,  finishTime-startTime,  "seconds (",  binsize/(finishTime-startTime)/1000.0,  "kbytes/sec)"
        self.transferProgress.updateValue(value=endAddress,  min=startAddress,  max=endAddress)
            


    def verifyFlash(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,   mb.BOOT_READ_MEMORY, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1


    def sendResetCommand(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter, mb.BOOT_RESET, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((pymavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

        
class Bootloader(QtGui.QDialog,  Plugin):
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
        self.actionButtons.add(QtGui.QPushButton("Reset all"),  "clicked()",  self.sendResetCommand)
        self.layout.addWidget(self.actionButtons)

        self.deviceList=ListWidget(itemlist=[],  title="Devices",  itemclass=DeviceActions,  mavlinkInterface=self.mavlinkReceiver,  sysid=1,  compid=1,  on_select_cb=DeviceActions.getDeviceInfo)
        self.layout.addWidget(self.deviceList)
        
        self.resize(600,600)

        

    #overwrite inherited methods for Plugin:
    def filter(self,  message):
        # only respond to MavBoot messages
        return message.__class__.__name__.startswith("MAVLink_bootloader")

    # this method will be called for each MavBoot message
    def run(self,  message):
        if message.__class__.__name__.startswith("MAVLink_bootloader"):            
            deviceActions=self.deviceList.addItem(addExistingItems=False, mavlinkInterface=self.mavlinkReceiver,   sysid=message._header.srcSystem,  compid=message._header.srcComponent)
            if deviceActions!=None:
                deviceActions.run(message)
        #print(message.__class__.__name__)
        # update property widget
        self.deviceList.propertyWidget.update()
        
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

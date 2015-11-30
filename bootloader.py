from pyqtgraph.Qt import QtGui
from gui_elements import *
from abstractparameters import *

from pymavlink import mavutil
from plugins import Plugin
import intelhex

from Queue import  Queue
from Queue import Empty
import time
import sys
import traceback
from pymavlink.generator.mavcrc import x25crc


class PageBlock:
    def __init__(self,  addr=0,  data=[],  length=0, retries = 3):
        self.addr=addr
        self.data=data
        self.length=length
        self.checksum = x25crc((bytearray(data)))
        self.messageCounter=0
        self.ack=0
        self.retries = retries

    def getCRC(self):
        return self.checksum.crc

    def padChecksum(self, total_length, value):
        for i in range(self.length, total_length):
            self.checksum.accumulate([value])

class DeviceActions(ItemWithParameters,  Plugin):
    def __init__(self,  name=None,  mavlinkInterface=None,  sysid=255,  compid=255,  boardname="",    **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.messageCounter=0
        self.mavlinkReceiver=mavlinkInterface
    
        self.ack_msg_queue=None
        self.sysid=sysid
        self.compid=compid
        self.hexFile=None
        
        if name==None:
            self.name=TextParameter(parent=self, name="Description", value="(%i:%i) %s"%(sysid,  compid,  boardname))
        else:
            self.name=TextParameter(parent=self, name="Description", value=name,  editable=False)
        
        self.processorInfo=dict()
        self.processorInfoLength=dict()
        self.processorInfo[mb.BOOT_PROCESSOR_MODEL]=TextParameter(parent=self, name="Processor Model", value=0,  editable=False,  formatString="0x{:02X}")
        self.processorInfo[mb.BOOT_PROCESSOR_ID]=TextParameter(parent=self, name="Processor ID", value=0,  editable=False,   formatString=" {:02X}")
        self.processorInfo[mb.BOOT_PAGE_SIZE]=TextParameter(parent=self, name="Flash page size", value=0,  editable=False,  formatString="{:d}")
        self.processorInfo[mb.BOOT_FLASH_ADDRESS]=TextParameter(parent=self, name="Flash address", value=0,  editable=False,  formatString="0x{:02X}")
        self.processorInfoLength[mb.BOOT_FLASH_ADDRESS]=TextParameter(parent=self, name="Flash size", value=0,  editable=False,  formatString="{:d}")
        self.processorInfo[mb.BOOT_RAM_ADDRESS]=TextParameter(parent=self, name="RAM address", value=0,  editable=False,  formatString="0x{:02X}")
        self.processorInfoLength[mb.BOOT_RAM_ADDRESS]=TextParameter(parent=self, name="RAM size", value=0,  editable=False,  formatString="{:d}")
        self.processorInfo[mb.BOOT_PROTECTED_BOOT_AREA]=TextParameter(parent=self, name="Application address", value=0,  editable=False,  formatString="0x{:02X}")
        self.processorInfoLength[mb.BOOT_PROTECTED_BOOT_AREA]=TextParameter(parent=self, name="Bootloader size", value=0,  editable=False,  formatString="{:d}")
        
        self.parallelPackets = NumericalParameter(parent=self, name="transmit parallel packets", value=12,  min=1,  max=15, step=1,  editable=True)
        self.sendInterval = NumericalParameter(parent=self, name="send interval", value=8,  min=0,  max=50,  step=1,  editable=True)

        self.getInfo=ActionParameter(parent=self,  name='Get Info',  callback=self.getDeviceInfo)
        self.flashFile=FileParameter(parent=self,  name="HEX file",  fileSelectionPattern="HEX files (*.hex)",  callback=self.openHexFile)
        self.readFlash=ActionParameter(parent=self,  name='Read Flash',  callback=self.readFlash)
        self.writeFlash=ActionParameter(parent=self,  name='Write Flash',  callback=self.writeFlash)
        self.verifyFlash=ActionParameter(parent=self,  name='Verify Flash',  callback=self.verifyFlash)
        self.startApp=ActionParameter(parent=self,  name='start Application',  callback=self.startApplication)
        self.transferProgress=ProgressParameter(parent=self,  name='Transfer',  min=0,  max=100,  value=0)
        self.reset=ActionParameter(parent=self,  name='Reset',  callback=self.sendResetCommand)


        self.parameters=[self.name,  
                                    self.getInfo,  
                                    #self.processorInfo[mb.BOOT_PROCESSOR_MODEL],  
                                    #self.processorInfo[mb.BOOT_PROCESSOR_ID], 
                                    #self.processorInfo[mb.BOOT_PAGE_SIZE], 
                                    #self.processorInfo[mb.BOOT_FLASH_ADDRESS], 
                                    #self.processorInfoLength[mb.BOOT_FLASH_ADDRESS], 
                                    #self.processorInfo[mb.BOOT_RAM_ADDRESS], 
                                    #self.processorInfoLength[mb.BOOT_RAM_ADDRESS], 
                                    #self.processorInfo[mb.BOOT_PROTECTED_BOOT_AREA],  
                                    #self.processorInfoLength[mb.BOOT_PROTECTED_BOOT_AREA], 
                                    self.parallelPackets, 
                                    self.sendInterval, 
                                    self.flashFile, 
                                    #self.readFlash,  
                                    self.writeFlash, 
                                    #self.verifyFlash,
                                    self.startApp, 
                                    self.transferProgress, 
                                    self.reset]
                                    
        #set flash file for testing:
        #self.flashFile.updateValue("/home/felix/Projects/maveric/Code/Maveric_myCopter/Debug_Linux/Maveric_myCopter_linux.hex")
        self.ack_msg_queue=Queue()

        
    # this method will be called for each MavBoot message
    def run(self,  message):
        if message.content().__class__.__name__.startswith("MAVLink_bootloader_cmd"):
            
            #remove ACK flag from command
            base_command=message.content().command & 0x3f
            #print("Ack:", base_command,  message.param_address,  message.param_length)
            if base_command==mb.BOOT_INITIATE_SESSION:
                print "Discovered device:" , message.content()._header.srcSystem,  message.content()._header.srcComponent
                self.getDeviceInfo()
                
            if base_command in self.processorInfo.keys():
                print ("updating processor info",  self.processorInfo[base_command].name)
                self.processorInfo[base_command].updateValue(message.content().param_address)
                if base_command in self.processorInfoLength.keys():
                    self.processorInfoLength[base_command].updateValue(message.content().param_length)
            if self.ack_msg_queue!=None:
                #print "put in queue"
                self.ack_msg_queue.put(message.content())
            #else:
            #    print "no message queue!!"

        if message.content().__class__.__name__.startswith("MAVLink_bootloader_data"):
            print(message.content().command,  message.content().base_address,  message.content().data_length,  message.content().data)
            #remove ACK flag from command
            base_command=message.content().command & 0x3f
            if base_command in self.processorInfo.keys():
                print ("updating processor info",  self.processorInfo[base_command].name)
                self.processorInfo[base_command].updateValue(message.content().data[:message.content().data_length])


    #def sendCommand(self):

    def getDeviceInfo(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter,   mb.BOOT_GET_PROCESSOR_INFORMATION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def openHexFile(self,  fileParameter):
        None

    def readFlash(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter,   mb.BOOT_READ_MEMORY, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
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

        # flush queue 
        while not  self.ack_msg_queue.empty():
            self.ack_msg_queue.get()
        #self.writeFlashThread()
        self.transferThread=Thread(target=self.writeFlashThread)
        self.transferThread.start()

    def loadPages(self):
        startAddress=self.hexObject.minaddr()
            
        endAddress=self.hexObject.maxaddr()
        pageSize=int(self.processorInfo[mb.BOOT_PAGE_SIZE].value)
        
        binaryData=self.hexObject.tobinarray(startAddress,  endAddress)
        addr=startAddress
        
        print "%0.2X - %0.2X" %(startAddress,  endAddress),  pageSize
        addr=startAddress
        if addr<self.processorInfo[mb.BOOT_PROTECTED_BOOT_AREA].value:
            addr=self.processorInfo[mb.BOOT_PROTECTED_BOOT_AREA].value
            print "skipping boot area to %0.2X" %  addr
            
        pages = []
        while addr<endAddress:
            pageAddress=addr - (addr%pageSize)
            data = binaryData[pageAddress - startAddress:min(pageAddress -startAddress + pageSize, endAddress)]
            currentPage = PageBlock(pageAddress, data, len(data))
            # erased flash pages are filled with 0xFF which will be included in the bootloader CRC
            currentPage.padChecksum(pageSize, 0xFF)
            pages.append(currentPage)
            addr += pageSize
        return pages

    def verifyPageCRC(self,  currentPage):
        pageSize=int(self.processorInfo[mb.BOOT_PAGE_SIZE].value)

        # send a request for a flash page CRC:
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,  mb.BOOT_VERIFY_MEMORY,  0,  currentPage.addr, pageSize)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        try:
            receivedAck=self.ack_msg_queue.get(True,  1.0)
            if receivedAck.command == mb.BOOT_VERIFY_MEMORY | mb.ACK_FLAG:
                if receivedAck.param_length == currentPage.getCRC():
                    return True
                else:
                    return False
            else:
                print "Wrong ACK to VERIFY_MEMORY command",  receivedAck.CMD
                return False
        except Empty:
            print "Failed communication during verify"
            return False
        except:
            print  sys.exc_info()[0],  traceback.format_exc()
            #self.ack_msg_queue=None
            return False


    # thread for memory transfers, connected to received ACK messages via a queue
    def writeFlashThread(self):
        repeat_tries=5
        
        startAddress=self.hexObject.minaddr()
        endAddress=self.hexObject.maxaddr()
        pageSize=int(self.processorInfo[mb.BOOT_PAGE_SIZE].value)
        
        binsize=endAddress-startAddress
        
        pageList = self.loadPages()
        
        startTime=time.time()

        for i in range(0, 3):
           #enter programming mode
            msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,  mb.BOOT_START_REPROGRAM,  0,  0, 0)
            self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))

            try:
                receivedAck=self.ack_msg_queue.get(True,  1.0)
                if receivedAck.command!= mb.BOOT_START_REPROGRAM | mb.ACK_FLAG:
                    print "Wrong ACK to START_REPROGRAM",  receivedAck.CMD
                if receivedAck.error_id!=0:
                    print "error entering programming mode",  receivedAck.error_id
                print "entering programming mode"
                break
            except Empty:
                print "Failed to enter programming mode"
            except:
                print  sys.exc_info()[0],  traceback.format_exc()
                #self.ack_msg_queue=None
                return

        while len(pageList) > 0:
            # break up page into 32 byte blocks
            currentPage = pageList[0]
    
            pageVerified = self.verifyPageCRC(currentPage)
            #pageVerified = False
            #collect all blocks for the current page:
            blocks=[]
            address_offset = 0
            if pageVerified:
                #print "skipping: page verified"
                pageList=pageList[1:]

            else:
                while (address_offset  < currentPage.length):
                    length=min(32,  currentPage.length - address_offset)
                    data = currentPage.data[address_offset:address_offset+length]
                    while len(data)<32:
                        data.append(0xff)

                    new_block=PageBlock(currentPage.addr + address_offset,  data, length)
                    blocks.append(new_block)
                    address_offset+=32
            
                while len(blocks)>0:
                    sentMessages=[]
                    for b in blocks:
                        b.messageCounter=self.messageCounter
                        #print "sending ",   "%02X"% b.addr
                        msg = mb.MAVLink_bootloader_data_message(self.sysid, self.compid,   b.messageCounter,  mb.BOOT_WRITE_TO_BUFFER,  b.addr,  b.length, b.data)
                        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
                        # append transmitted message IDs to list for checking the acknowledgements
                        sentMessages.append(self.messageCounter)
                        self.messageCounter+=1
                        time.sleep(self.sendInterval.getValue()/1000.0)
                        # check how many packets to send before waiting for acks:
                        if len(sentMessages)>=int(self.parallelPackets.getValue()):
                            break;
                    #print "sent:",   ["%i"%b for b in sentMessages]
                    # check if we received all acknowledgements
                    while len(sentMessages)>0:
                        # wait for acknowledgement with a timeout of 0.5 seconds
                       # print "waiting for ack"
                        try:
                            receivedAck=self.ack_msg_queue.get(True,  0.1)
                            recId=receivedAck.session_message_counter
                            #print "recv: %02X"%receivedAck.param_address
                            if recId in sentMessages:  # ack with correct sequence received?
                                sentMessages.remove(recId)
                            else:
                                print "received out-of-order session_message_counter! Aborting."
                                self.transferProgress.updateValue(value=startAddress,  min=startAddress,  max=endAddress)
                                return

                            ackBlock=None
                            #find corresponding block
                            for b in blocks:
                                if b.messageCounter==receivedAck.session_message_counter:
                                    ackBlock=b
                                
                            if receivedAck.error_id!=0:
                                print "write error:",  receivedAck.error_id,  "ret. addr:",  "%02X"%receivedAck.param_address
                                repeat_tries-=1
                            if receivedAck.param_length!=int(ackBlock.getCRC()):
                                print "checksum error:",  receivedAck.param_length,  "vs",  ackBlock.getCRC()
                                repeat_tries-=1
                            # ACK is fine - progress to next block
                            #print "."
                            
                            blocks.remove(ackBlock)
                            repeat_tries=5
                        except Empty:
                            print "Bootloader not responding! Addr: %02X ,  retrying:"%currentPage.addr,  repeat_tries,  ["%02X"%b.addr for b in blocks]
                            repeat_tries-=1
                            break

                            #self.transferProgress.updateValue(value=startAddress,  min=startAddress,  max=endAddress)
                            #return
                        except:  # general error
                            print  sys.exc_info()[0],  traceback.format_exc()
                            #self.ack_msg_queue=None
                            return

                    if repeat_tries<=0:
                        print "Aborting."
                        #self.ack_msg_queue=None
                        return
                
                #print "writing page %02X"%  currentPage.addr
                # page complete - send write to flash command
                msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,  mb.BOOT_WRITE_BUFFER_TO_FLASH,  0,  currentPage.addr, pageSize)
                self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
                try:
                    receivedAck=self.ack_msg_queue.get(True,  0.5)
                    
                    if receivedAck.command!= mb.BOOT_WRITE_BUFFER_TO_FLASH | mb.ACK_FLAG:
                        print "error writing flash page - out of order ACK",  receivedAck.CMD
                        #self.ack_msg_queue=None
                        return
                    if receivedAck.error_id!=0:
                        print "error writing flash page:",  receivedAck.error_id,  "%02X"%receivedAck.param_address,  "%02X"% currentPage.addr
                        #self.ack_msg_queue=None
                        return
                    if receivedAck.param_length!=currentPage.getCRC():
                        print "flash page checksum error:",   "%02X"%receivedAck.param_length,  "%02X"% currentPage.getCRC()
                    # page write successful
                    #print "success writing flash page:",  "remote %02X"%receivedAck.param_address,  "local %02X"% currentPage.addr, "chk %02X"%receivedAck.param_length,  " (%02X)"% currentPage.getCRC()                
                    pageList=pageList[1:]

                except Empty:
                    print "Flash write: Bootloader not responding! trying again..."
                    self.transferProgress.updateValue(value=startAddress,  min=startAddress,  max=endAddress)
                    #self.ack_msg_queue=None
                    
                except:
                    print  sys.exc_info()[0],  traceback.format_exc()
                    #self.ack_msg_queue=None
                    return


            #update progress bar
            self.transferProgress.updateValue(value=currentPage.addr,  min=startAddress,  max=endAddress)
        finishTime=time.time()

        self.transferProgress.updateValue(value=endAddress,  min=startAddress,  max=endAddress)
        
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,  mb.BOOT_END_REPROGRAM,  0,  0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))

        print "transfer complete." ,  finishTime-startTime,  "seconds (",  binsize/(finishTime-startTime)/1000.0,  "kbytes/sec)"
        #self.ack_msg_queue=None


    def verifyFlash(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,   self.messageCounter,   mb.BOOT_READ_MEMORY, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def startApplication(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter, mb.BOOT_START_APPLICATION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1


    def sendResetCommand(self):    
        msg = mb.MAVLink_bootloader_cmd_message(self.sysid, self.compid,  self.messageCounter, mb.BOOT_RESET, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

        
class Bootloader(QtGui.QDialog,  Plugin):

    def __init__(self,  parent,  mavlinkReceiver):
        from pymavlink.dialects.v10 import auv as mb
        global mb
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
        return message.content().__class__.__name__.startswith("MAVLink_bootloader")

    # this method will be called for each MavBoot message
    def run(self,  message):
        if message.content().__class__.__name__.startswith("MAVLink_bootloader"):
            #print(message.__class__.__name__)
            deviceActions=self.deviceList.addItem(addExistingItems=False, mavlinkInterface=self.mavlinkReceiver,   sysid=message.content()._header.srcSystem,  compid=message.content()._header.srcComponent)
            if deviceActions!=None:
                deviceActions.run(message)
        
        # update property widget
        self.deviceList.propertyWidget.update()
        
    def dummyAction(self):
        None;
        
    def discoverDevices(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255,  self.messageCounter,   mb.BOOT_INITIATE_SESSION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1

    def getDeviceInfo(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255,  self.messageCounter,   mb.BOOT_GET_PROCESSOR_INFORMATION, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1


    def sendResetCommand(self):    
        msg = mb.MAVLink_bootloader_cmd_message(255, 255, self.messageCounter, mb.BOOT_RESET, 0, 0, 0)
        self.mavlinkReceiver.master.write(msg.pack((mavutil.mavlink.MAVLink(file=0,  srcSystem=self.mavlinkReceiver.master.source_system))))
        self.messageCounter+=1
        
    def closeEvent(self,  event):
        self.parent.updater.plugin_manager.active_plugins.remove(self)
        
        print "closing bootloader"

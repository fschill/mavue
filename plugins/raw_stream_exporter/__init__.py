import plugins
from math import *
from pymavlink import mavutil

EARTH_RADIUS = 6378137.0

class Raw_Stream_Exporter(plugins.Plugin):
    def __init__(self,  data_range = [0, 0]):
        self.last_pos=(0, 0, 0)
        self.raw_data_outfile=  open ("raw_data_out.csv",  "w")

    def filter(self,  message):
        filter_result = message.get_msgType().startswith("RAW_DATA_STREAM") or message.get_msgType()=="GLOBAL_POSITION_INT"
        return filter_result

             
    def run(self,  message): 
        if message.get_msgType()=="GLOBAL_POSITION_INT" and message.get_srcSystem()==10:
            lat=message.getValueByName("lat").content()/10000000.0
            lon=message.getValueByName("lon").content()/10000000.0
            heading = float(message.getValueByName("hdg").content())
            self.last_pos = (lat,  lon,  heading)
            #print "last pos:",  self.last_pos

        if message.get_msgType().startswith("RAW_DATA_STREAM"):
            stream_id = message.getValueByName("stream_id").content()
            msg=message.content()
            self.raw_data_outfile.write(str(stream_id)+",\t%f,\t%f,\t%f\t"%(self.last_pos)+str(msg.time_boot_ms)+",\t"+"". join(str(x)+",\t" for x in msg.values) +"\n")



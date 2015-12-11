import plugins
from math import *
from pymavlink import mavutil

EARTH_RADIUS = 6378137.0

class gps_tool(plugins.Plugin):
    def __init__(self,  data_range = [0, 0]):
        self.start_pos=None
        self.data_range=data_range

        self.out_msg= mavutil.mavlink.MAVLink_message(1000,  "Kalman filter")
        self.out_msg.key="%s:%s"%(self.out_msg.get_srcSystem(),  self.out_msg.__class__.__name__)
        self.out_msg._fieldnames=["local_pos_x", "local_pos_y","distance"]

    def filter(self,  message):
        return message.name()=="GPS_RAW_INT"

             
    def run(self,  message): 
        lat=message.getValueByName("lat").content()/10000000.0
        lon=message.getValueByName("lon").content()/10000000.0
        if self.start_pos is None:
            self.start_pos = [lat,  lon]
        small_radius = cos(lat*pi/180.0)*EARTH_RADIUS
        local_pos_x = sin((lat-self.start_pos[0])*pi/180.0) * EARTH_RADIUS
        local_pos_y = sin((lon-self.start_pos[1])*pi/180.0) * small_radius
        
        dist = sqrt(local_pos_x**2 + local_pos_y**2)
        self.out_msg.local_pos_x = local_pos_x
        self.out_msg.local_pos_y = local_pos_y
        self.out_msg.distance= dist
        message.updateContent(self.out_msg)
        #return self.out_msg
        
class Named_Value_Scaler(plugins.Plugin):
    
    def __init__(self):
        self.out_msg= mavutil.mavlink.MAVLink_message(1000,  "Kalman filter")
        self.out_msg.key="%s:%s"%(self.out_msg.get_srcSystem(),  self.out_msg.__class__.__name__)
        self.out_msg._fieldnames=["distance"]        
    
    def filter(self,  message):
        return message.name()=="TOAus"

    def run(self,  message): 
        toa = message.getValueByName("value").content()
        self.out_msg.distance = toa / 1000000.0 * 1457.0
        message.updateContent(self.out_msg)

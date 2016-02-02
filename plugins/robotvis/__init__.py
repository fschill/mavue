import plugins
from math import *
from pymavlink import mavutil


class robotvis(plugins.Plugin):
    def __init__(self,  model_file="",  data_range = [0, 0]):
        self.model_file=model_file
        self.data_range=data_range

    def filter(self,  message):
        return message.name()=="GPS_GLOBAL_POSITION_INT" or message.name()=="ATTITUDE"

             
    def run(self,  message): 
        if message.name()=="GPS_GLOBAL_POSITION_INT":
            lat=message.getValueByName("lat").content()/10000000.0
            lon=message.getValueByName("lon").content()/10000000.0
        

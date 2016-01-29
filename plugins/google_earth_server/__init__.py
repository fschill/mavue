'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


#!/usr/bin/env python
 
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from thread import start_new_thread
import math
import plugins

KmlHeader = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">"""

def radianToPosDegree(alpha):
    while alpha<0.0: alpha+=2.0*math.pi
    while alpha>2.0*math.pi: alpha-=2.0*math.pi
    return alpha*180.0/math.pi

def radianToSymDegree(alpha):
    while alpha<-math.pi: alpha+=2.0*math.pi
    while alpha>math.pi: alpha-=2.0*math.pi
    return alpha*180.0/math.pi

class Trace:
    def __init__(self, name="Track", msg_node=None,  longitude=6.566044801857777,  latitude=46.51852236174565,  altitude=440,  heading=0.0,  tilt=0.0,  roll=0.0,  data_range = [-1000, 0],  color="red_line"):
        self.name=name
        self.heading=radianToPosDegree(heading)
        self.tilt=radianToPosDegree(90+tilt)
        self.roll=radianToSymDegree(-roll)
        self.altitude=altitude
        self.longitude=longitude
        self.latitude=latitude
        self.trace=[]
        self.color=color
        self.source_msg_node=msg_node
        self.data_range=data_range

    def update(self,  longitude=None,  latitude=None,  altitude=None,  heading=None,  tilt=None,  roll=None):
        if heading!=None: self.heading=radianToPosDegree(heading)
        if tilt!=None: self.tilt=radianToPosDegree(math.pi/2.0+tilt)
        if roll!=None: self.roll=radianToSymDegree(-roll)
        if altitude!=None: self.altitude=altitude
        if longitude!=None: self.longitude=longitude
        if latitude!=None: self.latitude=latitude
        if longitude!=None and latitude!=None:
            self.trace.append([self.longitude,  self.latitude,  self.altitude])
            
    def updateFromSource(self):
        long_trace = self.source_msg_node.getValueByName("lon").getTrace(self.data_range)
        lat_trace = self.source_msg_node.getValueByName("lat").getTrace(self.data_range)
        alt_trace = self.source_msg_node.getValueByName("alt").getTrace(self.data_range)
        self.trace = [[lon/10000000.0,  lat/10000000.0,  alt/1000.0] for lon, lat, alt in zip(long_trace,  lat_trace, alt_trace)]
        #print self.source_msg_node.getMavlinkKey(),  self.trace[-1]
        
#Create custom HTTPRequestHandler class
class KmlHTTPRequestHandler(BaseHTTPRequestHandler):
        
    def makeView(self, name,  longitude, latitude, altitude, heading, tilt, roll):
       return "<Placemark> <name>%s</name>\
        <Camera> <longitude> %f</longitude> \
        <latitude>%f</latitude> \
        <altitude>%f</altitude> \
        <heading>%f</heading> \
        <tilt>%f</tilt> \
        <roll>%f</roll> \
        <altitudeMode>absolute</altitudeMode> \
        </Camera></Placemark>" % (name, longitude, latitude, altitude, heading, tilt, roll)

    def makeTrace(self, name,  color,  trace):
        coordinate_string =""
        strace=trace
        if len(trace)>2000:
            divider=int(len(trace)/2000)
            strace=trace[0:-1:divider]
            print len(trace),  len(strace)
        for p in strace:
            coordinate_string+="%f,%f,%f "%(p[0],  p[1],  p[2])
        return\
    """
<Placemark>
<name>%s</name>
<styleUrl>#%s</styleUrl>
<LineString>
<tessellate>1</tessellate>
<coordinates>
%s 
</coordinates>
</LineString>
</Placemark>"""% (name, color,   coordinate_string)

    def makeModel(self, name,  longitude, latitude, altitude, heading, tilt, roll) :
    	return \
"""<Placemark><name>"%s"</name><styleUrl>#m_ylw-pushpin</styleUrl>
<Model id="model1"> 
<Location><longitude> %f</longitude> <latitude>%f</latitude> <altitude>%f</altitude> </Location>
<Orientation><heading>%f</heading> <tilt>%f</tilt> <roll>%f</roll> </Orientation>
<altitudeMode>absolute</altitudeMode> 
<Scale><x>1</x><y>1</y><z>1</z></Scale>
</Model></Placemark>""" % (name,  longitude, latitude, altitude, heading, tilt, roll)
#<Link>
#   <href>file:///Users/felix/Research/Projects/GIS/models/heli.dae</href>
#</Link>    
    #handle GET command
    def do_GET(self):
        try:
            #print self.path
            self.send_response(200)
 
            #send header first
            self.send_header('Content-type','application/vnd.google-earth.kml+xml')
            self.end_headers()
 
            #send file content to client
            kml=KmlHeader+"<Document> <name>Mavue Traces</name>\
            <Style id=\"red_line\"> <LineStyle><color>ff0000ff</color><width>4</width></LineStyle></Style>\
            <Style id=\"blue_line\"><LineStyle><color>ff00ffff</color><width>4</width></LineStyle></Style>"
            for key, p in Google_Earth_Server.traces.items():
                p.updateFromSource()
                #+ self.makeView(p.longitude, p.latitude, p.altitude, p.heading, p.tilt, p.roll) \
                #+ self.makeModel(p.longitude, p.latitude+0.003, p.altitude, p.heading, p.tilt, p.roll) \
                kml = kml + self.makeTrace(p.name, p.color,   p.trace)
 
            kml+= "</Document></kml>"
 #               + self.makeModel(p.longitude, p.latitude+0.003, p.altitude, p.heading, p.tilt, p.roll) \
            
            #print kml
            self.wfile.write(kml)
            
        except IOError:
            self.send_error(404, 'file not found')


class Google_Earth_Server(plugins.Plugin):
    traces=dict()
    views=dict()
    
    def __init__(self,  data_range = [-1000, 0]):

        self.data_range=data_range
        print('http server is starting...')
     
        #ip and port of servr
        #by default http server port is 80
        server_address = ('127.0.0.1', 8000)
        self.httpd = HTTPServer(server_address, KmlHTTPRequestHandler)
       
        print('http server is running...')
        start_new_thread(self.httpd.serve_forever, ())

    def run(self,  message):
        if message.name()=="ATTITUDE":
            pitch=message.getValueByName("pitch").content()
            roll=message.getValueByName("roll").content()
            yaw=message.getValueByName("yaw").content()
            self.updateView(message.getMavlinkKey(),  tilt=pitch,  roll=roll,  heading=yaw)

        if message.name()=="GLOBAL_POSITION_INT" or message.name()=="GPS_RAW_INT":
            #self.updateTrace(message.getMavlinkKey(),  longitude=message.getValueByName("lon").content()/10000000.0,  latitude=message.getValueByName( "lat").content()/10000000.0,  altitude=message.getValueByName( "alt").content()/1000.0)
            #self.updateView(message.getMavlinkKey(),  longitude=message.getValueByName( "lon").content()/10000000.0,  latitude=message.getValueByName( "lat").content()/10000000.0,  altitude=message.getValueByName( "alt").content()/1000.0)
            # add message node to traces dict
            col = "blue_line"
            if message.name()=="GLOBAL_POSITION_INT":
                col = "red_line"
            if not message.getMavlinkKey() in self.traces.keys():
                self.traces[message.getMavlinkKey()]=Trace(name = message.getMavlinkKey(),  msg_node=message, data_range=self.data_range,  color =col)
                #message.subscribe(self.traces[message.getMavlinkKey()].updateFromSource)
                
    def filter(self, message):
        return message.name()=="ATTITUDE" or message.name()=="GLOBAL_POSITION_INT" or  message.name()=="GPS_RAW_INT"
        

    def updateTrace(self,  name,  **kwargs):
        if not name in self.traces.keys():
            self.traces[name]=Trace(name)
        self.traces[name].update(**kwargs)

    def updateView(self,  name,  **kwargs):
        if not name in self.views.keys():
            self.views[name]=Trace(name)
        self.views[name].update(**kwargs)



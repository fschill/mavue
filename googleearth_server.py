'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


#!/usr/bin/env python
 
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os
from thread import start_new_thread
import time
import math
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
    def __init__(self, name="Track",  longitude=6.566044801857777,  latitude=46.51852236174565,  altitude=440,  heading=0.0,  tilt=0.0,  roll=0.0):
        self.name=name
        self.heading=radianToPosDegree(heading)
        self.tilt=radianToPosDegree(90+tilt)
        self.roll=radianToSymDegree(-roll)
        self.altitude=altitude
        self.longitude=longitude
        self.latitude=latitude
        self.trace=[]

    def update(self,  longitude=None,  latitude=None,  altitude=None,  heading=None,  tilt=None,  roll=None):
        if heading!=None: self.heading=radianToPosDegree(heading)
        if tilt!=None: self.tilt=radianToPosDegree(math.pi/2.0+tilt)
        if roll!=None: self.roll=radianToSymDegree(-roll)
        if altitude!=None: self.altitude=altitude
        if longitude!=None: self.longitude=longitude
        if latitude!=None: self.latitude=latitude
        if longitude!=None and latitude!=None:
            self.trace.append([self.longitude,  self.latitude,  self.altitude])

#Create custom HTTPRequestHandler class
class KmlHTTPRequestHandler(BaseHTTPRequestHandler):
        
    def makeView(self, longitude, latitude, altitude, heading, tilt, roll):
       return "<Placemark> <name>3D View</name>\
        <Camera> <longitude> %f</longitude> \
        <latitude>%f</latitude> \
        <altitude>%f</altitude> \
        <heading>%f</heading> \
        <tilt>%f</tilt> \
        <roll>%f</roll> \
        <altitudeMode>absolute</altitudeMode> \
        </Camera></Placemark>" % (longitude, latitude, altitude, heading, tilt, roll)

    def makeTrace(self, trace):
        coordinate_string =""
        for p in trace:
            coordinate_string+="%f,%f,%f "%(p[0],  p[1],  p[2])
        return\
    """<Placemark>
<name>Trace</name>
<styleUrl>#m_ylw-pushpin0</styleUrl>
<LineString>
<tessellate>1</tessellate>
<coordinates>
%s 
</coordinates>
</LineString>
</Placemark>"""% coordinate_string

    def makeModel(self, longitude, latitude, altitude, heading, tilt, roll) :
    	return \
"""<Placemark><name>"Model"</name><styleUrl>#m_ylw-pushpin</styleUrl>
<Model id="model1"> 
<Location><longitude> %f</longitude> <latitude>%f</latitude> <altitude>%f</altitude> </Location>
<Orientation><heading>%f</heading> <tilt>%f</tilt> <roll>%f</roll> </Orientation>
<altitudeMode>absolute</altitudeMode> 
<Scale><x>1</x><y>1</y><z>1</z></Scale>
</Model></Placemark>""" % (longitude, latitude, altitude, heading, tilt, roll)
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
            kml=KmlHeader+"<Document> <name>Mavue Traces</name>"
            for key, p in GoogleEarthServer.traces.items():
                kml = kml \
                + self.makeView(p.longitude, p.latitude, p.altitude, p.heading, p.tilt, p.roll) \
                + self.makeModel(p.longitude, p.latitude+0.003, p.altitude, p.heading, p.tilt, p.roll) \
                + self.makeTrace(p.trace)
 
            kml+= "</Document></kml>"
 #               + self.makeModel(p.longitude, p.latitude+0.003, p.altitude, p.heading, p.tilt, p.roll) \
            
            #print kml
            self.wfile.write(kml)
            
        except IOError:
            self.send_error(404, 'file not found')


class GoogleEarthServer:
    traces=dict()
    
    def run(self):

        print('http server is starting...')
     
        #ip and port of servr
        #by default http server port is 80
        server_address = ('127.0.0.1', 8000)
        self.httpd = HTTPServer(server_address, KmlHTTPRequestHandler)
       
        print('http server is running...')
        start_new_thread(self.httpd.serve_forever, ())

    def update(self,  name,  **kwargs):
        if not name in GoogleEarthServer.traces.keys():
            GoogleEarthServer.traces[name]=Trace(name)
        GoogleEarthServer.traces[name].update(**kwargs)

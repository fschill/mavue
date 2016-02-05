import plugins
import solid
from math import *
from pymavlink import mavutil
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph.opengl as gl
import numpy as np
PI=3.1415

def showFacets( solid,   widget,  color=(0.7, 0.7, 0.0, 0.5),  shader='edgeHilight', glOptions='translucent',  translate=(0.0,  0.0,  0.0)):
    vertices=np.array([[(v[0]+translate[0], v[1]+translate[1], v[2]+translate[2])  for v in f.vertices] for f in solid.facets])
    mesh=gl.MeshData(vertexes=vertices)
    gm=gl.GLMeshItem(meshdata=mesh,  smooth=False,computeNormals=True,   color=color,   shader=shader, glOptions=glOptions)
    widget.addItem(gm)
    return gm


class robotvis(plugins.Plugin):
    def __init__(self,  model_file="",  data_range = [0, 0]):
        self.model_file=model_file
        self.data_range=data_range
        print "loading CAD model"
        serafina=solid.Solid()
        serafina.load("Vertex_visible_simplest.stl")
        #serafina.rotate_z()
        #serafina.rotate_z()
        #serafina.rotate_z()
        w = gl.GLViewWidget()
        w.opts['distance'] = 200
        
        axes=gl.GLAxisItem()
        axes.setSize(x=2000,  y=1000,  z=100)
        w.addItem(axes)
        w.show()
        w.setWindowTitle('Robot Visualiser')
        self.gl_item = showFacets(solid=serafina,  widget=w,  glOptions="opaque",  translate=[0,0,0])


    def filter(self,  message):
        return message.name()=="GPS_GLOBAL_POSITION_INT" or message.name()=="ATTITUDE"

             
    def run(self,  message): 
        if message.name()=="GPS_GLOBAL_POSITION_INT":
            lat=message.getValueByName("lat").content()/10000000.0
            lon=message.getValueByName("lon").content()/10000000.0
        
        if message.name()=="ATTITUDE":
            roll=message.getValueByName("roll").content()
            pitch=message.getValueByName("pitch").content()
            yaw=message.getValueByName("yaw").content()
            self.gl_item.resetTransform()
            self.gl_item.rotate(roll*180/PI, 1,0,0)
            self.gl_item.rotate(pitch*180/PI, 0,-1,0)
            self.gl_item.rotate(yaw*180/PI, 0,0,-1)

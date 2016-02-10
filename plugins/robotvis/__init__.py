import plugins
import solid
from math import *
from pymavlink import mavutil
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph.opengl as gl
import numpy as np
from droptarget import *

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
        serafina.scale((0.001,  0.001,  0.001))
        w = gl.GLViewWidget()
        w.opts['distance'] = 5
        
        axes=gl.GLAxisItem()
        axes.setSize(x=200,  y=100,  z=10)
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


class DropPlot6D(QtGui.QWidget):
    def __init__(self,  parent=None, model_file="",  data_range = [0, 0]):
        
        QtGui.QWidget.__init__( self, parent=parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setAcceptDrops(True)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        self.model_file=model_file
        self.data_range=data_range
        print "loading CAD model"
        serafina=solid.Solid()
        serafina.load("Vertex_visible_simplest.stl")
        serafina.scale((0.001,  0.001,  0.001))
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.opts['distance'] = 5
        
        axes=gl.GLAxisItem()
        axes.setSize(x=200,  y=100,  z=10)
        self.gl_widget.addItem(axes)
        self.gl_item = showFacets(solid=serafina,  widget=self.gl_widget,  glOptions="opaque",  translate=[0,0,0])


        self.layout.addWidget(self.gl_widget)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.targets_area=QtGui.QWidget()
        self.targets_layout=QtGui.QHBoxLayout()
        
        self.targets_area.setLayout(self.targets_layout)

        self.targets_area.setHidden(True)
        self.targets=[]
        self.layout.addWidget(self.targets_area)

    def sizeHint(self):
        return QtCore.QSize(500, 500)
        

    def removeTarget(self,  target):
        self.plotwidget.removeItem(target.curve)
        self.targets_layout.removeWidget(target)
        target.deleteLater()
        self.targets.remove(target)
            
    def updateSource(self, source):
      self.source=source

    def updatePlot(self):
        for t in self.targets:
            t.updateValue()
              
    def dragEnterEvent(self, event):
        print "drag_enter plot"
        self.targets_area.setHidden(False)

        if event.mimeData().hasFormat('application/x-mavplot'):
            event.accept()
        else:
            event.ignore() 

    def dropEvent(self, event):
        #self.updatePlot()
        new_source =  event.source().model()._rootNode.retrieveByKey(str(event.mimeData().text()).split(':'))

        if new_source.__class__.__name__=="MsgNode":
            self.addSource(source=new_source)
        else: 
            print "This plot doesn't accept this type:",   new_source.__class__.__name__

    def addSource(self, source=None):
        sourceTarget=DropTarget("Msg", self,  color=self.color)
        if sourceX is not None:
            sourceTarget.updateSource(source)
        self.targets.append(sourceTarget)
        self.targets_layout.addWidget(sourceTarget)
        
    def enterEvent(self,  event):
        self.targets_area.setHidden(False)
        pass

    def leaveEvent(self,  event):
        self.targets_area.setHidden(True)
        None

    def mouseMoveEvent(self,  event):
        print(event.pos())

    def mousePressEvent(self,  event):
        self.targets_area.setHidden(False)

    def closeEvent(self,  event):
        while len(self.targets)>0:
            self.targets[0].deleteTarget()
        print "closing window"
        
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

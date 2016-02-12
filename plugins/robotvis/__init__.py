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

class RobotDisplayObject(QtGui.QWidget):
    
    def __init__(self,text, parent, dataRange=[-100, 0],  gl_item = None):
        QtGui.QWidget.__init__( self, parent=parent)
        self.myParent=parent
        self.sources=[DropTarget("Attitude", self,  class_filter="MsgNode"),  DropTarget("Position", self,  class_filter="MsgNode")]
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self.gl_item = gl_item
        for s in self.sources:
            self.layout.addWidget(s)
        self.setAcceptDrops(True)
        self.dataRange = dataRange

    def updateValue(self):
        for s in self.sources:
            if s.source is not None:
                message = s.source
                #print message.name()
                if s.source.name() == "ATTITUDE":
                    roll=message.getValueByName("roll").getTrace(self.dataRange)[-1]
                    pitch=message.getValueByName("pitch").getTrace(self.dataRange)[-1]
                    yaw=message.getValueByName("yaw").getTrace(self.dataRange)[-1]
                    self.gl_item.resetTransform()
                    self.gl_item.rotate(roll*180/PI, 1,0,0)
                    self.gl_item.rotate(pitch*180/PI, 0,-1,0)
                    self.gl_item.rotate(yaw*180/PI, 0,0,-1)
                    
                if s.source.name() == "GLOBAL_POSITION_INT":
                    lat = message.getValueByName("lat").content()/10000000.0
                    lon = message.getValueByName("lon").content()/10000000.0
                    alt = message.getValueByName("alt").content()/1000.0
                    self.gl_item.translate(1, 1, 0)

                if s.source.name() == "LOCAL_POSITION_NED":
                    xtrace = message.getValueByName("x").getTrace(self.dataRange)
                    ytrace = message.getValueByName("y").getTrace(self.dataRange)
                    ztrace = message.getValueByName("z").getTrace(self.dataRange)
                    self.gl_item.translate(xtrace[-1], -ytrace[-1], -ztrace[-1])
                
    def removeTarget(self,  target):
        removal=True
        target.source=None
        
        for s in self.sources:
            if s.source!=None:
                removal=False
            
        if removal:
            try:
                self.myParent.removeTarget(self)
            except:
                pass
                
    def deleteTarget(self):
        for s in self.sources:
            s.remove()
        


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
        serafina.scale((0.01,  0.01,  0.01))
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
        self.layout.setStretch(0,  20)
        
        self.targets_area.setLayout(self.targets_layout)
        self.targets_area.setHidden(True)
        self.targets=[]
        self.layout.addWidget(self.targets_area)

    def sizeHint(self):
        return QtCore.QSize(500, 500)
        

    def removeTarget(self,  target):
        self.targets_layout.removeWidget(target)
        target.deleteLater()
        self.targets.remove(target)
            
    def updateSource(self, source):
      self.source=source

    def updatePlot(self):
        for t in self.targets:
            print t.source.name()
              
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
        sourceTarget = RobotDisplayObject("Msg", self,  gl_item = self.gl_item,  dataRange=self.data_range)
        if source is not None:
            if source.name=="ATTITUDE":
                sourceTarget.sources[0].updateSource(source)
            else:
                sourceTarget.sources[1].updateSource(source)
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
        


'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''



from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

import gui_elements 
from droptarget import *

class Curve2DBox(QtGui.QWidget):
    def __init__(self,text, parent, dataRange=[-100, 0],  color=QtGui.QColor(0, 0, 0)):
        QtGui.QWidget.__init__( self, parent=parent)
        self.myParent=parent
        self.color=color

        self.sources=[DropTarget("x", self,  color=self.color,  class_filter="ValueNode"),  DropTarget("y", self,  color=self.color,  class_filter="ValueNode")]
        self.curveTypeCombo=gui_elements.PlainComboField(parent=self,  label="curve",  value="Line",  choices=["Line",  "Scatter"])
        self.curveType="Line"
        self.connect(self.curveTypeCombo.combo,  QtCore.SIGNAL("currentIndexChanged(QString)"),  self.updateCurveType)
        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        #self.layout.addStretch()
        self.setLayout(self.layout)
        for s in self.sources:
            self.layout.addWidget(s)
        self.layout.addWidget(self.curveTypeCombo)
        self.curve=None
        self.setAcceptDrops(True)
        self.dataRange = dataRange

    def updateCurveType(self,  selectedCurve):
        self.curveType=selectedCurve
        self.myParent.plotwidget.removeItem(self.curve)
        self.curve=None
        #self.updateCurve()
    
    def updateValue(self):
        #print self.sources[1].currentName
        if self.curve==None:
            if self.curveType=="Line":
                self.curve=self.myParent.plotwidget.plot(pen=pg.mkPen(self.color))
                #self.myParent.plotwidget.plotItem.legend.addItem(self.curve,  self.sources[1].currentName)
                #self.curve=pg.PlotDataItem(pen=pg.mkPen(self.color),  name=self.sources[1].currentName)
                #self.myParent.plotwidget.addItem(self.curve)
                
            elif self.curveType=="Scatter":
                self.curve=self.myParent.plotwidget.scatterPlot(pen=pg.mkPen(self.color),  size=5, brush=pg.mkBrush(255, 255, 255, 100))
                #self.myParent.plotwidget.plotItem.legend.addItem(self.curve,  self.sources[1].currentName)
                #self.curve=pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 100),  name=self.sources[1].currentName)
                #self.myParent.plotwidget.addItem(self.curve)
            
            self.myParent.rebuildLegend()
        
        self.myParent.plotwidget.plotItem.legend.setGeometry(0, 0, 30, 30)

        xdata=self.sources[0].getData()
        ydata=self.sources[1].getData()
        length=max(len(xdata),  len(ydata))
        if len(xdata)==0:
            #xdata=[i for i in range(0, length)]
            xdata = self.sources[1].source.getCounterTrace(self.dataRange)
            if len(xdata)!=len(ydata):
                xdata=[i for i in range(0, len(ydata))]

        if len(ydata)==0:
            ydata=[i for i in range(0, length)]

        if len(xdata)!=len(ydata):
            # try to get matching ydata for each point in xdata
            print "size mismatch: x: %i, y%i"%(len(xdata),  len(ydata))
            xtrace = self.sources[0].source.getCounterTrace(self.dataRange)
            xdata = [self.sources[0].source.trace[self.sources[0].source.findTraceIndex(xi)] for xi in xtrace]
            ydata = [self.sources[1].source.trace[self.sources[1].source.findTraceIndex(xi)] for xi in xtrace]
            
        self.curve.setData(x=xdata,  y=ydata)


    def removeTarget(self,  target):
        #self.layout.removeWidget(target)
        #target.deleteLater()
        #self.targets.remove(target)

        removal=True
        self.myParent.plotwidget.plotItem.legend.removeItem(target.currentName)
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
        

    
class DropPlot(QtGui.QWidget):
    dropped = QtCore.pyqtSignal(list)
    def __init__(self, parent=None, data_range=[-100,0]):
        QtGui.QWidget.__init__( self, parent=parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.setAcceptDrops(True)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        self.plotwidget = pg.PlotWidget(name='Plot1')  
        self.plotwidget.addLegend(size=(10,  10),  offset=(10, 10))
        self.layout.addWidget(self.plotwidget)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.targets_area=QtGui.QWidget()
        self.targets_layout=QtGui.QHBoxLayout()
        
        self.targets_area.setLayout(self.targets_layout)

        self.targets_area.setHidden(True)
        self.targets=[]
        self.layout.addWidget(self.targets_area)
        self.dataRange=data_range
        #sourceTarget=Curve2DBox("data", self,  color=pg.intColor(len(self.targets)))
        #self.targets.append(sourceTarget)
        #self.targets_layout.addWidget(sourceTarget)
    
    def sizeHint(self):
        return QtCore.QSize(500, 500)
        
    def removeTarget(self,  target):
        self.plotwidget.removeItem(target.curve)
        self.targets_layout.removeWidget(target)
        target.deleteLater()
        self.targets.remove(target)

    def rebuildLegend(self):
        for t in self.targets:
            self.plotwidget.plotItem.legend.removeItem(t.sources[1].currentName)

        for t in self.targets:
            print "adding ",  t.sources[1].currentName
            self.plotwidget.plotItem.legend.addItem(t.curve,  t.sources[1].currentName)
        #self.myParent.plotwidget.plotItem.legend.updateSize()
        
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
        if new_source.__class__.__name__=="ValueNode":
            self.addSource(sourceY=new_source)
            print "dropped on plot!"
        elif new_source.__class__.__name__=="MsgNode":
            #add all values of the message
            # look for time_boot_ms:
            timestamp = new_source.getValueByName("time_boot_ms")
            for val in new_source.getChildrenNames():
                val_node=new_source.getValueByName(val)
                print val_node.name()
                if val_node.name()!="time_boot_ms":
                    self.addSource(sourceY=val_node,  sourceX = timestamp)
        else: 
            print "This plot doesn't accept this type:",   new_source.__class__.__name__

    def addSource(self, sourceX=None, sourceY=None):
        if (sourceX is not None and not (isinstance(sourceX.content(),  int) or isinstance(sourceX.content(),  float) or  isinstance(sourceY.content(),  list) )) or \
        (sourceY is not None and not (isinstance(sourceY.content(),  int) or isinstance(sourceY.content(),  float) or isinstance(sourceY.content(),  list))):
            print "cannot add this type as source:",  sourceX,  isinstance(sourceY.content(),  list)
            return

        sourceTarget=Curve2DBox("data", self, dataRange=self.dataRange, color=pg.intColor(len(self.targets)))
        if sourceX is not None:
            sourceTarget.sources[0].updateSource(sourceX)
        if sourceY is not None:
            sourceTarget.sources[1].updateSource(sourceY)
        self.targets.append(sourceTarget)
        self.targets_layout.addWidget(sourceTarget)
        self.rebuildLegend()

        
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

class TimeLinePlot(DropPlot):
    def __init__(self, parent=None, dataRange=[0,0]):
        DropPlot.__init__( self, parent=parent, data_range=dataRange)

        self.lr = pg.LinearRegionItem([0, 1000])
        self.plotwidget.addItem(self.lr)
        self.lr.sigRegionChanged.connect(self.regionChanged)
        self.plotwidget.sigXRangeChanged.connect(self.plotChanged)
        self.tracking = True
        self.internalModificationFlag = False

    def addSource(self, sourceX=None, sourceY=None):
        if (sourceX is not None and not (isinstance(sourceX.content(),  int) or isinstance(sourceX.content(),  float))) or \
        (sourceY is not None and not (isinstance(sourceY.content(),  int) or isinstance(sourceY.content(),  float))):
            print "cannot add this type as source"
            return

        sourceTarget=Curve2DBox("data", self, dataRange=[0,0], color=pg.intColor(len(self.targets)))
        #if sourceX is not None:
        #    sourceTarget.sources[0].updateSource(sourceX)
        if sourceY is not None:
            sourceTarget.sources[1].updateSource(sourceY)
        self.targets.append(sourceTarget)
        self.targets_layout.addWidget(sourceTarget)
        self.rebuildLegend()

    def regionChanged(self):
        if self.internalModificationFlag:
            self.internalModificationFlag=False
            return
        region = list(self.lr.getRegion())
        try:
            maxCounter = self.targets[0].sources[1].source.getMessageCounter()
            visibleRange = self.plotwidget.getViewBox().viewRange()[0]
            if region[1] >= maxCounter:
                offset = region[1]-maxCounter
                region[1] -= offset
                region[0] -= offset
                self.tracking = True
            else:
                self.tracking = False

            self.lr.setRegion(region)
            self.dataRange[0]=region[0]
            self.dataRange[1]=region[1]
            if not self.tracking:
                self.targets[0].sources[1].source.getRootNode().notifyAllSubscribers()
        except:
            pass

    def plotChanged(self):
        region = list(self.lr.getRegion())
        visibleRange = self.plotwidget.getViewBox().viewRange()[0]
        if self.tracking and  region[1] < visibleRange[1]:
            offset = region[1]-visibleRange[1]
            region[1] -= offset
            region[0] -= offset
        self.internalModificationFlag = True
        self.lr.setRegion(region)
        self.dataRange[0]=region[0]
        self.dataRange[1]=region[1]

    def sizeHint(self):
        return QtCore.QSize(800, 150)

    def closeEvent(self,  event):
        DropPlot.closeEvent(self,  event)
        self.dataRange[0]=-100
        self.dataRange[1]=0
        


class DockPlot(QtGui.QDialog):
    def __init__(self,  title="Plot",  parent=None,  widget=None):
        QtGui.QDialog.__init__( self, parent=parent)
        self.setWindowTitle(title)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.widget=widget
        if widget!= None:
            self.layout.addWidget(widget)
        self.setAcceptDrops(True)
#        self.setFloating(True)
#        self.setAllowedAreas(QtCore.Qt.NoDockWidgetArea)

    def closeEvent(self,  event):
        self.widget.closeEvent(event)
        print "closing dock"
        
        
class ParamSlider(QtGui.QDialog):
    def __init__(self,  title="Parameter",  parent=None):
        QtGui.QDialog.__init__( self, parent=parent)
        self.setWindowTitle(title)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(True)

        self.slider=QtGui.QSlider(parent=self)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.slider)
        
        self.target=DropTarget(text="source",  parent=self, class_filter="ValueNode")
        self.layout.addWidget(self.target)
        self.scaling=1000
        self.emitChange=True
        self.connect(self.slider,  QtCore.SIGNAL("valueChanged(int)"),  self.sliderChanged)
        #self.connect(self.slider,  QtCore.SIGNAL("sliderMoved(int)"),  self.sliderChanged)
        #self.connect(self.slider,  QtCore.SIGNAL("sliderReleased()"),  self.sliderChanged)
        
    def updateValue(self):
        self.setWindowTitle(self.target.currentName)
        newValue=int(self.scaling*self.target.getCurrent())
        self.emitChange=False
        if newValue<self.slider.minimum():
            self.slider.setMinimum(newValue)
            print "newMin",  newValue,  self.slider.minimum()
        if newValue>self.slider.maximum():
            self.slider.setMaximum(newValue)
            print "newMax",  newValue,  self.slider.maximum()
        self.slider.setValue(newValue)
        self.emitChange=True
        
    def sliderChanged(self):
        newValue=self.slider.value()/1000.0
        if self.emitChange:
            try:
                print newValue
                self.target.source._parent.editValue(newValue)
            except:
                print "updating parameter unsuccessful!"
        
    def removeTarget(self,  target):
        self.slider.setRange(-1,  1)
        self.setWindowTitle("slider")

import plugins
from math import *
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

import numpy as np
from droptarget import *

from numpy.fft import fft, ifft

def periodic_corr(x, y):
    """Periodic correlation, implemented using the FFT.

    x and y must be real sequences with the same length.
    """
    return ifft(fft(x) * fft(y).conj()).real

class SpectrogramPlot(QtGui.QWidget):
    def __init__(self,  parent=None, model_file="",  data_range = [0, 0]):
        
        QtGui.QWidget.__init__( self, parent=parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.data_range = data_range
        self.setAcceptDrops(True)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        #self.graphicsView = pg.GraphicsLayoutWidget()
        #self.view = self.graphicsView.addViewBox()
        #self.imageItem = pg.ImageItem(border='w')
        
        #self.view.addItem(self.imageItem)
        self.imageItem = pg.ImageView()
        self.imageItem.getView().setAspectLocked(False)
        self.layout.addWidget(self.imageItem)
        self.layout.setMargin(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.targets_area=QtGui.QWidget()
        self.targets_layout=QtGui.QHBoxLayout()
        self.targets_area.setLayout(self.targets_layout)
        self.targets_area.setHidden(True)
        self.targets=[]

        self.layout.addWidget(self.targets_area)
        
        self.layout.setStretch(0,  20)

        data = np.random.normal(size=(600, 600), loc=1024, scale=64).astype(np.uint16)
        self.imageItem.setImage(data)
        self.source = None

    def sizeHint(self):
        return QtCore.QSize(500, 500)
        
            
    def updateSource(self, source):
      self.source=source

    def updatePlot(self):
        if self.source is not None:
            trace = self.source.getTrace(self.data_range)
            data = np.array(trace)
            
#            signal = np.array(trace[0],  float)
#            f =    40000.0
#            sr = 100000.0
#            for i in range(0, 100):
#                signal[i] = sin(i * f/sr *3.1415*2)
#                f = f+ 50
#
#            for i in range(100,  len(signal)):
#                signal[i]=0
#            data = periodic_corr(data,  signal)

#            combined_data = np.hstack(data)
#            fftdata = []
#            fft_window_size = 512
#            fft_step_size = 64
#            for i in range(0,  len(combined_data)/fft_step_size-fft_window_size):
#                fft_real = fft(combined_data[i*fft_step_size:i*fft_step_size+fft_window_size])[fft_window_size/2:]
#                fftdata.append(np.absolute(fft_real))
#            
#            data=np.array(fftdata)
            data = np.absolute(data)

            self.imageItem.setImage(data)
            

    def dragEnterEvent(self, event):
        print "drag_enter plot"

        if event.mimeData().hasFormat('application/x-mavplot'):
            event.accept()
        else:
            event.ignore() 

    def dropEvent(self, event):
        #self.updatePlot()
        new_source =  event.source().model()._rootNode.retrieveByKey(str(event.mimeData().text()).split(':'))

        if new_source.__class__.__name__=="ValueNode":
            self.addSource(source=new_source)
        else: 
            print "This plot doesn't accept this type:",   new_source.__class__.__name__

    def addSource(self, source=None):
        if source is not None:
            self.source = source
            self.source.subscribe(self.updatePlot)
            self.updatePlot()
        
    def mouseMoveEvent(self,  event):
        print(event.pos())

    def enterEvent(self,  event):
        self.targets_area.setHidden(False)
        pass

    def leaveEvent(self,  event):
        self.targets_area.setHidden(True)
        None

    def mousePressEvent(self,  event):
        self.targets_area.setHidden(False)
        
    def closeEvent(self,  event):
        if self.source is not None:
            self.source = source
            self.source.unsubscribe(self.updatePlot)
        
        print "closing window"
        

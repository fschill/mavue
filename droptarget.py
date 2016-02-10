'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''



from pyqtgraph.Qt import QtGui, QtCore

class DropTarget(QtGui.QWidget):
    def __init__(self,text, parent, color=QtGui.QColor(0, 0, 0)):
        QtGui.QWidget.__init__( self, parent=parent)
        self.myParent=parent
        self.originalName=text
        self.currentName=self.originalName
        self.color=color
        self.label=QtGui.QLabel(text, self)
        self.removeButton=QtGui.QPushButton("-")
        #self.removeButton.setAutoFillBackground(True)
        #self.removeButton.setStyleSheet("background-color: rgba(%i, %i, %i, %i); "%(color.red(),  color.green(),  color.blue(),  255))

        self.removeButton.setFixedSize(15, 15)
        self.connect(self.removeButton,  QtCore.SIGNAL("clicked()"),  self.remove)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.layout.setMargin(0)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.removeButton)
        self.layout.addStretch()
        self.setAcceptDrops(True)
        self.source=None
        self.curve=None

    def dragEnterEvent(self, event):
        print "drag_enter"
        if event.mimeData().hasFormat('application/x-mavplot'):
            print event.mimeData().text()
            print event.source().model()._rootNode.retrieveByKey(str(event.mimeData().text()).split(':')).getKey()
            event.accept()
        else:
            event.ignore() 

    def remove(self):
        try:
            self.source.unsubscribe(self.myParent.updateValue)
        except:
            print "remove", self.currentName, "  not subscribed"

        self.myParent.removeTarget(self)
        self.source=None
       
        self.label.setText(self.originalName)
        self.currentName=self.originalName
    
    def updateSource(self,  source):
        try:
            self.source.unsubscribe(self.myParent.updateValue)
        except:
            print "not subscribed"
        self.source=source
        self.source.subscribe(self.myParent.updateValue)
        self.myParent.updateValue()
                
        self.label.setAutoFillBackground(True)
        self.label.setStyleSheet("background-color: rgba(%i, %i, %i, %i); "%(self.color.red(),  self.color.green(),  self.color.blue(),  255))
        self.label.setText(source.displayName())
        self.currentName=source.displayName()
                     
    def dropEvent(self, event):
        #self.updateSource( event.source().model().lastDraggedNode)
        new_source =  event.source().model()._rootNode.retrieveByKey(str(event.mimeData().text()).split(':'))
        print new_source.__class__.__name__
        if new_source.__class__.__name__=="ValueNode":
            self.updateSource(new_source)
            self.source.subscribe(self.myParent.updateValue)
            self.myParent.updateValue()
        
    def getData(self):
        if self.source==None:
            return []
        #if isinstance(self.source.content(), list):
        #    return self.source.content()
        #else:
        return self.source.getTrace(self.myParent.dataRange)

    def getCurrent(self):
        if self.source==None:
            return []
        return self.source.content()

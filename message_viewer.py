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
import time

from message_store import *


class TreeModel(QtCore.QAbstractItemModel):

    def __init__(self, root, parent=None):
        super(TreeModel, self).__init__(parent)
        self._rootNode = root
        self.lastDraggedNode=None

    def rowCount(self, parent):
        if not parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = parent.internalPointer()

        return parentNode.childCount()

    def columnCount(self, parent):
      if parent and parent.isValid():
            return parent.internalPointer().columnCount(parent)
      else:
            return 2
            
    def data(self, index, role):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return str(node.name())
            if index.column() == 1:
                return str(node.displayContent())
                
        if role == QtCore.Qt.CheckStateRole and self.isMavlinkMessage(index) and index.column()==0:
            if node.checked():
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked

    def setData(self, index, value, role=QtCore.Qt.EditRole):

        if index.isValid():
            if role == QtCore.Qt.CheckStateRole:
                node = index.internalPointer()
                node.setChecked(not node.checked())
                self.dataChanged.emit(index, index)               
                self.emitDataChangedForChildren(index)
                return True
            if role == QtCore.Qt.EditRole:
                stream=index.internalPointer()
                stream.editValue(float(value.toString()))
                print "edit",  value.toString()
        return False
        
    def emitDataChangedForChildren(self, index):
        count = self.rowCount(index)
        if count:            
            self.dataChanged.emit(index.child(0, 0), index.child(count-1, 0))
            for child in range(count):
                self.emitDataChangedForChildren(index.child(child, 0))
                
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if  section==0:
                return "Nodes"
            else:
                return "Values"

    def isMavlinkMessage(self,  index):
        return index.internalPointer().isMessage()

    def flags(self, index):
        if not index.isValid(): return QtCore.Qt.NoItemFlags
        if self.isMavlinkMessage(index):
            if  index.column()==0:
                return QtCore.Qt.ItemIsEnabled  | QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable
            elif index.column()==1: # frequency display
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable |QtCore.Qt.ItemIsEditable
            else:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsDragEnabled 
        else:
            if  index.column()==0:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsUserCheckable
            else:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsDragEnabled
        
                
    def supportedDropActions(self): 
        return QtCore.Qt.CopyAction 

    def mimeTypes(self):
        return ['application/x-mavplot']

    def mimeData(self, indexes):
        print "start drag"
        mimedata = QtCore.QMimeData()
        #data = QtCore.QByteArray()
        #stream = QtCore.QDataStream(data, QtCore.QIODevice.WriteOnly)
        #stream << indexes[0].internalPointer()
        mimedata.setData('application/x-mavplot', str(indexes[0].internalPointer().getFullKey()))
        mimedata.setText( str(indexes[0].internalPointer().getFullKey()))
        self.lastDraggedNode=indexes[0].internalPointer()
        
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):
        print 'dropMimeData %s %s %s %s' % (data.data('application/x-mavplot'), action, row, parent.internalPointer()) 
        return True

    def parent(self, index):
        node = self.getNode(index)
        parentNode = node.parent()

        if parentNode == self._rootNode:
            return QtCore.QModelIndex()
        return self.createIndex(parentNode.row(), 0, parentNode)

    def index(self, row, column, parent):
        parentNode = self.getNode(parent)
        childItem = parentNode.child(row)

        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def getNode(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node

        return self._rootNode

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):

        parentNode = self.getNode(parent)
        self.beginRemoveRows(parent, position, position + rows - 1)

        for row in range(rows):
            success = parentNode.removeChild(position)

        self.endRemoveRows()

        return success
        

class MessageTreeView:
    def __init__(self):
        self.rootNode   = RootNode(name="Mavlink",  key_attribute='Mavlink')
        self.model = TreeModel(self.rootNode)
        self.treeView = QtGui.QTreeView()
        self.treeView.setMinimumWidth(400)

        self.treeView.show()
        self.treeView.setModel(self.model)
        self.treeView.setColumnWidth(0, 300)
        self.treeView.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.treeView.setSelectionMode( QtGui.QAbstractItemView.ExtendedSelection )
    
    def close(self):
        self.rootNode.unsubscribeAllRecursive()

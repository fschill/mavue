'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


from PyQt4.QtCore import *
from PyQt4 import QtGui,  QtCore
from threading import Thread
from multiprocessing import Queue

class HorizontalBar(QtGui.QWidget):
    def __init__(self,  parent=None):
        QtGui.QWidget.__init__( self, parent=parent)
        self.items=[]
        self.layout=QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        
    def add(self,  widget,  signal,  action):
        self.layout.addWidget(widget)
        self.items.append(widget)
        self.connect(widget,   QtCore.SIGNAL(signal),  action)

        

class PlainComboField(QtGui.QComboBox):
    def __init__(self, parent=None,  label="", value=None,  choices=None,  onOpenCallback=None):
        QtGui.QComboBox.__init__( self, parent=parent)
        self.choices = choices
        self.onOpenCallback = onOpenCallback
        if not value in choices:
            self.choices.append(value)
        for t in choices:
            self.addItem(QString(t))
        if value!=None:
            self.setCurrentIndex(self.choices.index(value))
        self.combo=self

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(self.choices.index(value))
            
    def showPopup(self):
        if self.onOpenCallback!=None:
            self.onOpenCallback()
        QtGui.QComboBox.showPopup(self)
         
    def updateChoices(self,  choices):
        changed=False
        for mc,nc in zip(self.choices,  choices):
            if mc != nc:
                changed=  True
        if not changed:
            return
        self.clear()
        
        self.choices = choices
        for t in choices:
            self.addItem(QString(t))
        
        

class LabeledComboField(QtGui.QWidget):
    def __init__(self, parent=None,  label="", value=None,  choices=None):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.combo=QtGui.QComboBox(parent=self)
        for t in choices:
            self.combo.addItem(QString(t))
        if value!=None:
            self.combo.setCurrentIndex(choices.index(value))
        self.layout.addWidget(self.combo)

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(choices.index(value))


class LabeledTextField(QtGui.QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None,  formatString="{:s}"):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.formatString=formatString
        self.editable=editable
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.text=QtGui.QLineEdit(parent=self)
        self.text.setReadOnly(not self.editable)
        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)

    def updateValue(self,  value):
        if value!=None:
            # check if value is a multi-value object:
            if isinstance(value, (list,  frozenset,  tuple,  set,  bytearray)):
                self.text.setText(''.join(self.formatString.format(x) for x in value))
            else:
                self.text.setText(self.formatString.format(value))


class LabeledProgressField(QtGui.QWidget):
    def __init__(self, parent=None,  label="", value=None, min=None,  max=None,  step=1.0):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.progress=QtGui.QProgressBar(parent=self)
        self.updateValue(value=value,  min=min,  max=max)
        self.layout.addWidget(self.progress)

    def updateValue(self,  value,  min,  max):
        self.progress.setMinimum(min)
        self.progress.setMaximum(max)
        self.progress.setValue(value)
        
class LabeledFileField(QtGui.QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None,  fileSelectionPattern="All files (*.*)"):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.fileSelectionPattern=fileSelectionPattern
        self.editable=editable
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.text=QtGui.QLineEdit(parent=self)
        self.text.setReadOnly(not self.editable)
        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)
        
        self.fileDialogButton=QtGui.QPushButton("Select...")
        self.connect(self.fileDialogButton,  SIGNAL("clicked()"), self.showDialog)
        self.layout.addWidget(self.fileDialogButton)
        

    def updateValue(self,  value):
        if value!=None:
            self.text.setText(value)
    
    def showDialog(self):
        filename=QtGui.QFileDialog.getOpenFileName(self, 'Open file', '',  self.fileSelectionPattern)
        if filename!=None:
            self.updateValue(filename)

class LabeledNumberField(QtGui.QWidget):
    def __init__(self, parent=None,  label="", min=None,  max=None,  value=0,  step=1.0):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.number=QtGui.QDoubleSpinBox(parent=self)
        if min!=None:
            self.number.setMinimum(min)
        else:
            self.number.setMinimum(-10000000)
        if max!=None:
            self.number.setMaximum(max)
        else:
            self.number.setMaximum(10000000)
        self.number.setSingleStep(step);
        self.number.setValue(value)
        self.layout.addWidget(self.number)
    
    def updateValue(self,  value):
        self.number.setValue(value)




class ToolPropertyWidget(QtGui.QWidget):
    def updateParameter(self,  object=None,  newValue=None):
        object.updateValue(newValue)
        
    def __init__(self, parent,  tool):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.parameters=dict()
        
        # get editable parameters
        for object in tool.parameters:
            p=object
        
            if object.__class__.__name__=="TextParameter":
                w=LabeledTextField(parent=self,  label=object.name,  editable=object.editable,  formatString=object.formatString)
                self.parameters[p]=w
                w.updateValue(object.value)
                self.layout.addWidget(w)
                if object.editable:
                    self.connect(w.text,  SIGNAL("textChanged(QString)"), object.updateValue)

            if object.__class__.__name__=="FileParameter":
                w=LabeledFileField(parent=self,  label=object.name,  editable=object.editable,  fileSelectionPattern=object.fileSelectionPattern)
                self.parameters[p]=w
                w.updateValue(object.value)
                self.layout.addWidget(w)
                if object.editable:
                    self.connect(w.text,  SIGNAL("textChanged(QString)"), object.updateValue)

            if object.__class__.__name__=="NumericalParameter":
                w=LabeledNumberField(parent=self, label=object.name,  min=object.min, max=object.max,   value=object.getValue(),  step=object.step)
                self.parameters[p]=w
                self.layout.addWidget(w)
                if object.editable:
                    self.connect(w.number,  SIGNAL("valueChanged(double)"),  object.updateValue)

            if object.__class__.__name__=="ProgressParameter":
                w=LabeledProgressField(parent=self,  label=object.name,  min=object.min, max=object.max,   value=object.getValue())
                self.parameters[p]=w
                self.layout.addWidget(w)


            if object.__class__.__name__=="ChoiceParameter":
                w=LabeledComboField(parent=self,  label=object.name,  value=object.getChoiceStrings()[object.choices.index(object.getValue())],  choices=object.getChoiceStrings())
                self.parameters[p]=w
                self.layout.addWidget(w)
                if object.editable:
                    self.connect(w.combo,  SIGNAL("currentIndexChanged(QString)"),  object.updateValueByString)
                
            if object.__class__.__name__=="ActionParameter":
                w=QtGui.QPushButton(object.name)
                self.parameters[p]=w
                self.layout.addWidget(w)
                self.connect(w,  SIGNAL("clicked()"),  object.callback)
                

        self.layout.addStretch()
        
    def update(self):
        # get editable parameters
        for object in self.parameters.keys():
            w=self.parameters[object]
            if object.__class__.__name__=="TextParameter":
                w.updateValue(object.value)

            if object.__class__.__name__=="FileParameter":
                w.updateValue(object.value)

            if object.__class__.__name__=="ProgressParameter":
                w.updateValue(value=object.value,  min=object.min,  max=object.max)

            if object.__class__.__name__=="NumericalParameter":
                w.updateValue(object.value)
                
            if object.__class__.__name__=="ChoiceParameter":
                w.updateValue(object.value)
                
            if object.__class__.__name__=="ActionParameter":
                None

class ItemListModel(QAbstractListModel): 
    def __init__(self, itemlist, parent=None, *args): 
        
        QAbstractListModel.__init__(self, parent, *args) 
        self.listdata = itemlist
 
    def rowCount(self, parent=QModelIndex()): 
        return len(self.listdata) 
 
    def data(self, index, role): 
        if not (index.isValid()  and index.row()<len(self.listdata)):
            return None
        if role == Qt.DisplayRole:
            return self.listdata[index.row()].name.value
        if role == Qt.CheckStateRole:
            if len(self.listdata)>0 and self.listdata[index.row()].selected:
                return Qt.Checked
            else:
                return Qt.Unchecked
        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid():
            if role == Qt.CheckStateRole:
                if index.row()<len(self.listdata):
                    self.listdata[index.row()].selected=(not self.listdata[index.row()].selected)
                    self.dataChanged.emit(index, index)               
                    return True
        return False
        
    def addItem(self,  newItem):
        self.beginInsertRows(QModelIndex(),  self.rowCount(),  self.rowCount()+1)
        self.listdata.append(newItem)
        self.endInsertRows()
        return self.index(self.rowCount()-1)
        

    def removeRows(self,  row,  count,  parent):
        self.beginInsertRows(QModelIndex(),  self.rowCount(),  self.rowCount()+1)
        for i in reversed(range(row,  row+count)):
            del self.listdata[i]
        self.endInsertRows()
        
    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable |  Qt.ItemIsEditable | Qt.ItemIsUserCheckable


class ListWidget(QtGui.QWidget):
    def __init__(self, parent=None,  title="",  itemlist=[],  itemclass=None,  on_select_cb=None,   **creationArgs):
        QtGui.QWidget.__init__( self, parent=parent)
        self.creationArgs=creationArgs
        self.on_select_cb=on_select_cb
        ## Create a grid layout to manage the widgets size and position
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.listmodel=ItemListModel(itemlist)
        self.itemclass=itemclass
        self.listw = QtGui.QListView()
        self.listw.setModel(self.listmodel)
        self.listw.clicked.connect(self.respondToSelect)
        
        buttonwidget=QtGui.QWidget()
        buttonLayout=QtGui.QHBoxLayout()
        buttonwidget.setLayout(buttonLayout)
        self.addBtn = QtGui.QPushButton('+')
        self.removeBtn = QtGui.QPushButton('-')
        buttonLayout.addWidget(self.addBtn)
        buttonLayout.addWidget(self.removeBtn)
        self.layout.addWidget(QtGui.QLabel(title), 0, 0)   # button goes in upper-left
        self.layout.addWidget(self.listw, 1, 0)  # list widget goes in bottom-left
        self.layout.addWidget(buttonwidget, 2, 0)   # button goes in upper-left
        
        self.connect(self.addBtn,  SIGNAL("clicked()"),  self.addItem)
        self.connect(self.removeBtn,  SIGNAL("clicked()"),  self.removeItem)
        
        
        if len(itemlist)>0:
            self.selectedTool=itemlist[0]
        else:
            self.selectedTool=None
        
        if self.selectedTool!=None:
            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            self.layout.addWidget(self.propertyWidget, 0, 1,  3,  1)  
        
    def respondToSelect(self,  index):
        self.selectedTool=self.listmodel.listdata[index.row()]
        if self.selectedTool!=None:
            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            self.layout.addWidget(self.propertyWidget, 0, 1,  3,  1)  
            if self.on_select_cb!=None:
                self.on_select_cb(self.selectedTool)
            
    def addItem(self,  addExistingItems=True,  **creationArgs):
        if len(creationArgs)==0:
            newItem=self.itemclass(**self.creationArgs)
        else:
            newItem=self.itemclass(**creationArgs)
        
        newName=newItem.name.value
        nameExists=False
        foundItem=None
        for item in self.listmodel.listdata:
            if item.name.value==newName:
                nameExists=True
                foundItem=item
                break
        
        if not nameExists or (nameExists and addExistingItems):
            counter=1
            while newName in [i.name.value for i in self.listmodel.listdata]:
                newName="%s - %i"%(newItem.name.value,  counter)
                counter+=1
            newItem.name.updateValue(newName)
            # add to list model
            addedItem=self.listmodel.addItem(newItem)
            self.listw.setCurrentIndex(addedItem)
            self.respondToSelect(addedItem)
            return newItem
        else:
            return foundItem
        
    def findItem(self,  name):
        for item in self.listmodel.listdata:
            if name==item.name.value:
                return item
        return None
        
    def removeItem(self):
        itemindex=self.listw.selectedIndexes()
        if len(itemindex)==0:
            return
        self.listmodel.removeRows(itemindex[0].row(),  1,  itemindex[0])
        
        

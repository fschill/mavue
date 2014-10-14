class ItemWithParameters:
    def __init__(self, name="-",  ):
        self.name=TextParameter(parent=self, name="Name", value=name)
        self.selected=False    

    def getName(self):
        return self.name


class EditableParameter:
    
    def __init__(self,  parent=None,  name="",  editable=True,   callback=None):
        self.name=name
        self.parent=parent
        self.value=None
        self.selected=False    
        self.editable=editable
        self.callback=callback
    
    def updateValue(self,  value):
        #print "new value",  value
        self.value=value
        if self.callback!=None:
            self.callback(self)
        
    def getValue(self):
        return self.value

class TextParameter(EditableParameter):
    def __init__(self,  value="", formatString="{:s}",     **kwargs):
        self.formatString=formatString
        EditableParameter.__init__(self,  **kwargs)
        self.value=value


class FileParameter(EditableParameter):
    def __init__(self,  value="",  fileSelectionPattern="All files (*.*)",     **kwargs):
        EditableParameter.__init__(self,  **kwargs)
        self.value=value
        self.fileSelectionPattern=fileSelectionPattern


class NumericalParameter(EditableParameter):
    def __init__(self,  value=0,  min=None,  max=None,  step=0,  enforceRange=False,  enforceStep=False,  **kwargs):
        EditableParameter.__init__(self,  **kwargs)
        self.value=value
        self.min=min
        self.max=max
        self.step=step
        self.enforceRange=enforceRange
        self.enforceStep=enforceStep

    def updateValue(self,  value):
        #print "new value",  value
        self.value=value
        if self.enforceRange:
            self.value=min(max,  max(min,  self.value))
        if self.enforceStep:
            self.value=float(int(self.value/self.step)*self.step)
        
        
class ChoiceParameter(EditableParameter):
    def __init__(self,  value=None, choices=None, **kwargs):
        EditableParameter.__init__(self, **kwargs)
        self.value=value
        self.choices=choices
    
    def getChoiceStrings(self):
        cs=[]
        for c in self.choices:
            if "name" in dir(c) and "value" in dir(c.name):
                cs.append(c.name.value)
            elif c.__class__.__name__=="str":
                cs.append(c)
        return cs
            
    def updateValueByString(self,  value):
        strings=self.getChoiceStrings()
        for i in range(0, len(self.choices)):
            s=strings[i]
            if s==value:
                print i,  s
                self.value=self.choices[i]
        print self.value
        
class ActionParameter(EditableParameter):
    def __init__(self,   **kwargs):
        EditableParameter.__init__(self, **kwargs)
        

import time

KEY_SEPARATOR=":"

def rgetattr(item,  attribute):
    subItem=item
    attList=attribute.split('.')
    while len(attList)>0:
        testsubItem=getattr(subItem,  attList[0])
        subItem=testsubItem
        attList=attList[1:]
    return subItem


class RootNode(object):
    def __init__(self, name, parent=None, checked=False, content=None,  key_attribute=None):
        self._name = name
        self._content=content
        self._children = dict()
        self._parent = parent
        self._checked = checked
        self._key_attribute=key_attribute
        self._subscribers=set()
        
        if content!=None and self._key_attribute!=None:
            self._name=rgetattr(content,  self._key_attribute)
        
        if parent is not None:
            parent.addChild(self)

    def addChild(self, child):
        self._children[child.name()]=child

    def updateContent(self, key_attribute_list,  content):
        if len(key_attribute_list)==0:
            return
        
        child_name=None
        try:
            child_name=rgetattr(content,  key_attribute_list[0])
        except AttributeError:
            pass
        
        # test remaining keys to see if any are valid
        future_keys=0
        for a in key_attribute_list:
            try:
                if rgetattr(content,  a)!=None:
                    future_keys+=1
            except AttributeError:
                pass
        #skip non-existent keys
        while future_keys>=1 and child_name==None:
            key_attribute_list=key_attribute_list[1:]
            try:
                child_name=rgetattr(content,  key_attribute_list[0])
            except AttributeError:
                pass
        if child_name==None:
            return
        
        if future_keys==1:
            if not(child_name in self._children.keys()):
                if content._type=="PARAM_VALUE":
                    ParamNode(name=child_name,    parent=self,  content=content,  key_attribute=key_attribute_list[0])
                else:
                    MsgNode(name=child_name,    parent=self,  content=content,  key_attribute=key_attribute_list[0])
            self._children[child_name].updateContent(content=content)
                
        else:
            if not(child_name in self._children.keys()):
                RootNode(name=child_name,    parent=self, content=content,  key_attribute=key_attribute_list[0])
            self._children[child_name].updateContent(key_attribute_list=key_attribute_list[1:],  content=content)
            
        return self._children[child_name]
    
    def insertChild(self, position, child):
        self._children[child.name()]=child
        return True

    def name(self):
        return self._name
    
    def getKey(self):
        return str(self._key_attribute)+'='+str(self._name)

    def getFullKey(self):
        if self._parent!=None:
            return str(self._parent.getFullKey()+KEY_SEPARATOR+self.getKey())
        else:
            return self._name
    
    def retrieveByKey(self,  key):
        key_list=key
        if len(key_list)==0:
            return None
        local_key=key_list[0].split('=')
        if (len(local_key)==1 and local_key[0]==str(self._key_attribute)) or  (len(local_key)>1 and local_key[0]==str(self._key_attribute) and local_key[1]==str(self._name)):
            if len(key_list)==1:
                return self
            else:
                for c in self._children.values():
                    r=c.retrieveByKey(key_list[1:])
                    if r!=None:
                        return r
        else:
            return None
    
    
    def checked(self):
        return self._checked

    def setChecked(self, state):
        None
        
    def child(self, row):
        return self._children[sorted(self._children.keys())[row]]

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent is not None:
            return sorted(self._parent._children.keys()).index(self.name())

    def columnCount(self, parent):
        return 2

    def content(self):
        return self._content

    def isMessage(self):
        return False

    def displayContent(self):
        #return str(self._name)
        #return self._key_attribute
        return ""

    def displayName(self):
        if self._parent!=None:
            return str(self._parent._name)+':'+str(self._name)
        else:
            return str(self._name)
        #return self._key_attribute
        
    def notifySubscribers(self):
        for s in self._subscribers:
            try:
                s()
            except:
                print "subscriber error"
            
    def subscribe(self,  subscriber):
        self._subscribers.add(subscriber)
        print "subscribed"
        
    def unsubscribe(self,  subscriber):
        self._subscribers.remove(subscriber)
        print "unsubscribed"
    
    def unsubscribeAllRecursive(self):
        self._subscribers=set()
        for c in self._children.values():
            c.unsubscribeAllRecursive()
        
class MsgNode(RootNode):   
    
    def __init__(self, *args,  **kwargs):
        RootNode.__init__(self,  *args,  **kwargs)

        self.trace=[]
        self.max_trace_length=100
        self.last_update=None
        self.update_period=0

        if self._parent is not None:
            self._parent.addChild(self)

    def updateContent(self, content):
        self._content=content
        
        for valueName in content.get_fieldnames():
            value=getattr(content, valueName)
            if not(valueName in self._children.keys()):
                ValueNode(name=valueName, parent=self, content=value)
            self._children[valueName].updateContent(value)             

        update_time=time.time()
        if self.last_update!=None:
            if self.update_period==0:
                self.update_period=(update_time-self.last_update)
            else:
                self.update_period=0.7*self.update_period+0.3*(update_time-self.last_update)
        self.last_update=update_time
        

    def isMessage(self):
        return True

    def displayContent(self):
        if self.last_update!=None and (time.time()-self.last_update)>min(1.5,  2.0*self.update_period+0.3):
            self.update_period=0
        
        if self.update_period==0:
            self._checked=False
            return "inactive"
        else:
            self._checked=True
            return "{:4.1f} Hz".format(1.0/self.update_period)
    
    
    def setChecked(self, state):
        self.content().mavlinkReceiver.requestStream(self.content(),  state)
        self._checked = state

    def  editValue(self,  new_value):
        self.content().mavlinkReceiver.requestStream(self.content(),  True,  new_value)

    
class ParamNode(MsgNode):
    def __init__(self, *args,  **kwargs):
        MsgNode.__init__(self,  *args,  **kwargs)

    def displayContent(self):
        return self._children['param_value'].displayContent()

    def updateContent(self, content):
        MsgNode.updateContent(self,  content)
        self._checked=False

    def setChecked(self, state):
        print "fetching ",  self._children['param_index']._content
        self.content().mavlinkReceiver.master.param_fetch_one(self._children['param_id']._content)
        self._checked = state

    def  editValue(self,  new_value):
        print "change parameter",self._children['param_id'].content()," to ",  new_value
        #self.content().mavlinkReceiver.master.param_set_send(self._children['param_id'].content(),  new_value)
        self.content().mavlinkReceiver.master.mav.param_set_send( self.content().get_srcSystem(), self.content().get_srcComponent(), self._children['param_id'].content(),  new_value, 9)

class ValueNode(RootNode):   
    def __init__(self, *args,  **kwargs):
        RootNode.__init__(self,  *args,  **kwargs)

        self._key_attribute="fieldname"
        self.trace=[]
        self.max_trace_length=100
        self.last_update=None
        self.update_period=0

        if self._parent is not None:
            self._parent.addChild(self)


    def updateContent(self, content):
    #keep traces of scalar values
        if isinstance(content, list):
             for i in range(0,len(content)):
                if not(i in self._children.keys()):
                    ValueNode(name=i,   parent=self, content=content)
                self._children[i].updateContent(content[i])

        if isinstance(self._content, int) or isinstance(self._content, float):
           self.trace.append(content)
           if len(self.trace)>self.max_trace_length:
              self.trace=self.trace[-self.max_trace_length:]
        self._content=content
        self.notifySubscribers()
        

    def displayContent(self):        
        if isinstance(self._content, str) or isinstance(self._content, int) or isinstance(self._content, float):
           return str(self._content)

        return "?"

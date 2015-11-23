import os,  sys

class Instance:
    def __init__(self,  input):
        print input
        if input[0] == "unsigned" or input[0] == "signed":
            self.type_name = input[0]+" "+input[1]
            self.instance_name = input[2]
        if input[0] == "union":
            return
        else:
            self.type_name = input[0]
            self.instance_name = input[1]
            
        self.offset = input[3]
        self.size = input[4]

class ParsedType:
    def __init__(self,  input):
        self.type_name = ""
        if input[0][0]=='struct':
            self.type_name = input[0][1]
        if input[0][0]=='typedef' and input[0][1]=='struct': 
            self.type_name = input[-1][1].split(";")[0]
        self.members = [Instance(x) for x in input[1:-1]]
        self.size = 0
        self.offset = 0

def load_structure(filename,  name):
    cmd = "pahole "+filename+" -a "
    p = os.popen(cmd)
    sloc = p.readlines()
    p.close()
    cleaned = []
    for l in sloc:
        ls = l.strip()
        if not ls.startswith("/*") and not ls=="" and not ls.startswith("(null)"):
            cleaned.append(l.strip().split())
    
    buffer = []
    types = []
    for input in cleaned:
        if input[0]=='struct' or (input[0]=='typedef' and input[1]=='struct'): 
            buffer=[]
        buffer.append(input)
        if input[0].split(";")[0] == "}":
            new_type = ParsedType(buffer)
            types.append(new_type)
            print new_type.type_name
            buffer = []

filename = sys.argv[1]
name=sys.argv[2]
load_structure(filename,  name)

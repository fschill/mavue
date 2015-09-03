import plugins

from elftools.common.py3compat import maxint, bytes2str
from elftools.dwarf.descriptions import describe_form_class
from elftools.elf.elffile import ELFFile

import os

class Debugger(plugins.Plugin):
    def __init__(self):
        self.severity = ["EMERGENCY",  "ALERT",  "CRITICAL",  "ERROR",  "WARNING",  "NOTICE",  "INFO",  "DEBUG_0",  "DEBUG_1",  "DEBUG_2",  "DEBUG_3"]
        self.elf_filename = "/home/felix/Hydromea/AUV_Software/Power/Debug_Linux/Power.elf"
        self.load_elf_file(self.elf_filename)
                
    def filter(self,  message):
        return message.__class__.__name__.startswith("MAVLink_statustext_message")

             
    def run(self,  message): 
        print(self.severity[getattr(message,  "severity")]+"("+str(message._header.srcSystem)+":"+ str(message._header.srcComponent)+"): "+getattr(message,  "text")+"\n" )
        
        text = getattr(message,  "text").split()
        if (len(text)>1 and text[1].startswith("0x8")):
            address = int(text[1],  16)
            #funcname = self.decode_funcname(address)
            #file, line = self.decode_file_line(address)
            self.sys_decode_address(self.elf_filename,  address)
            #if funcname is not None and file is not None:
            #    print ('Function:'+bytes2str(funcname)+' File:', bytes2str(file)+' Line:', line)
    
    def sys_decode_address(self,  filename,  address):
        cmd = 'addr2line -f -e ' + filename +" "+ hex(address)
        p = os.popen(cmd)
        sloc = p.readline() + p.readline()
        print sloc
        p.close()
        
    def load_elf_file(self,  filename):
        print('Processing file:', filename)
        with open(filename, 'rb') as f:
            self.elffile = ELFFile(f)

            if not self.elffile.has_dwarf_info():
                print('  file has no DWARF info')
                return

            # get_dwarf_info returns a DWARFInfo context object, which is the
            # starting point for all DWARF-based processing in pyelftools.
            self.dwarfinfo = self.elffile.get_dwarf_info()

    def decode_funcname(self, address):
        # Go over all DIEs in the DWARF information, looking for a subprogram
        # entry with an address range that includes the given address. Note that
        # this simplifies things by disregarding subprograms that may have
        # split address ranges.
        for CU in self.dwarfinfo.iter_CUs():
            for DIE in CU.iter_DIEs():
                try:
                    if DIE.tag == 'DW_TAG_subprogram':
                        lowpc = DIE.attributes['DW_AT_low_pc'].value

                        # DWARF v4 in section 2.17 describes how to interpret the
                        # DW_AT_high_pc attribute based on the class of its form.
                        # For class 'address' it's taken as an absolute address
                        # (similarly to DW_AT_low_pc); for class 'constant', it's
                        # an offset from DW_AT_low_pc.
                        highpc_attr = DIE.attributes['DW_AT_high_pc']
                        highpc_attr_class = describe_form_class(highpc_attr.form)
                        if highpc_attr_class == 'address':
                            highpc = highpc_attr.value
                        elif highpc_attr_class == 'constant':
                            highpc = lowpc + highpc_attr.value
                        else:
                            print('Error: invalid DW_AT_high_pc class:',
                                  highpc_attr_class)
                            continue

                        if lowpc <= address <= highpc:
                            return DIE.attributes['DW_AT_name'].value
                except KeyError:
                    continue
        return None


    def decode_file_line(self, address):
        # Go over all the line programs in the DWARF information, looking for
        # one that describes the given address.
        
        for CU in self.dwarfinfo.iter_CUs():
            
            # First, look at line programs to find the file/line for the address
            lineprog = self.dwarfinfo.line_program_for_CU(CU)
            prevstate = None
            for entry in lineprog.get_entries():
                # We're interested in those entries where a new state is assigned
                if entry.state is None or entry.state.end_sequence:
                    continue
                # Looking for a range of addresses in two consecutive states that
                # contain the required address.
                if prevstate and prevstate.address <= address < entry.state.address:
                    filename = lineprog['file_entry'][prevstate.file - 1].name
                    line = prevstate.line
                    return  filename, line
                prevstate = entry.state
        return None, None

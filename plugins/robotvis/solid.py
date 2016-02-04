from geometry import *
from numpy import  *
import math
#from gcode import *

#import pyclipper

import multiprocessing as mp
import subprocess
from random import randint

def RandomPoly(maxWidth, maxHeight, vertCnt):
    result = []
    for _ in range(vertCnt):
        result.append(Point(randint(0, maxWidth), randint(0, maxHeight)))
    return result

class facet:
    def __init__(self, normal):
        self.normal=normal;
        self.vertices=[]

    def __eq__(self, of):
        return self.vertices == of.vertices

    def __ne__(self, of):
        return not self.__eq__(of)


def load_stl_file(filename):
    infile = []
    infile = open(filename)

    datalines = infile.readlines();

    last_facet = []
    facets = []
    for l in datalines:
        l_el = l.split();
        if l_el[0] == "facet" and l_el[1] == "normal":
            last_facet = facet([float(x) for x in l_el[2:]])
        elif l_el[0] == "vertex":
            last_facet.vertices.append(array([float(x) / 1.0 for x in l_el[1:]]))
        elif l_el[0] == "endfacet":
            facets.append(last_facet)
            #faces(pos=last_facet.vertices, normal=last_facet.normal)
            last_facet = []
    return facets

class Solid:

    def __init__(self):
        self.map=[]
        self.update_visual=False
        self.refmap=None
        self.material=None
        self.facets=None


    def load(self, filename):
        self.facets=load_stl_file(filename)
        self.get_bounding_box()

    def scale(self, scale_factors):
        for f in self.facets:
            for p in f.vertices:
                p[0]=p[0]*scale_factors[0]
                p[1]=p[1]*scale_factors[1]
                p[2]=p[2]*scale_factors[2]
        self.get_bounding_box()

    def rotate_z(self):
        for f in self.facets:
            for p in f.vertices:
                tmp=p[1]
                p[1]=-p[0]
                p[0]=tmp
                p[2]=p[2]
        self.get_bounding_box()

    def translate(self,  vector):
        for f in self.facets:
            for p in f.vertices:
                p[0]=p[0]+vector[0]
                p[1]=p[1]+vector[1]
                p[2]=p[2]+vector[2]
        self.get_bounding_box()


    def get_bounding_box(self):
        self.minv=self.facets[0].vertices[0]
        self.maxv=self.facets[0].vertices[0]
        self.leftmost_point_facet=self.facets[0]
        self.leftmost_point=self.facets[0].vertices[0]
        for f in self.facets:
            for p in f.vertices:
                self.minv=pmin(self.minv,p)
                self.maxv=pmax(self.maxv,p)
                if p[0]<self.leftmost_point[0]:
                        self.leftmost_point_facet=f
                        self.leftmost_point=p

        self.waterlevel=self.minv[2]

        print self.minv, self.maxv,  "waterlevel",  self.waterlevel

    def add_padding(self, pad3D):
        self.minv[0]-=pad3D[0]
        self.minv[1]-=pad3D[1]
        self.minv[2]-=pad3D[2]
        self.maxv[0]+=pad3D[0]
        self.maxv[1]+=pad3D[1]
        self.maxv[2]+=pad3D[2]




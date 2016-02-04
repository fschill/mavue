import math

from numpy import *

PI=3.1415926

def vec(arr):
	return transpose(matrix(arr))

def norm(u):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]*u[i]
    return float(math.sqrt(tmp))

def dist(u, v):
    return norm([u[i]-v[i] for i in range(0,  len(u))])

def normalize(u):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]**2
    length=float(math.sqrt(tmp))
    return array(u)/length 
    
def scapro(u,  v):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]*v[i]
    return tmp
    
def crossproduct(u,v):
	return array([u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]])

def is_num_equal(a, b,  tolerance=0.0001):
    return abs(a-b)<tolerance

def frange(left, right, step):
    return [left+i*step for i in range(0,int((right-left)/step))]
    
def calc_angle(u,  v):
    s=scapro(normalize(u),  normalize(v))
    #print s
    return math.acos(0.999999*s)
    
def full_angle2d(u,  v):
    nu=0.9999*normalize(u)
    nv=0.9999*normalize(v)
    alpha= math.atan2(nv[1],nv[0]) - math.atan2(nu[1],nu[0])
    while alpha<0: alpha+=2.0*math.pi
    while alpha>=2.0*math.pi: alpha-=2.0*math.pi
    return alpha
    
    
def shares_points(vertices1,  vertices2):
    result=0
    for v1 in vertices1:
        for v2 in vertices2:
            if tuple(v1)==tuple(v2): 
                result+=1
            
    return result

def pmin(x,y):
    return [min(x[i], y[i])for i in range(0,len(x))]

def pmax(x,y):
    return [max(x[i], y[i])for i in range(0,len(x))]

def SameSide(p1,p2, a,b):
    cp1 = crossproduct(b-a, p1-a)
    cp2 = crossproduct(b-a, p2-a)
    return (sp(cp1, cp2) >= 0)

def PointInTriangle(p, vertices):
    a=vec(vertices[0])
    b=vec(vertices[1])
    c=vec(vertices[2])
    return (SameSide(p,a, b,c) and SameSide(p,b, a,c) and SameSide(p,c, a,b))

def getPlaneHeight(location,  triangleVertices):
    a=triangleVertices[0]
    b=triangleVertices[1]
    c=triangleVertices[2]
    l=location

    denom=((b[1] - c[1])*(a[0] - c[0]) + (c[0] - b[0])*(a[1] - c[1]))
    #if is_num_equal(denom,  0.0,  0.000001):
    if denom==0.0:
        return False,  [0, 0, 0],  False
        
    u = ((b[1] - c[1])*(l[0] - c[0]) + (c[0] - b[0])*(l[1] - c[1])) / denom
    v = ((c[1] - a[1])*(l[0] - c[0]) + (a[0] - c[0])*(l[1] - c[1])) / denom
    w = 1.0 - u - v;
    # Check if point is in triangle
    inTriangle=False
    onEdge=False
    if (u >= 0.0) and (v >= 0.0) and (w >=0.0):
        inTriangle=True
        onEdge=is_num_equal(abs(u)+abs(v)+abs(w),  0.0,  0.00000001)
    projectedPoint=[u*a[0]+v*b[0]+ w*c[0],  u*a[1]+v*b[1]+w*c[1],  u*a[2]+v*b[2] +w*c[2]]
    
    return inTriangle,  projectedPoint,  onEdge

def closestPointOnLineSegment2D(a,  b,  x,  y):
    ab=[b[0]-a[0],  b[1]-a[1],  b[2]-a[2]]
    pa=[x-a[0],  y-a[1]]
    if ab[0]==0.0 and ab[1]==0.0:
        return [a[0],  a[1],  max(a[2],  b[2])]
    
    t= (ab[0]*pa[0]+ab[1]*pa[1]) / (ab[0]*ab[0]+ab[1]*ab[1])
    t=max(0.0,  min(1.0,  t))
    return [a[0]+t*ab[0],  a[1]+t*ab[1],  a[2]+t*ab[2]]
    

def closestPointOnLineSegment(a,  b,  p):
    ab=[b[0]-a[0],  b[1]-a[1],  b[2]-a[2]]
    pa=[p[0]-a[0],  p[1]-a[1], p[2]-a[2]]

    ab_sp=(ab[0]*ab[0]+ab[1]*ab[1]+ab[2]*ab[2])
    if ab_sp==0.0:
        return a
    
    t= (ab[0]*pa[0]+ab[1]*pa[1]+ab[2]*pa[2]) / ab_sp
    t=max(0.0,  min(1.0,  t))
    return [a[0]+t*ab[0],  a[1]+t*ab[1],  a[2]+t*ab[2]]

def dropSphereLine(a, b,  p,  r):

    #assume that a=(0,0,0) and transform everything into that frame of reference:
    #line vector:
    u=(b[0]-a[0])
    v=(b[1]-a[1])
    w=(b[2]-a[2])
    x=(p[0]-a[0])
    y=(p[1]-a[1])
    #solve for z (positive sqrt is sufficient)
    squared=-(u**2+v**2+w**2) * (-r**2 *u**2-r**2 *v**2+u**2 *y**2 - 2 * u *v*x*y+v**2* x**2)
    if squared>=0 and (u**2+v**2)!=0.0:
        z = (math.sqrt(squared)+u* w *x+v *w *y)/(u**2+v**2)
        m=(u*x+v*y+w*z) / (u**2+v**2+w**2)
        if (m>=0) and (m<=1): 
            return True,  z+a[2]-r
    
    return False,  0
    
    
def dropSpherePoint(v,  x,  y,  radius):
    dx=(v[0]-x)
    dy=(v[1]-y)
    rs=radius*radius
    r2ds=dx*dx+dy*dy

    if r2ds<=rs:
        h=math.sqrt(rs-r2ds)
        pp=v[2]+h-radius
        return True,  pp
    else:
        return False,  0


class normalset:
    def __init__(self):
        self.normals=[];
        self.avg_normal=[0,0,0]
    def calcNormal(self):
        self.avg_normal=array([0.0,0.0,0.0], 'float')
        c=0
        for n in self.normals:
            self.avg_normal=self.avg_normal+array(n,'float')
            c=c+1
        self.avg_normal=[x/float(c) for x in self.avg_normal]
        return self.avg_normal

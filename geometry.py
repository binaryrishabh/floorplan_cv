from __future__ import annotations
import math
import numpy as np


def dist(a,b):
    return math.hypot(a.x-b.x, a.y-b.y)


def fit_circle(points):
    arr=np.asarray(points,dtype=float)
    if len(arr)<3:
        return None
    x=arr[:,0]; y=arr[:,1]
    A=np.column_stack([2*x,2*y,np.ones_like(x)])
    rhs=x*x+y*y
    try:
        cx,cy,c=np.linalg.lstsq(A,rhs,rcond=None)[0]
    except np.linalg.LinAlgError:
        return None
    r2=cx*cx+cy*cy+c
    if r2<=0:
        return None
    r=math.sqrt(r2)
    d=np.sqrt((x-cx)**2+(y-cy)**2)
    rms=float(np.sqrt(np.mean((d-r)**2)))
    return float(cx),float(cy),float(r),rms


def minimal_angular_span(points,cx,cy):
    a=np.mod(np.degrees(np.arctan2(points[:,1]-cy,points[:,0]-cx)),360.0)
    a=np.sort(a)
    if len(a)<2:
        return 0.0
    gaps=np.diff(np.r_[a,a[0]+360.0])
    return float(360.0-np.max(gaps))

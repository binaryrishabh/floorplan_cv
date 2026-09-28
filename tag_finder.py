from __future__ import annotations
import math
import pymupdf
from config import TAG_PATTERN, TAG_RADIUS_FT, TAG_DEDUPE_PT


def _small_curve_rects(drawings):
    """Paper-space evidence for the small rounded/capsule door-number badge."""
    rects=[]
    for d in drawings:
        rect=d.get('rect')
        if rect is None: continue
        width=float(d.get('width',0.0) or 0.0)
        if width>0.55: continue
        # Badge geometry is plotted at annotation size, independent of plan scale.
        if max(rect.width,rect.height)>52 or min(rect.width,rect.height)>26: continue
        count=sum(1 for it in d.get('items',[]) if it[0]=='c')
        if count: rects.append((rect,count))
    return rects


def find_candidates(spans,drawings):
    curve_rects=_small_curve_rects(drawings); out=[]
    for s in spans:
        if not TAG_PATTERN.match(s['text']): continue
        if not (6.0<=s['size']<=18.0): continue
        area=pymupdf.Rect(s['bbox'])+(-20,-20,20,20)
        evidence=sum(count for rect,count in curve_rects if rect.intersects(area))
        if evidence<2: continue
        if any(e['text']==s['text'] and math.hypot(e['x']-s['x'],e['y']-s['y'])<=TAG_DEDUPE_PT for e in out):
            continue
        out.append({'text':s['text'],'x':s['x'],'y':s['y'],'size':s['size'],'bbox':s['bbox'],'curve_evidence':evidence})
    return out


def attach_tags(doors,candidates,points_per_foot=18.0):
    radius=TAG_RADIUS_FT*points_per_foot
    assignments=[]
    for di,d in enumerate(doors):
        dx=d.get('hinge_x',d['x']); dy=d.get('hinge_y',d['y'])
        for ci,c in enumerate(candidates):
            distance=math.hypot(dx-c['x'],dy-c['y'])
            if distance<=radius: assignments.append((distance,di,ci))
    used_d=set();used_c=set()
    for distance,di,ci in sorted(assignments):
        if di in used_d or ci in used_c: continue
        c=candidates[ci]
        doors[di]['tag']=c['text']; doors[di]['tag_distance']=round(distance,1)
        doors[di]['tag_x']=round(c['x'],2); doors[di]['tag_y']=round(c['y'],2)
        used_d.add(di);used_c.add(ci)
    return doors

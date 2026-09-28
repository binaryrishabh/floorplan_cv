from __future__ import annotations
import math
from collections import defaultdict
import numpy as np

from config import (
    ARC_SEG_MIN_FT, ARC_SEG_MAX_FT, ARC_STROKE_MAX_PT,
    ARC_COMPONENT_MIN_SEGMENTS, ARC_COMPONENT_MAX_SEGMENTS,
    DOOR_LEAF_MIN_FT, DOOR_LEAF_MAX_FT, ARC_SPAN_MIN_DEG, ARC_SPAN_MAX_DEG,
    ARC_RMS_MAX_FT, ENDPOINT_SNAP_FT, LEAF_CENTER_TOL_FT, LEAF_ENDPOINT_TOL_FT,
    LEAF_RATIO_MIN, LEAF_RATIO_MAX, DOOR_CENTER_DEDUPE_FT, DOOR_RADIUS_DEDUPE_FT,
    LEAF_STROKE_MIN_PT, LEAF_STROKE_MAX_PT, TAG_AXIS_LEAF_MAX_DIST_FT,
    TAG_DIAG_LEAF_MAX_DIST_FT, LEAF_DUP_MID_FT, LEAF_DUP_LEN_FT,
    LEAF_DUP_ANGLE_DEG, DIAG_ANGLE_MARGIN_DEG, DOUBLE_PAIR_MAX_MID_DIST_FT,
    DOUBLE_PAIR_MAX_ENDPOINT_GAP_FT, FALLBACK_DOOR_DEDUPE_FT,
)
from geometry import fit_circle, minimal_angular_span, dist


def _th(ft, ppf): return ft * ppf

def _key(pt, snap):
    return (round(pt.x/snap), round(pt.y/snap))


def _collect_lines(drawings, ppf):
    all_lines=[]; arc_segments=[]
    lo=_th(ARC_SEG_MIN_FT,ppf); hi=_th(ARC_SEG_MAX_FT,ppf)
    for path_idx,d in enumerate(drawings):
        width=float(d.get('width',0.0) or 0.0)
        for item in d.get('items',[]):
            if item[0] != 'l' or len(item)<3: continue
            p,q=item[1],item[2]; L=dist(p,q)
            rec={'path':path_idx,'p':p,'q':q,'length':L,'width':width}
            all_lines.append(rec)
            if lo <= L <= hi and width <= ARC_STROKE_MAX_PT:
                arc_segments.append(rec)
    return all_lines,arc_segments


def _components(segments, snap):
    endpoint_map=defaultdict(list)
    for i,s in enumerate(segments):
        endpoint_map[_key(s['p'],snap)].append(i)
        endpoint_map[_key(s['q'],snap)].append(i)
    seen=set(); comps=[]
    for i in range(len(segments)):
        if i in seen: continue
        stack=[i]; seen.add(i); comp=[]
        while stack:
            j=stack.pop(); comp.append(j); s=segments[j]
            for pt in (s['p'],s['q']):
                for k in endpoint_map[_key(pt,snap)]:
                    if k not in seen:
                        seen.add(k); stack.append(k)
        comps.append(comp)
    return comps


def _component_points(comp,segments):
    seen=set(); pts=[]
    for idx in comp:
        s=segments[idx]
        for p in (s['p'],s['q']):
            k=(round(p.x,3),round(p.y,3))
            if k not in seen:
                seen.add(k); pts.append((p.x,p.y))
    return np.asarray(pts,dtype=float)


def _component_endpoints(comp,segments,snap):
    counts=defaultdict(int); points={}
    for idx in comp:
        s=segments[idx]
        for p in (s['p'],s['q']):
            k=_key(p,snap); counts[k]+=1; points[k]=p
    return [points[k] for k,n in counts.items() if n==1]


def _sample_cubic(p0,p1,p2,p3,n=17):
    ts=np.linspace(0.0,1.0,n)
    out=[]
    for t in ts:
        u=1-t
        x=u**3*p0.x+3*u*u*t*p1.x+3*u*t*t*p2.x+t**3*p3.x
        y=u**3*p0.y+3*u*u*t*p1.y+3*u*t*t*p2.y+t**3*p3.y
        out.append((x,y))
    return np.asarray(out,float)


def _curve_arc_candidates(drawings, ppf):
    """Support CAD/PDF exports that keep door arcs as cubic Béziers."""
    rmin=_th(DOOR_LEAF_MIN_FT,ppf); rmax=_th(DOOR_LEAF_MAX_FT,ppf)
    rmsmax=_th(ARC_RMS_MAX_FT,ppf)
    out=[]
    for path_idx,d in enumerate(drawings):
        chunks=[]
        for it in d.get('items',[]):
            if it[0]=='c' and len(it)>=5:
                chunks.append(_sample_cubic(it[1],it[2],it[3],it[4]))
        if not chunks: continue
        pts=np.vstack(chunks)
        fit=fit_circle(pts)
        if fit is None: continue
        cx,cy,r,rms=fit
        if not (rmin<=r<=rmax) or rms>rmsmax: continue
        span=minimal_angular_span(pts,cx,cy)
        if not (ARC_SPAN_MIN_DEG<=span<=ARC_SPAN_MAX_DEG): continue
        # extrema of ordered cubic sample approximate arc endpoints.
        endpoints=[]
        for chunk in chunks:
            endpoints.extend([chunk[0],chunk[-1]])
        # choose farthest endpoint pair around the fitted circle.
        best=None
        for i in range(len(endpoints)):
            for j in range(i+1,len(endpoints)):
                a,b=endpoints[i],endpoints[j]
                dd=float(np.hypot(*(a-b)))
                if best is None or dd>best[0]: best=(dd,a,b)
        if best:
            class P:
                def __init__(self,a): self.x=float(a[0]); self.y=float(a[1])
            eps=[P(best[1]),P(best[2])]
            out.append({'cx':cx,'cy':cy,'radius':r,'rms':rms,'span':span,'endpoints':eps,'segments':len(chunks),'source':'bezier_arc'})
    return out


def _leaf_for_arc(cx,cy,radius,endpoints,all_lines,ppf):
    best=None; best_cost=1e9
    center_tol=_th(LEAF_CENTER_TOL_FT,ppf); endpoint_tol=_th(LEAF_ENDPOINT_TOL_FT,ppf)
    for ln in all_lines:
        ratio=ln['length']/radius if radius else 99
        if not (LEAF_RATIO_MIN <= ratio <= LEAF_RATIO_MAX): continue
        # Exclude extremely heavy wall strokes, but do not assume one exact CAD lineweight.
        if ln['width'] > 2.0: continue
        for near,far in ((ln['p'],ln['q']),(ln['q'],ln['p'])):
            dc=math.hypot(near.x-cx,near.y-cy)
            if dc>center_tol: continue
            de=min(math.hypot(far.x-e.x,far.y-e.y) for e in endpoints)
            if de>endpoint_tol: continue
            stroke_bonus=0.0
            if LEAF_STROKE_MIN_PT <= ln['width'] <= LEAF_STROKE_MAX_PT: stroke_bonus=0.25
            cost=abs(1.0-ratio)*4.0 + dc/max(center_tol,1e-6) + de/max(endpoint_tol,1e-6) - stroke_bonus
            if cost<best_cost:
                best_cost=cost; best=(ln,near,far)
    return best


def _dedupe(doors,ppf):
    kept=[]; ctol=_th(DOOR_CENTER_DEDUPE_FT,ppf); rtol=_th(DOOR_RADIUS_DEDUPE_FT,ppf)
    def quality(d):
        rms=d.get('arc_rms')
        if rms is None: rms=999
        span=d.get('span_deg')
        if span is None: span=0
        return (rms,abs(span-90.0))
    for d in sorted(doors,key=quality):
        if any(math.hypot(d['hinge_x']-k['hinge_x'],d['hinge_y']-k['hinge_y'])<=ctol and abs(d['radius']-k['radius'])<=rtol for k in kept):
            continue
        kept.append(d)
    return kept


def _line_arc_candidates(arc_segments,ppf):
    snap=max(0.04,_th(ENDPOINT_SNAP_FT,ppf)); comps=_components(arc_segments,snap)
    rmin=_th(DOOR_LEAF_MIN_FT,ppf); rmax=_th(DOOR_LEAF_MAX_FT,ppf); rmsmax=_th(ARC_RMS_MAX_FT,ppf)
    out=[]
    for comp in comps:
        if not (ARC_COMPONENT_MIN_SEGMENTS <= len(comp) <= ARC_COMPONENT_MAX_SEGMENTS): continue
        pts=_component_points(comp,arc_segments)
        if len(pts)<6: continue
        fit=fit_circle(pts)
        if fit is None: continue
        cx,cy,radius,rms=fit
        if not (rmin<=radius<=rmax) or rms>rmsmax: continue
        span=minimal_angular_span(pts,cx,cy)
        if not (ARC_SPAN_MIN_DEG<=span<=ARC_SPAN_MAX_DEG): continue
        endpoints=_component_endpoints(comp,arc_segments,snap)
        if len(endpoints)!=2: continue
        out.append({'cx':cx,'cy':cy,'radius':radius,'rms':rms,'span':span,'endpoints':endpoints,'segments':len(comp),'source':'polyline_arc'})
    return out


def find_doors(drawings, points_per_foot=18.0):
    ppf=points_per_foot
    all_lines,arc_segments=_collect_lines(drawings,ppf)
    arcs=_line_arc_candidates(arc_segments,ppf) + _curve_arc_candidates(drawings,ppf)
    doors=[]
    for arc in arcs:
        leaf=_leaf_for_arc(arc['cx'],arc['cy'],arc['radius'],arc['endpoints'],all_lines,ppf)
        if leaf is None: continue
        ln,near,far=leaf
        mx=(near.x+far.x)/2.0; my=(near.y+far.y)/2.0
        doors.append({
            'hinge_x':round(arc['cx'],2),'hinge_y':round(arc['cy'],2),
            'x':round(mx,2),'y':round(my,2),'radius':round(arc['radius'],2),
            'span_deg':round(arc['span'],2),'arc_rms':round(arc['rms'],3),
            'arc_segments':arc['segments'],'leaf_length':round(ln['length'],2),
            'leaf_width':round(ln['width'],2),'tag':None,'tag_distance':None,
            'method':'swing_arc','arc_source':arc['source'],
            'width_ft':round(arc['radius']/ppf,3),
        })
    return _dedupe(doors,ppf)


def _ang_diff(a,b):
    d=abs(a-b)%180.0; return min(d,180.0-d)


def _infer_leaf_band(existing_doors):
    widths=[d.get('leaf_width') for d in existing_doors if d.get('leaf_width') and d.get('method')=='swing_arc']
    if widths:
        # Robust mode rounded to 0.05 pt. Accepted swing geometry tells us this export's door-leaf lineweight.
        buckets={}
        for w in widths:
            k=round(float(w)/0.05)*0.05; buckets[k]=buckets.get(k,0)+1
        mode=max(buckets.items(),key=lambda kv:kv[1])[0]
        return max(0.05,mode-0.16), mode+0.16
    return LEAF_STROKE_MIN_PT, LEAF_STROKE_MAX_PT


def _leaf_lines(drawings,ppf,stroke_band=None):
    raw=[]; lo=_th(DOOR_LEAF_MIN_FT,ppf); hi=_th(DOOR_LEAF_MAX_FT,ppf)
    if stroke_band is None: stroke_band=(LEAF_STROKE_MIN_PT,LEAF_STROKE_MAX_PT)
    swlo,swhi=stroke_band
    for path_idx,d in enumerate(drawings):
        width=float(d.get('width',0.0) or 0.0)
        if not (swlo <= width <= swhi): continue
        for it in d.get('items',[]):
            if it[0]!='l' or len(it)<3: continue
            a,b=it[1],it[2]; length=dist(a,b)
            if not (lo<=length<=hi): continue
            mx,my=(a.x+b.x)/2.0,(a.y+b.y)/2.0
            angle=math.degrees(math.atan2(b.y-a.y,b.x-a.x))%180.0
            raw.append({'path':path_idx,'a':a,'b':b,'x':mx,'y':my,'length':length,'width':width,'angle':angle})
    kept=[]; midtol=_th(LEAF_DUP_MID_FT,ppf); lentol=_th(LEAF_DUP_LEN_FT,ppf)
    for ln in sorted(raw,key=lambda z:(-(LEAF_STROKE_MIN_PT<=z['width']<=LEAF_STROKE_MAX_PT),-z['width'],z['path'])):
        if any(math.hypot(ln['x']-k['x'],ln['y']-k['y'])<=midtol and abs(ln['length']-k['length'])<=lentol and _ang_diff(ln['angle'],k['angle'])<=LEAF_DUP_ANGLE_DEG for k in kept):
            continue
        kept.append(ln)
    return kept


def _is_diagonal(angle):
    a=angle%180.0; m=DIAG_ANGLE_MARGIN_DEG
    return (m<a<90.0-m) or (90.0+m<a<180.0-m)


def _used_tag(candidate,doors):
    for d in doors:
        if d.get('tag_x') is not None and math.hypot(d['tag_x']-candidate['x'],d['tag_y']-candidate['y'])<=2.0:
            return True
    return False


def _door_near(x,y,doors,ppf,tol_ft=FALLBACK_DOOR_DEDUPE_FT):
    tol=_th(tol_ft,ppf)
    return any(math.hypot(d['x']-x,d['y']-y)<=tol for d in doors)


def find_tag_leaf_doors(drawings,tag_candidates,existing_doors,points_per_foot=18.0):
    ppf=points_per_foot; leaves=_leaf_lines(drawings,ppf,_infer_leaf_band(existing_doors)); out=[]
    axis_lim=_th(TAG_AXIS_LEAF_MAX_DIST_FT,ppf); diag_lim=_th(TAG_DIAG_LEAF_MAX_DIST_FT,ppf)
    # Common physical leaf widths, only a soft prior.
    common=(2.0,2.5,2.75,3.0,3.25,3.5,4.0,4.5,5.0)
    for tag in tag_candidates:
        if _used_tag(tag,existing_doors+out): continue
        scored=[]
        for ln in leaves:
            d=math.hypot(ln['x']-tag['x'],ln['y']-tag['y'])
            limit=diag_lim if _is_diagonal(ln['angle']) else axis_lim
            if d>limit: continue
            width_ft=ln['length']/ppf
            width_pen=min(abs(width_ft-w) for w in common)*ppf*0.08
            stroke_pen=0.0 if LEAF_STROKE_MIN_PT<=ln['width']<=LEAF_STROKE_MAX_PT else 0.35*ppf
            scored.append((d+width_pen+stroke_pen,ln))
        if not scored: continue
        _,ln=min(scored,key=lambda z:z[0])
        if _door_near(ln['x'],ln['y'],existing_doors+out,ppf): continue
        da=math.hypot(ln['a'].x-tag['x'],ln['a'].y-tag['y']); db=math.hypot(ln['b'].x-tag['x'],ln['b'].y-tag['y'])
        ref=ln['a'] if da<=db else ln['b']
        out.append({
            'hinge_x':round(ref.x,2),'hinge_y':round(ref.y,2),'x':round(ln['x'],2),'y':round(ln['y'],2),
            'radius':round(ln['length'],2),'span_deg':None,'arc_rms':None,'arc_segments':0,
            'leaf_length':round(ln['length'],2),'leaf_width':round(ln['width'],2),
            'tag':tag['text'],'tag_distance':round(math.hypot(ln['x']-tag['x'],ln['y']-tag['y']),1),
            'tag_x':round(tag['x'],2),'tag_y':round(tag['y'],2),'method':'tag_leaf','leaf_angle':round(ln['angle'],1),
            'width_ft':round(ln['length']/ppf,3),
        })
    return out


def _endpoint_min_distance(a,b):
    return min(math.hypot(p.x-q.x,p.y-q.y) for p in (a['a'],a['b']) for q in (b['a'],b['b']))


def find_untagged_double_doors(drawings,existing_doors,points_per_foot=18.0):
    ppf=points_per_foot
    leaves=[ln for ln in _leaf_lines(drawings,ppf,_infer_leaf_band(existing_doors)) if _is_diagonal(ln['angle'])]
    leaves=[ln for ln in leaves if not _door_near(ln['x'],ln['y'],existing_doors,ppf,0.7)]
    max_mid=_th(DOUBLE_PAIR_MAX_MID_DIST_FT,ppf); max_gap=_th(DOUBLE_PAIR_MAX_ENDPOINT_GAP_FT,ppf)
    used=set(); out=[]
    for i,a in enumerate(leaves):
        if i in used: continue
        best=None
        for j in range(i+1,len(leaves)):
            if j in used: continue
            b=leaves[j]
            if abs(a['length']-b['length'])>_th(0.5,ppf): continue
            ad=_ang_diff(a['angle'],b['angle'])
            if not (45.0<=ad<=135.0): continue
            md=math.hypot(a['x']-b['x'],a['y']-b['y'])
            if md>max_mid: continue
            eg=_endpoint_min_distance(a,b)
            if eg>max_gap: continue
            score=eg+0.15*md+abs(a['length']-b['length'])
            if best is None or score<best[0]: best=(score,j,b)
        if best is None: continue
        _,j,b=best; used.add(i);used.add(j)
        x=(a['x']+b['x'])/2.0; y=(a['y']+b['y'])/2.0
        if _door_near(x,y,existing_doors+out,ppf): continue
        avg=(a['length']+b['length'])/2.0
        out.append({'hinge_x':round(x,2),'hinge_y':round(y,2),'x':round(x,2),'y':round(y,2),
                    'radius':round(avg,2),'span_deg':None,'arc_rms':None,'arc_segments':0,
                    'leaf_length':round(avg,2),'leaf_width':round(max(a['width'],b['width']),2),
                    'tag':None,'tag_distance':None,'method':'double_leaf','width_ft':round(avg/ppf,3)})
    return out


def merge_door_sets(*sets,points_per_foot=18.0):
    ppf=points_per_foot; out=[]; priority={'swing_arc':0,'tag_leaf':1,'double_leaf':2}
    flat=[]
    for s in sets: flat.extend(s)
    tol=_th(FALLBACK_DOOR_DEDUPE_FT,ppf)
    for d in sorted(flat,key=lambda z:priority.get(z.get('method','swing_arc'),9)):
        near=[k for k in out if math.hypot(d['x']-k['x'],d['y']-k['y'])<=tol]
        if near:
            if d.get('tag'):
                for k in near:
                    if not k.get('tag'):
                        for key in ('tag','tag_distance','tag_x','tag_y'):
                            if key in d: k[key]=d[key]
                        break
            continue
        out.append(d)
    return out

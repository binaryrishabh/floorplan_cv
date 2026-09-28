from __future__ import annotations
import math
from collections import defaultdict
import numpy as np

from config import (
    REG_MIN_SHARED_TAGS, REG_MAX_TAG_RESIDUAL_FT, CROSS_SHEET_MATCH_FT,
    CROSS_SHEET_RADIUS_RATIO_TOL, REG_SCALE_RATIO_TOL,
)


class DSU:
    def __init__(self,n): self.p=list(range(n)); self.r=[0]*n
    def find(self,x):
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]]; x=self.p[x]
        return x
    def union(self,a,b):
        a=self.find(a);b=self.find(b)
        if a==b:return
        if self.r[a]<self.r[b]:a,b=b,a
        self.p[b]=a
        if self.r[a]==self.r[b]:self.r[a]+=1


def _same_level(a,b):
    la=a.get('level'); lb=b.get('level')
    if la and lb: return la==lb
    # Unknown levels are not safe to reconcile across sheets.
    return False


def _similarity(src,dst):
    """Least-squares 2D similarity transform src -> dst."""
    src=np.asarray(src,float); dst=np.asarray(dst,float)
    if len(src)<2:return None
    ms=src.mean(axis=0); md=dst.mean(axis=0)
    X=src-ms; Y=dst-md
    var=float((X*X).sum())
    if var<1e-9:return None
    H=X.T@Y
    U,S,Vt=np.linalg.svd(H)
    R=Vt.T@U.T
    if np.linalg.det(R)<0:
        Vt[-1,:]*=-1; R=Vt.T@U.T
    scale=float(S.sum()/var)
    t=md-scale*(R@ms)
    return scale,R,t


def _apply(T,p):
    s,R,t=T; v=s*(R@np.asarray(p,float))+t
    return float(v[0]),float(v[1])


def _fit_registration(pairs,ppf_target,expected_scale):
    """Small deterministic RANSAC over tag correspondences."""
    if len(pairs)<REG_MIN_SHARED_TAGS:return None
    tol=REG_MAX_TAG_RESIDUAL_FT*ppf_target
    candidates=[]
    n=len(pairs)
    for i in range(n):
        for j in range(i+1,n):
            src=[pairs[i][1],pairs[j][1]]; dst=[pairs[i][0],pairs[j][0]]
            T=_similarity(src,dst)
            if T is None:continue
            if expected_scale>0 and abs(T[0]/expected_scale-1.0)>REG_SCALE_RATIO_TOL:continue
            residuals=[]; inliers=[]
            for k,(a,b,tag) in enumerate(pairs):
                x,y=_apply(T,b); r=math.hypot(x-a[0],y-a[1]); residuals.append(r)
                if r<=tol:inliers.append(k)
            if len(inliers)>=REG_MIN_SHARED_TAGS:
                candidates.append((len(inliers),-sum(residuals[k] for k in inliers),inliers,T))
    if not candidates:return None
    _,_,inliers,T=max(candidates,key=lambda x:(x[0],x[1]))
    src=[pairs[k][1] for k in inliers]; dst=[pairs[k][0] for k in inliers]
    refined=_similarity(src,dst) or T
    residuals=[]
    for k in inliers:
        a,b,_=pairs[k]; x,y=_apply(refined,b); residuals.append(math.hypot(x-a[0],y-a[1]))
    return {'transform':refined,'inliers':len(inliers),'rms':float(np.sqrt(np.mean(np.square(residuals)))) if residuals else 0.0}


def reconcile(pages,meta,anchors=None):
    anchors=anchors or {}
    # Flatten detections.
    flat=[]; ids_by_page=defaultdict(list)
    for pno,doors in pages.items():
        for di,d in enumerate(doors):
            idx=len(flat); flat.append((pno,di,d)); ids_by_page[pno].append(idx)
    dsu=DSU(len(flat))

    # Strong first pass: same verified door tag across different sheets on same level.
    by_tag=defaultdict(list)
    for idx,(pno,di,d) in enumerate(flat):
        if d.get('tag'):
            level=meta[pno].get('level')
            if level: by_tag[(level,d['tag'])].append(idx)
    for key,ids in by_tag.items():
        pages_seen=defaultdict(list)
        for idx in ids: pages_seen[flat[idx][0]].append(idx)
        pnos=list(pages_seen)
        for i in range(len(pnos)):
            for j in range(i+1,len(pnos)):
                # If a tag is duplicated within a page, don't guess which instance matches.
                if len(pages_seen[pnos[i]])==1 and len(pages_seen[pnos[j]])==1:
                    dsu.union(pages_seen[pnos[i]][0],pages_seen[pnos[j]][0])

    # Register overlapping sheets using shared unique tags, then reconcile untagged/tag-missing doors spatially.
    registrations=[]
    pnos=sorted(pages)
    for ai in range(len(pnos)):
        pa=pnos[ai]
        for bi in range(ai+1,len(pnos)):
            pb=pnos[bi]
            if not _same_level(meta[pa],meta[pb]):continue
            taga=defaultdict(list); tagb=defaultdict(list)
            for idx in ids_by_page[pa]:
                d=flat[idx][2]
                if d.get('tag'):taga[d['tag']].append(d)
            for idx in ids_by_page[pb]:
                d=flat[idx][2]
                if d.get('tag'):tagb[d['tag']].append(d)
            door_pairs=[]
            for tag in sorted(set(taga)&set(tagb)):
                if len(taga[tag])==1 and len(tagb[tag])==1:
                    da,db=taga[tag][0],tagb[tag][0]
                    door_pairs.append(((da['x'],da['y']),(db['x'],db['y']),'door:'+tag))
            # Text anchors (typically room numbers) are used only to estimate a page-to-page
            # transform. They never create or count a door by themselves.
            anchor_pairs=[]
            aa=anchors.get(pa,{}) ; ab=anchors.get(pb,{})
            for tag in sorted(set(aa)&set(ab)):
                anchor_pairs.append((aa[tag],ab[tag],'text:'+tag))
            ppf_a=meta[pa]['points_per_foot']; ppf_b=meta[pb]['points_per_foot']
            expected=ppf_a/ppf_b
            reg=None; basis=None; pair_count=0
            if len(door_pairs)>=REG_MIN_SHARED_TAGS:
                reg=_fit_registration(door_pairs,ppf_a,expected); basis='door_tags'; pair_count=len(door_pairs)
            # For overall-vs-enlarged or weakly-overlapping sheets, room/equipment text anchors
            # provide the registration. Require >=3 inliers to avoid an accidental two-point fit.
            if reg is None and len(anchor_pairs)>=3:
                cand=_fit_registration(anchor_pairs,ppf_a,expected)
                if cand is not None and cand['inliers']>=3:
                    reg=cand; basis='text_anchors'; pair_count=len(anchor_pairs)
            if reg is None:continue
            T=reg['transform']; tol=CROSS_SHEET_MATCH_FT*ppf_a
            matched=0
            for ib in ids_by_page[pb]:
                db=flat[ib][2]; tx,ty=_apply(T,(db['x'],db['y']))
                best=None
                for ia in ids_by_page[pa]:
                    da=flat[ia][2]
                    if da.get('tag') and db.get('tag') and da['tag']!=db['tag']:continue
                    dist=math.hypot(tx-da['x'],ty-da['y'])
                    if dist>tol:continue
                    wa=da.get('width_ft') or (da.get('radius',0)/ppf_a)
                    wb=db.get('width_ft') or (db.get('radius',0)/ppf_b)
                    if wa and wb and abs(wa-wb)/max(wa,wb)>CROSS_SHEET_RADIUS_RATIO_TOL:continue
                    if best is None or dist<best[0]:best=(dist,ia)
                if best is not None:
                    dsu.union(best[1],ib); matched+=1
            registrations.append({
                'page_a':pa,'page_b':pb,'basis':basis,'correspondences':pair_count,'inliers':reg['inliers'],
                'rms_ft':round(reg['rms']/ppf_a,3),'scale':round(T[0],5),'matched_doors':matched,
            })

    groups=defaultdict(list)
    for i in range(len(flat)):groups[dsu.find(i)].append(i)
    method_rank={'swing_arc':0,'tag_leaf':1,'double_leaf':2}
    project=[]
    for gid,ids in groups.items():
        members=[]
        for idx in ids:
            pno,di,d=flat[idx]
            members.append({'page':pno,'sheet':meta[pno].get('sheet_number'),'level':meta[pno].get('level'),
                            'area':meta[pno].get('area'),'tag':d.get('tag'),'method':d.get('method'),'x':d['x'],'y':d['y']})
        # Prefer more detailed scale, then stronger geometry, then tagged detection.
        rep_idx=min(ids,key=lambda idx:(-meta[flat[idx][0]]['points_per_foot'],method_rank.get(flat[idx][2].get('method'),9),0 if flat[idx][2].get('tag') else 1))
        rp,_,rd=flat[rep_idx]
        tags=sorted({flat[idx][2].get('tag') for idx in ids if flat[idx][2].get('tag')})
        project.append({'project_id':len(project)+1,'level':meta[rp].get('level'),'tag':tags[0] if len(tags)==1 else None,
                        'tag_candidates':tags,'representative_page':rp,'width_ft':rd.get('width_ft'),
                        'method':rd.get('method'),'appearances':len(ids),'members':members})
    project.sort(key=lambda x:(str(x.get('level')),str(x.get('tag') or ''),x['representative_page'],x['project_id']))
    for i,p in enumerate(project,1):p['project_id']=i

    # Source hierarchy: the most detailed floor-plan scale available for a level is
    # authoritative. Lower-detail overall views still help registration and QA, but
    # unmatched detections on them are review candidates instead of silently inflating
    # the project count. If a level has only one scale, that scale is authoritative.
    level_max_ppf={}
    for pno,m in meta.items():
        lv=m.get('level') or 'unknown'; level_max_ppf[lv]=max(level_max_ppf.get(lv,0.0),m['points_per_foot'])
    counted=[]; secondary_review=[]
    for p in project:
        lv=p.get('level') or 'unknown'; mx=level_max_ppf.get(lv,0.0)
        member_ppf=[meta[m['page']]['points_per_foot'] for m in p['members']]
        has_primary=any(v>=0.90*mx for v in member_ppf) if mx else True
        if has_primary:
            p['count_status']='counted'; counted.append(p)
        else:
            p['count_status']='secondary_only_review'; secondary_review.append(p)
    by_level=defaultdict(int)
    for p in counted:by_level[p.get('level') or 'unknown']+=1
    repeated={p['project_id']:p['appearances'] for p in counted if p['appearances']>1}

    # Accounting is deliberately explicit. There are three distinct stages:
    #   sheet appearances -> cross-sheet groups -> authoritative project doors.
    # A group can be withheld from the auto-count when it exists only on a
    # lower-detail secondary view. Those are review items, not duplicates.
    appearance_count=len(flat)
    reconciled_group_count=len(project)
    duplicate_appearances_merged=appearance_count-reconciled_group_count
    secondary_only_review_count=len(secondary_review)
    auto_counted_project_doors=len(counted)

    # These invariants make reporting bugs fail loudly instead of producing
    # arithmetic that looks contradictory in the CLI / summary JSON.
    assert appearance_count == duplicate_appearances_merged + reconciled_group_count
    assert reconciled_group_count == auto_counted_project_doors + secondary_only_review_count

    return {
        # Backward-compatible field names.
        'appearance_count':appearance_count,
        'unique_project_doors':auto_counted_project_doors,
        'all_reconciled_groups':reconciled_group_count,
        'unique_tags':len(by_tag),
        'unique_doors_by_level':dict(sorted(by_level.items())),
        'duplicate_appearance_groups':len(repeated),
        'duplicate_appearances_removed':duplicate_appearances_merged,
        'secondary_only_review_count':secondary_only_review_count,
        'secondary_only_review':secondary_review,
        # Clear v5.2 aliases / accounting.
        'sheet_appearance_count':appearance_count,
        'reconciled_group_count':reconciled_group_count,
        'duplicate_appearances_merged':duplicate_appearances_merged,
        'auto_counted_project_doors':auto_counted_project_doors,
        'registrations':registrations,'project_doors':counted,'all_groups':project,
    }

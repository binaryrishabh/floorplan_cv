from __future__ import annotations
import argparse, json, time
from pathlib import Path

from config import RENDER_DPI, OUT_DIR, LOW_DETAIL_DOUBLE_MIN_PPF
from pdf_reader import open_doc, page_drawings, page_text_spans
from shape_finder import find_doors, find_tag_leaf_doors, find_untagged_double_doors, merge_door_sets
from tag_finder import find_candidates, attach_tags
from page_space import PageSpace
from visualizer import annotate_page
from sheet_classifier import classify_sheet
from scale import choose_page_scale
from reconcile import reconcile
from anchor_finder import find_text_anchors
from output_utils import safe_write_text


def main(pdf_path, out_dir=OUT_DIR, dpi=RENDER_DPI, include_unknown=False, points_per_foot=None, show_review=False):
    started=time.perf_counter(); doc=open_doc(pdf_path)
    pages={}; meta={}; anchors={}; report=[]
    for idx,page in enumerate(doc):
        pno=idx+1; text=page.get_text('text')
        cls=classify_sheet(text)
        if cls['kind']!='floor_plan' and not (include_unknown and cls['kind']=='unknown'):
            print(f"sheet {pno}: skipped ({cls['kind']})")
            continue
        scale=choose_page_scale(text)
        ppf=float(points_per_foot or scale['points_per_foot'])
        drawings=page_drawings(page); spans=page_text_spans(page)
        tags=find_candidates(spans,drawings)
        anchors[pno]=find_text_anchors(spans)

        swing=find_doors(drawings,ppf)
        swing=attach_tags(swing,tags,ppf)
        tag_leaf=find_tag_leaf_doors(drawings,tags,swing,ppf)
        base=merge_door_sets(swing,tag_leaf,points_per_foot=ppf)
        doubles=find_untagged_double_doors(drawings,base,ppf)
        if ppf >= LOW_DETAIL_DOUBLE_MIN_PPF:
            doors=merge_door_sets(base,doubles,points_per_foot=ppf)
            review_candidates=[]
        else:
            doors=base
            review_candidates=doubles
            for d in review_candidates:
                d['review_reason']='low_scale_double_leaf_ambiguous'

        for d in doors:
            d['page']=pno; d['sheet_number']=cls.get('sheet_number'); d['level']=cls.get('level')
            d['area']=cls.get('area'); d['points_per_foot']=round(ppf,4)

        pages[pno]=doors
        meta[pno]={**cls,'points_per_foot':ppf,'scale_source':'override' if points_per_foot else scale['source'],
                   'scale_text':scale['scale_text'],'scale_candidates':scale['candidates'],'anchor_count':len(anchors[pno])}
        pix=page.get_pixmap(dpi=dpi,alpha=False)
        image=annotate_page(pix,PageSpace(page,dpi),doors,pno,out_dir,review_candidates if show_review else None)
        tagged=sum(1 for d in doors if d.get('tag')); methods={}
        for d in doors:methods[d.get('method','unknown')]=methods.get(d.get('method','unknown'),0)+1
        scale_desc=scale['scale_text'] or f"{ppf:.2f} pt/ft"
        print(f"sheet {pno} {cls.get('sheet_number') or ''}: {len(doors)} doors, {tagged} tagged "
              f"(arc={methods.get('swing_arc',0)}, tag-leaf={methods.get('tag_leaf',0)}, double={methods.get('double_leaf',0)}, review={len(review_candidates)}) "
              f"[{cls['detail']}, level={cls.get('level') or '?'}, scale={scale_desc}]")
        report.append({'page':pno,**cls,'rotation':page.rotation,'points_per_foot':round(ppf,4),
                       'scale_source':'override' if points_per_foot else scale['source'],'scale_text':scale['scale_text'],
                       'doors_detected':len(doors),'tagged':tagged,'methods':methods,'review_candidates':review_candidates,
                       'image':image,'doors':doors})

    rec=reconcile(pages,meta,anchors); elapsed=time.perf_counter()-started
    all_review=[{'page':r['page'],'sheet_number':r.get('sheet_number'),'level':r.get('level'),**d} for r in report for d in r.get('review_candidates',[])]
    sheet_review_count=len(all_review)
    secondary_review_count=rec.get('secondary_only_review_count',0)
    total_review_count=sheet_review_count+secondary_review_count

    accounting={
        'sheet_appearances':rec['appearance_count'],
        'duplicate_appearances_merged':rec['duplicate_appearances_merged'],
        'reconciled_groups':rec['reconciled_group_count'],
        'secondary_only_groups_withheld_for_review':secondary_review_count,
        'auto_counted_project_doors':rec['auto_counted_project_doors'],
        'sheet_level_review_candidates':sheet_review_count,
        'total_review_candidates':total_review_count,
    }
    # Keep the arithmetic self-checking in the saved artifact too.
    assert accounting['sheet_appearances'] == accounting['duplicate_appearances_merged'] + accounting['reconciled_groups']
    assert accounting['reconciled_groups'] == accounting['secondary_only_groups_withheld_for_review'] + accounting['auto_counted_project_doors']
    assert accounting['total_review_candidates'] == accounting['sheet_level_review_candidates'] + accounting['secondary_only_groups_withheld_for_review']

    summary={'pdf':Path(pdf_path).name,'runtime_seconds':round(elapsed,2),
             'review_candidates':all_review,'sheet_level_review_count':sheet_review_count,
             'total_review_count':total_review_count,'reconciliation_accounting':accounting,
             'processed_floor_plan_sheets':sorted(pages),'sheet_metadata':meta,**rec,'pages':report}
    out=Path(out_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    summary_path = safe_write_text(out/'summary.json', json.dumps(summary, indent=2), encoding='utf8')
    summary['summary_path'] = str(summary_path)

    print('\nPROJECT RECONCILIATION')
    print(f"  sheet door appearances:                 {accounting['sheet_appearances']}")
    print(f"- duplicate appearances merged:           {accounting['duplicate_appearances_merged']}")
    print(f"= reconciled physical-door groups:        {accounting['reconciled_groups']}")
    print(f"- secondary-only groups held for review:  {accounting['secondary_only_groups_withheld_for_review']}")
    print(f"= AUTO-COUNTED UNIQUE PROJECT DOORS:       {accounting['auto_counted_project_doors']}")

    print('\nREVIEW QUEUE')
    print(f"  sheet-level ambiguous candidates:        {accounting['sheet_level_review_candidates']}")
    print(f"+ secondary-only reconciled groups:        {accounting['secondary_only_groups_withheld_for_review']}")
    print(f"= total review candidates:                 {accounting['total_review_candidates']}")

    print(f"\nunique auto-counted doors by level: {summary['unique_doors_by_level']}")
    print(f"done in {elapsed:.2f}s -> {out}")
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Scale-aware vector PDF door detector and cross-sheet reconciler.')
    ap.add_argument('pdf')
    ap.add_argument('--out',default=OUT_DIR)
    ap.add_argument('--dpi',type=int,default=RENDER_DPI)
    ap.add_argument('--include-unknown',action='store_true',help='also try pages whose title cannot be classified')
    ap.add_argument('--points-per-foot',type=float,default=None,help='override inferred drawing scale for all processed sheets')
    ap.add_argument('--show-review',action='store_true',help='draw orange review-only candidates in annotated PNGs')
    args=ap.parse_args()
    main(args.pdf,args.out,args.dpi,args.include_unknown,args.points_per_foot,args.show_review)

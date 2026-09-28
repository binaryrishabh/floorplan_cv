from __future__ import annotations
import argparse, json, math


def match(pred, truth, tol):
    pairs=[]
    for i,p in enumerate(pred):
        for j,t in enumerate(truth):
            d=math.hypot(float(p[0])-float(t[0]),float(p[1])-float(t[1]))
            if d<=tol:pairs.append((d,i,j))
    usedp=set();usedt=set();tp=0
    for d,i,j in sorted(pairs):
        if i in usedp or j in usedt:continue
        usedp.add(i);usedt.add(j);tp+=1
    fp=len(pred)-tp;fn=len(truth)-tp
    precision=tp/(tp+fp) if tp+fp else 1.0
    recall=tp/(tp+fn) if tp+fn else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1}


def main(summary_path, ground_truth_path, tol=20.0):
    s=json.load(open(summary_path,encoding='utf8')); gt=json.load(open(ground_truth_path,encoding='utf8'))
    pages={str(p['page']):[(d['x'],d['y']) for d in p['doors']] for p in s['pages']}
    out={}; totalp=[]; totalt=[]
    for page in sorted(set(pages)|set(gt),key=lambda x:int(x)):
        pred=pages.get(page,[]); truth=gt.get(page,[])
        out[page]=match(pred,truth,tol); totalp.extend([(int(page),*p) for p in pred]); totalt.extend([(int(page),*t) for t in truth])
    # total is summed per-page, never cross-matches between sheets.
    tp=sum(v['tp'] for v in out.values()); fp=sum(v['fp'] for v in out.values()); fn=sum(v['fn'] for v in out.values())
    precision=tp/(tp+fp) if tp+fp else 1.0; recall=tp/(tp+fn) if tp+fn else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    result={'tolerance_pdf_points':tol,'per_page':out,'total':{'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1}}
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Evaluate per-sheet door centers against manual ground truth JSON.')
    ap.add_argument('summary'); ap.add_argument('ground_truth'); ap.add_argument('--tol',type=float,default=20.0)
    a=ap.parse_args(); main(a.summary,a.ground_truth,a.tol)

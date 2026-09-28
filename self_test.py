from sheet_classifier import classify_sheet
from scale import choose_page_scale
from reconcile import _similarity, _apply
import numpy as np


def main():
    a=choose_page_scale('ENLARGED FLOOR PLAN 1/4" = 1\'-0"')
    b=choose_page_scale('OVERALL FLOOR PLAN - LEVEL 2 1/8" = 1\'-0"')
    assert abs(a['points_per_foot']-18)<1e-6
    assert abs(b['points_per_foot']-9)<1e-6
    assert classify_sheet('A2.01A ENLARGED LEVEL 1 FLOOR PLAN - AREA A')['kind']=='floor_plan'
    assert classify_sheet('A4.01 BUILDING ELEVATIONS')['kind']!='floor_plan'
    src=np.array([[0,0],[10,0],[0,10]],float); dst=0.5*src+np.array([7,9])
    T=_similarity(src,dst); q=_apply(T,(4,6))
    assert np.linalg.norm(np.array(q)-np.array([9,12]))<1e-6
    print('self-test passed')

if __name__=='__main__':main()

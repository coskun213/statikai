import csv, math, tempfile
from pathlib import Path
from generate_dataset import generate, reactions

def test_reactions():
    assert reactions(10,8,3,6,7) == (7.4,6.6) or all(math.isclose(a,b) for a,b in zip(reactions(10,8,3,6,7),(7.4,6.6)))

def test_dataset():
    with tempfile.TemporaryDirectory() as t:
        generate(t,40,2209)
        rows=list(csv.DictReader(open(Path(t)/'ground_truth.csv')))
        assert len(rows)==200
        assert len(set(r['problem_id'] for r in rows))==40
        distinct_physical = {tuple(r[k] for k in ('L_m','P1_kN','x1_m','P2_kN','x2_m')) for r in rows}
        assert len(distinct_physical)==80, 'Each base/intervention case must be physically distinct across families'
        for r in rows:
            assert (Path(t)/r['image']).exists()
            assert (Path(t)/r['symbol_labels']).exists()
            L,P1,x1,P2,x2=[float(r[k]) for k in ('L_m','P1_kN','x1_m','P2_kN','x2_m')]
            ra,rb=reactions(L,P1,x1,P2,x2)
            assert math.isclose(float(r['RA_kN']),ra,abs_tol=1e-5)
            assert math.isclose(float(r['RB_kN']),rb,abs_tol=1e-5)
        for pid in range(40):
            sub=[r for r in rows if r['problem_id']==str(pid)]
            assert len({r['split'] for r in sub})==1
            assert len({r['RA_kN'] for r in sub[:4]})==1
            assert len({r['RB_kN'] for r in sub[:4]})==1

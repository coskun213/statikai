"""Evaluate external reactions using ground-truth inputs, not visual inference."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statikai.physics import reactions, residuals


def _read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def evaluate(truth_csv, prediction_csv, out_csv, reaction_tol=0.05,
             force_tol=0.05, moment_tol=0.05):
    for tolerance in (reaction_tol, force_tol, moment_tol):
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError('Tolerances must be finite and non-negative')
    truth_rows, predictions = _read(truth_csv), _read(prediction_csv)
    if not truth_rows or not predictions:
        raise ValueError('Truth and predictions must both contain data rows')
    truth = {row['image']: row for row in truth_rows}
    if len(truth) != len(truth_rows):
        raise ValueError('Duplicate image IDs in ground truth')
    rows, by_problem, seen = [], defaultdict(dict), set()
    for prediction in predictions:
        image = prediction['image']
        if image not in truth or image in seen:
            raise ValueError(f'Unknown or duplicate prediction image: {image}')
        seen.add(image)
        gt = truth[image]
        inputs = tuple(float(gt[key]) for key in ('L_m','P1_kN','x1_m','P2_kN','x2_m'))
        expected = reactions(*inputs)
        reference = float(gt['RA_kN']), float(gt['RB_kN'])
        if not all(math.isfinite(v) for v in reference) or max(abs(a-b) for a,b in zip(reference,expected)) > 1e-5:
            raise ValueError(f'Invalid analytical reference: {image}')
        ra, rb = float(prediction['predicted_RA_kN']), float(prediction['predicted_RB_kN'])
        rf, rm = residuals(*inputs, ra, rb)
        error = max(abs(ra-reference[0]), abs(rb-reference[1]))
        rows.append(dict(image=image, problem_id=gt['problem_id'], variant=gt['variant'],
                         split=gt['split'], max_abs_reaction_error_kN=error,
                         force_residual_kN=rf, moment_residual_kNm=rm,
                         solution_correct_0_1=int(error <= reaction_tol),
                         physics_flag_0_1=int(abs(rf)>force_tol or abs(rm)>moment_tol)))
        by_problem[gt['problem_id']][gt['variant']] = (ra,rb)
    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf8', newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    eligible = [v for v in by_problem.values() if all(str(i) in v for i in range(4))]
    consistent = sum(all(max(abs(v[str(i)][k]-v['0'][k]) for k in (0,1)) <= reaction_tol
                         for i in range(1,4)) for v in eligible)
    correct = sum(r['solution_correct_0_1'] for r in rows)
    report = dict(predictions=len(rows), expected_predictions=len(truth),
                  coverage=len(rows)/len(truth), missing_predictions=len(truth)-len(rows),
                  conditional_solution_accuracy=correct/len(rows),
                  full_truth_solution_accuracy=correct/len(truth),
                  reaction_tolerance_kN=reaction_tol, force_tolerance_kN=force_tol,
                  moment_tolerance_kNm=moment_tol,
                  physics_flag_rate=sum(r['physics_flag_0_1'] for r in rows)/len(rows),
                  equivalence_consistency=consistent/len(eligible) if eligible else None,
                  consistent_n=consistent, eligible_equivalence_sets=len(eligible))
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--truth',default='dataset/ground_truth.csv')
    parser.add_argument('--predictions',required=True)
    parser.add_argument('--out',default='predictions_evaluated.csv')
    args=parser.parse_args()
    evaluate(args.truth,args.predictions,args.out)

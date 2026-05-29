"""
experiments.py
==============
Runs the three required experiments and writes all result artefacts to
results/.

  Experiment 1 -- User comparison : User 1 vs User 2 Pareto fronts.
  Experiment 2 -- Algorithm comparison : NSGA-II vs SPEA2, same parameters.
  Experiment 3 -- Diversity impact : diversity ON vs OFF.

These are covered by the run matrix:  {user 1,2} x {NSGA-II, SPEA2} x {div on/off}.

Hypervolume uses a SINGLE fixed reference point shared by all runs: for each
objective, the worst value observed across all runs (final fronts + every
generation snapshot) extended by 10% of the observed range. Reported in
results/reference_point.json.

All objectives are stored in minimisation form ( -preference, cost, time );
the CSV/JSON also report the raw human-readable objectives.
"""
from __future__ import annotations

import csv
import json
import os
import time

import data_model
import nsga2
import spea2
from config import Config
from hypervolume import hypervolume
from moea_common import raw_min
from data_model import NUTRIENT_IDS, NUTRIENT_LABELS, NUTRIENT_UNITS

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")

POP = 100
GEN = 100
SEED = 42
ALGOS = {"NSGA-II": nsga2, "SPEA2": spea2}


def run_matrix():
    """Run every (user, algorithm, diversity) combination once."""
    results = {}
    for uid in (1, 2):
        problem = data_model.build_problem(uid)
        for algo_name, mod in ALGOS.items():
            for div in (True, False):
                cfg = Config(pop_size=POP, generations=GEN, seed=SEED, use_diversity=div)
                label = "u%d_%s_%s" % (uid, algo_name.replace("-", "").lower(),
                                       "div" if div else "nodiv")
                t = time.time()
                res = mod.run(problem, cfg)
                dt = time.time() - t
                res.front = _dedupe_front(res.front)
                results[label] = {
                    "label": label, "user": uid, "algo": algo_name, "diversity": div,
                    "result": res, "seconds": dt,
                }
                print("  %-22s %5.1fs  front=%3d feasible=%3d" % (
                    label, dt, len(res.front), sum(i.ev.feasible for i in res.front)))
    return results


def _dedupe_front(front):
    """Keep one individual per distinct raw objective vector (cleaner front)."""
    seen = {}
    for ind in front:
        key = (round(ind.ev.raw["preference"], 6), round(ind.ev.raw["cost"], 6),
               round(ind.ev.raw["time"], 6))
        if key not in seen:
            seen[key] = ind
    return list(seen.values())


def compute_reference(results):
    """Worst min-objective per dimension across ALL points + 10% of range."""
    n_obj = 3
    pts = []
    for r in results.values():
        res = r["result"]
        pts.extend(raw_min(i) for i in res.front)
        for snap in res.history:
            pts.extend(snap)
    worst = [max(p[k] for p in pts) for k in range(n_obj)]
    best = [min(p[k] for p in pts) for k in range(n_obj)]
    ref = []
    for k in range(n_obj):
        span = (worst[k] - best[k]) or abs(worst[k]) or 1.0
        ref.append(worst[k] + 0.10 * span)
    return tuple(ref)


def export_pareto(results, problem_by_user):
    os.makedirs(RESULTS, exist_ok=True)
    for label, r in results.items():
        res = r["result"]
        problem = problem_by_user[r["user"]]
        rows = []
        for sid, ind in enumerate(sorted(res.front, key=lambda i: -i.ev.raw["preference"])):
            ev = ind.ev
            row = {
                "solution_id": sid,
                "preference": round(ev.raw["preference"], 4),
                "cost": round(ev.raw["cost"], 4),
                "time": round(ev.raw["time"], 4),
                "feasible": int(ev.feasible),
                "compliance_5": ev.compliance,
                "distinct_groups": ev.distinct_groups,
                "n_foods": ev.n_foods,
            }
            for nid in NUTRIENT_IDS:
                row[NUTRIENT_LABELS[nid].lower()] = round(ev.totals[nid], 2)
            row["food_ids"] = ";".join(str(x) for x in ev.menu)
            row["food_names"] = " | ".join(problem.foods[x].name for x in ev.menu)
            rows.append(row)
        # CSV
        csv_path = os.path.join(RESULTS, "pareto_%s.csv" % label)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        # JSON (with DRI bounds for menu-quality reporting)
        json_path = os.path.join(RESULTS, "pareto_%s.json" % label)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "label": label, "user": r["user"], "algo": r["algo"],
                "diversity": r["diversity"], "seed": SEED,
                "dri_bounds": {NUTRIENT_LABELS[nid]: list(problem.dri[nid]) for nid in NUTRIENT_IDS},
                "solutions": rows,
            }, f, ensure_ascii=False, indent=2)


def export_metrics(results, ref):
    # final HV + convergence
    hv_rows = []
    conv_rows = []
    for label, r in results.items():
        res = r["result"]
        final_front = [raw_min(i) for i in res.front]
        final_hv = hypervolume(final_front, ref)
        hv_rows.append({
            "label": label, "user": r["user"], "algo": r["algo"], "diversity": int(r["diversity"]),
            "final_hypervolume": round(final_hv, 4),
            "front_size": len(res.front),
            "feasible": sum(i.ev.feasible for i in res.front),
            "avg_distinct_groups": round(
                sum(i.ev.distinct_groups for i in res.front) / len(res.front), 3),
            "seconds": round(r["seconds"], 2),
        })
        for gen, snap in enumerate(res.history):
            conv_rows.append({"label": label, "generation": gen,
                              "hypervolume": round(hypervolume(snap, ref), 4)})

    with open(os.path.join(RESULTS, "hypervolume.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hv_rows[0].keys()))
        w.writeheader()
        w.writerows(hv_rows)
    with open(os.path.join(RESULTS, "convergence.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["label", "generation", "hypervolume"])
        w.writeheader()
        w.writerows(conv_rows)

    ref_meta = {
        "reference_point_min_form": list(ref),
        "objectives_min_form": ["-preference", "cost", "time"],
        "note": "worst value across all runs (final fronts + every generation) + 10% of range",
        "pop_size": POP, "generations": GEN, "seed": SEED,
        "penalty_lambda": Config().lam, "diversity_alpha": Config().alpha,
    }
    with open(os.path.join(RESULTS, "reference_point.json"), "w", encoding="utf-8") as f:
        json.dump(ref_meta, f, indent=2)
    return hv_rows


def main():
    print("Running experiment matrix (pop=%d gen=%d seed=%d)..." % (POP, GEN, SEED))
    problem_by_user = {1: data_model.build_problem(1), 2: data_model.build_problem(2)}
    results = run_matrix()
    ref = compute_reference(results)
    print("\nShared HV reference point (min-form): %s" % (tuple(round(x, 2) for x in ref),))
    export_pareto(results, problem_by_user)
    hv_rows = export_metrics(results, ref)

    print("\n=== Summary (final hypervolume) ===")
    print("%-22s %8s %6s %9s %6s" % ("run", "HV", "front", "feasible", "groups"))
    for h in hv_rows:
        print("%-22s %8.1f %6d %9d %6.1f" % (
            h["label"], h["final_hypervolume"], h["front_size"], h["feasible"],
            h["avg_distinct_groups"]))
    print("\nArtefacts written to %s/" % RESULTS)


if __name__ == "__main__":
    main()

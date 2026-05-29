"""
objectives.py  (OUR CODE -- graded)
===================================
Evaluate a chromosome into its objective vector + constraint penalty.

Objectives chosen (handout: exactly 3, f1 mandatory):
    f1 = total user preference   -> MAX
    f2 = total cost              -> MIN
    f3 = total prep+cook time    -> MIN

For the MOEA everything is minimised, so the fitness vector is
    ( -preference , cost , time )
The DRI penalty R (and optional diversity term) is folded in by WORSENING every
objective by lambda * R_total -- i.e. the handout's `obj - lambda*R` for the
maximised objective and `obj + lambda*R` for the minimised ones. Infeasible
menus are thus pushed off the Pareto front while we still tune lambda.

`OBJ_NAMES` / `OBJ_DIRS` describe the raw objectives for reporting.
"""
from __future__ import annotations

from dataclasses import dataclass

from data_model import NUTRIENT_IDS
import penalty
import diversity
import decode as decode_mod

OBJ_NAMES = ("preference", "cost", "time")
OBJ_DIRS = ("max", "min", "min")
N_OBJ = 3


@dataclass
class Eval:
    menu: list                 # selected food ids (phenotype)
    raw: dict                  # {'preference','cost','time'} raw objective values
    totals: dict               # nutrientId -> menu total
    R: float                   # DRI violation penalty
    R_total: float             # R (+ diversity term if enabled)
    distinct_groups: int
    compliance: int            # # of 5 nutrients within hard DRI bounds
    feasible: bool             # all 5 within hard DRI bounds
    fitness: tuple             # minimisation vector (penalised)
    n_foods: int


def raw_objectives(problem, menu) -> dict:
    pref = cost = time = 0.0
    for fid in menu:
        f = problem.foods[fid]
        pref += f.preference
        cost += f.cost
        time += f.time
    return {"preference": pref, "cost": cost, "time": time}


def evaluate(problem, chromo, lam: float = 1.0, alpha: float = 1.0,
             use_diversity: bool = True) -> Eval:
    menu = decode_mod.decode(problem, chromo)
    raw = raw_objectives(problem, menu)
    totals = problem.nutrient_totals(menu)

    R, _ = penalty.violation_R(totals, problem.dri)
    R_total = R
    if use_diversity:
        R_total = R + diversity.diversity_term(problem, menu, alpha)

    groups = diversity.distinct_groups(problem, menu)
    compliance = penalty.compliance_count(totals, problem.dri)
    feasible = compliance == len(NUTRIENT_IDS)

    pen = lam * R_total
    fitness = (
        -raw["preference"] + pen,   # maximise preference -> minimise (-pref); worsen by +pen
        raw["cost"] + pen,
        raw["time"] + pen,
    )

    return Eval(
        menu=menu, raw=raw, totals=totals, R=R, R_total=R_total,
        distinct_groups=groups, compliance=compliance, feasible=feasible,
        fitness=fitness, n_foods=len(menu),
    )

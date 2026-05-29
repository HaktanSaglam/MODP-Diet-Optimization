"""
decode.py  (OUR CODE -- graded, the heart of the project)
=========================================================
Greedy left-to-right decoding of a chromosome (genotype) into the actual
selected menu (phenotype), exactly per handout section 3.

Breakfast part  -- Energy + Protein only, target 35% of daily DRI:
    * iterate the breakfast genes left to right
    * tentatively add each food; if it would exceed eps*RUL_b for Energy or
      Protein -> skip it
    * stop once eps*RLL_b for BOTH Energy and Protein is satisfied

Lunch+dinner part -- all 5 nutrients, totals carried over from breakfast:
    * same greedy procedure, checking all 5 daily DRI bounds at each step
    * stop once all 5 reach the (soft) lower bound

Tolerances (handout): effective RUL = RUL*1.15, effective RLL = RLL*0.90,
breakfast split RLL_b = RLL*0.35, RUL_b = RUL*0.35.
"""
from __future__ import annotations

from data_model import (
    NUTRIENT_IDS,
    EPS_RUL,
    EPS_RLL,
    BREAKFAST_FRACTION,
)

ENERGY = 5
PROTEIN = 15
BREAKFAST_NUTRIENTS = (ENERGY, PROTEIN)


def decode(problem, chromo) -> list:
    """Return the list of selected food ids (the menu / phenotype)."""
    dri = problem.dri
    foods = problem.foods
    totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    selected = []

    # --- Breakfast: Energy + Protein only, 35% of daily DRI ----------------
    b_upper = {nid: dri[nid][1] * BREAKFAST_FRACTION * EPS_RUL for nid in BREAKFAST_NUTRIENTS}
    b_lower = {nid: dri[nid][0] * BREAKFAST_FRACTION * EPS_RLL for nid in BREAKFAST_NUTRIENTS}
    for fid in chromo.breakfast:
        if all(totals[nid] >= b_lower[nid] for nid in BREAKFAST_NUTRIENTS):
            break  # breakfast target met
        f = foods[fid]
        # would this food push Energy or Protein over the (soft) breakfast cap?
        if any(totals[nid] + f.nutrient(nid) > b_upper[nid] for nid in BREAKFAST_NUTRIENTS):
            continue
        selected.append(fid)
        for nid in NUTRIENT_IDS:           # accumulate ALL nutrients (carry over)
            totals[nid] += f.nutrient(nid)

    # --- Lunch+dinner: all 5 nutrients, full daily DRI ---------------------
    d_upper = {nid: dri[nid][1] * EPS_RUL for nid in NUTRIENT_IDS}
    d_lower = {nid: dri[nid][0] * EPS_RLL for nid in NUTRIENT_IDS}
    for fid in chromo.lunchdinner:
        if all(totals[nid] >= d_lower[nid] for nid in NUTRIENT_IDS):
            break  # all daily lower bounds satisfied
        f = foods[fid]
        if any(totals[nid] + f.nutrient(nid) > d_upper[nid] for nid in NUTRIENT_IDS):
            continue
        selected.append(fid)
        for nid in NUTRIENT_IDS:
            totals[nid] += f.nutrient(nid)

    return selected

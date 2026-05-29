"""
penalty.py  (OUR CODE -- graded)
================================
DRI constraint-violation penalty, exactly as specified in the handout
(section 4). Solutions that violate the hard DRI bounds are penalized
proportionally; under-nutrition is penalized harder (0.7) than over-nutrition
(0.3).

    for each nutrient j with menu total v_j and bounds [RLL_j, RUL_j]:
        viol_low_j  = max(0, RLL_j - v_j) / (RUL_j - RLL_j)
        viol_high_j = max(0, v_j - RUL_j) / (RUL_j - RLL_j)
    R = 0.7 * sum(viol_low_j) + 0.3 * sum(viol_high_j)

The penalty is later combined into the fitness as  obj - lambda * R  (for the
maximised objective) / obj + lambda * R (for minimised objectives).
"""
from __future__ import annotations

from data_model import NUTRIENT_IDS

W_LOW = 0.7    # under-nutrition penalised harder
W_HIGH = 0.3   # over-nutrition penalised lighter


def violation_R(totals: dict, dri: dict):
    """Return (R, per_nutrient) where per_nutrient[nid] = (viol_low, viol_high)."""
    sum_low = 0.0
    sum_high = 0.0
    per_nutrient = {}
    for nid in NUTRIENT_IDS:
        rll, rul = dri[nid]
        v = totals.get(nid, 0.0)
        span = (rul - rll) or 1.0
        vlow = max(0.0, rll - v) / span
        vhigh = max(0.0, v - rul) / span
        per_nutrient[nid] = (vlow, vhigh)
        sum_low += vlow
        sum_high += vhigh
    R = W_LOW * sum_low + W_HIGH * sum_high
    return R, per_nutrient


def compliance_count(totals: dict, dri: dict) -> int:
    """How many of the 5 nutrients are inside the hard DRI bounds."""
    c = 0
    for nid in NUTRIENT_IDS:
        rll, rul = dri[nid]
        v = totals.get(nid, 0.0)
        if rll <= v <= rul:
            c += 1
    return c

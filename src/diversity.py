"""
diversity.py  (OUR CODE -- graded)
==================================
Diversity mechanism (handout section 5). A valid daily menu should span several
food groups. We implement **Option B -- penalty term**, because it toggles
cleanly on/off for the required "with vs without diversity" experiment:

    R_total = R + alpha * (1 / distinct_group_count)

(low group-diversity -> larger penalty). Target 4-6 distinct food groups.
`distinct_groups` is also reported as a menu-quality metric.
"""
from __future__ import annotations


def distinct_groups(problem, menu) -> int:
    return len({problem.foods[fid].group_id for fid in menu})


def diversity_term(problem, menu, alpha: float) -> float:
    """alpha * (1 / distinct_group_count). 0 groups -> max penalty (alpha)."""
    g = distinct_groups(problem, menu)
    if g <= 0:
        return alpha
    return alpha * (1.0 / g)

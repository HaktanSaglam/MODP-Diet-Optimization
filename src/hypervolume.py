"""
hypervolume.py  (OUR CODE)
==========================
Exact hypervolume of a MINIMISATION objective set with respect to a fixed
reference point (the worst/upper corner). Implemented with the HSO
(Hypervolume by Slicing Objectives) recursion -- exact and simple, fine for the
3 objectives and modest front sizes in this project.

The handout requires hypervolume (true Pareto front unknown, so IGD is out)
with a single fixed reference point shared by all algorithms (= worst value per
objective across all runs + 10% margin).
"""
from __future__ import annotations


def _pareto_min(pts):
    """Keep only non-dominated points (minimisation)."""
    out = []
    for i, p in enumerate(pts):
        dom = False
        for j, q in enumerate(pts):
            if i == j:
                continue
            if all(q[k] <= p[k] for k in range(len(p))) and any(q[k] < p[k] for k in range(len(p))):
                dom = True
                break
        if not dom:
            out.append(p)
    return out


def _hso(pts, ref):
    d = len(ref)
    if not pts:
        return 0.0
    if d == 1:
        return max(0.0, ref[0] - min(p[0] for p in pts))
    pts = sorted(pts, key=lambda p: p[0])      # ascending on first objective
    vol = 0.0
    for i in range(len(pts)):
        next0 = pts[i + 1][0] if i + 1 < len(pts) else ref[0]
        width = next0 - pts[i][0]
        if width <= 0:
            continue
        proj = _pareto_min([p[1:] for p in pts[:i + 1]])
        base = _hso(proj, ref[1:])
        vol += width * base
    return vol


def hypervolume(front, ref) -> float:
    """`front`: list of minimisation objective tuples. `ref`: worst-corner point."""
    ref = tuple(ref)
    pts = [tuple(p) for p in front if all(p[k] < ref[k] for k in range(len(ref)))]
    if not pts:
        return 0.0
    return _hso(_pareto_min(pts), ref)


if __name__ == "__main__":
    # sanity checks
    # 2D: single point (1,1), ref (2,2) -> area 1
    print("expect 1.0 ->", hypervolume([(1, 1)], (2, 2)))
    # 2D: points (1,2),(2,1), ref (3,3) -> 2*1 + 1*2 - 1*1 = ... compute: union of [(1,2),(3,3)] & [(2,1),(3,3)]
    # box A=(3-1)*(3-2)=2, box B=(3-2)*(3-1)=2, overlap=(3-2)*(3-2)=1 -> 3
    print("expect 3.0 ->", hypervolume([(1, 2), (2, 1)], (3, 3)))
    # 3D: single point (0,0,0) ref (1,1,1) -> 1
    print("expect 1.0 ->", hypervolume([(0, 0, 0)], (1, 1, 1)))

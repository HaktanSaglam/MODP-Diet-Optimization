"""
moea_common.py  (OUR CODE -- graded)
====================================
Shared machinery for the MOEAs: the Individual wrapper, Pareto dominance,
fast non-dominated sorting (NSGA-II) and crowding distance. SPEA2's strength /
density bits live in spea2.py.

All objective vectors are MINIMISATION (see objectives.py): an individual's
`fitness` is the penalised ( -preference, cost, time ) tuple.
"""
from __future__ import annotations

from dataclasses import dataclass

import objectives


@dataclass
class Result:
    algo: str
    problem: object
    cfg: object
    pop: list           # final population (or archive)
    front: list         # final non-dominated Individuals
    history: list       # per-generation: list of raw-min objective tuples of the front


def raw_min(ind) -> tuple:
    """Raw objective vector in minimisation form: ( -preference, cost, time )."""
    r = ind.ev.raw
    return (-r["preference"], r["cost"], r["time"])


class Individual:
    __slots__ = ("chromo", "ev", "fitness",
                 "rank", "crowding",            # NSGA-II
                 "strength", "raw_fitness", "density", "spea_fitness")  # SPEA2

    def __init__(self, chromo, ev):
        self.chromo = chromo
        self.ev = ev
        self.fitness = ev.fitness
        self.rank = None
        self.crowding = 0.0
        self.strength = 0
        self.raw_fitness = 0.0
        self.density = 0.0
        self.spea_fitness = 0.0


def make_individual(problem, chromo, cfg) -> Individual:
    ev = objectives.evaluate(problem, chromo, lam=cfg.lam, alpha=cfg.alpha,
                             use_diversity=cfg.use_diversity)
    return Individual(chromo, ev)


def dominates(a: Individual, b: Individual) -> bool:
    """True if a Pareto-dominates b (minimisation on all objectives)."""
    fa, fb = a.fitness, b.fitness
    not_worse = True
    strictly_better = False
    for x, y in zip(fa, fb):
        if x > y:
            not_worse = False
            break
        if x < y:
            strictly_better = True
    return not_worse and strictly_better


def fast_non_dominated_sort(pop):
    """Return list of fronts (each a list of Individuals); sets `rank`."""
    S = {id(p): [] for p in pop}
    n = {id(p): 0 for p in pop}
    fronts = [[]]
    for p in pop:
        for q in pop:
            if p is q:
                continue
            if dominates(p, q):
                S[id(p)].append(q)
            elif dominates(q, p):
                n[id(p)] += 1
        if n[id(p)] == 0:
            p.rank = 0
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[id(p)]:
                n[id(q)] -= 1
                if n[id(q)] == 0:
                    q.rank = i + 1
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    fronts.pop()
    return fronts


def crowding_distance(front, n_obj: int = None):
    """Assign NSGA-II crowding distance to every individual in `front`."""
    if not front:
        return
    n_obj = n_obj or len(front[0].fitness)
    for p in front:
        p.crowding = 0.0
    m = len(front)
    for k in range(n_obj):
        front.sort(key=lambda ind: ind.fitness[k])
        front[0].crowding = float("inf")
        front[-1].crowding = float("inf")
        fmin = front[0].fitness[k]
        fmax = front[-1].fitness[k]
        span = (fmax - fmin) or 1.0
        for i in range(1, m - 1):
            front[i].crowding += (front[i + 1].fitness[k] - front[i - 1].fitness[k]) / span


def crowded_better(a: Individual, b: Individual) -> bool:
    """NSGA-II crowded-comparison: lower rank wins, then higher crowding."""
    if a.rank != b.rank:
        return a.rank < b.rank
    return a.crowding > b.crowding


def nondominated(pop):
    """Return the non-dominated subset (Pareto front) of a population."""
    out = []
    for p in pop:
        if not any(dominates(q, p) for q in pop if q is not p):
            out.append(p)
    return out
